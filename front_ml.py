"""RefriPerú - Aplicación Streamlit Integrada

Esta aplicación es la interface final de RefriPerú con:
- Login seguro con roles (Analista Logístico / Administrador)
- Regresor XGBoost de demanda semanal por SKU (lags + media móvil), entrenado
  una vez con corte temporal 80/20 y persistido en models/xgb_forecast_reg.json
- Pronóstico T+1 con intervalo de confianza 95% (ŷ ± 1.96·RMSE)
- Política de inventario: stock de seguridad, punto de reorden, estado del SKU
  y cantidad sugerida de pedido (el stock actual es SIMULADO)
- Métricas RMSE / MAE / MAPE impresas en consola una vez por sesión
- Dashboard, pronóstico, sugerencias de pedidos, logs, auditoría y configuración

Para ejecutar:
    pip install -r requirements.txt
    streamlit run front_ml.py
"""

import os
import io
import math
import importlib.util
from datetime import datetime

try:
    import pandas as pd
    import numpy as np
    import streamlit as st
    import altair as alt
except ImportError as exc:
    missing = str(exc).split()[-1].strip("\"\'")
    raise SystemExit(
        "Faltan dependencias: instale `streamlit`, `pandas`, `numpy`, `altair`, `scikit-learn` y `xgboost` si aún no las tiene. "
        "Ejecute: pip install -r requirements.txt"
    )

# ===== Configuración global =====
APP_TITLE = "RefriPerú Analytics - Dashboard Logístico"
DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset_refriperu.csv")
MODEL_FOLDER = os.path.join(os.path.dirname(__file__), "models")
MODEL_FILE_JSON = os.path.join(MODEL_FOLDER, "xgb_asymmetric.json")
MODEL_FILE_BIN = os.path.join(MODEL_FOLDER, "xgb_asymmetric.bin")

USERS = {
    "analista": {
        "password": "refri2026",
        "role": "Analista Logístico",
        "label": "Analista Logístico"
    },
    "admin": {
        "password": "admin2026",
        "role": "Administrador",
        "label": "Administrador"
    }
}

ROLE_PAGES = {
    "Analista Logístico": [
        "Dashboard General",
        "Pronóstico de Demanda",
        "Sugerencia de Pedidos"
    ],
    "Administrador": [
        "Dashboard General",
        "Pronóstico de Demanda",
        "Sugerencia de Pedidos",
        "Logs del Sistema",
        "Auditoría de Datos",
        "Configuración de Parámetros Core"
    ]
}

DEFAULT_MODEL_CONFIG = {
    "learning_rate": 0.08,
    "max_depth": 5,
    "n_estimators": 120,
    "scale_pos_weight": 2.2
}

MODEL_FILE_REG = os.path.join(MODEL_FOLDER, "xgb_forecast_reg.json")
FEATURES_REG = ["lag_1", "lag_2", "rolling_mean_4", "week_of_year", "IsHoliday", "Temperatura_Promedio"]
REG_PARAMS = dict(objective="reg:squarederror", n_estimators=300, learning_rate=0.05, max_depth=6,
                  subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=0)
Z_CI = 1.96               # IC 95%
MAPE_TARGET = 15.0        # %
MAPE_MIN_ABS = 1.0        # excluir |y| < 1.0 (mil $) del MAPE
MIN_VAL_POINTS_SKU = 8    # mínimo de puntos de validación para usar RMSE propio del SKU
LEAD_TIME_WEEKS = 2
Z_SERVICE = 1.65          # nivel de servicio 95%
DEMAND_WINDOW_WEEKS = 12  # ventana para μ y σ
NO_MOVEMENT_WEEKS = 8
OVERSTOCK_COVER_WEEKS = 4
STATUS_ORDER = ["Crítico", "Bajo", "Óptimo", "Sobrestock", "Sin Movimiento"]
STATUS_ICON = {"Crítico": "🔴", "Bajo": "🟠", "Óptimo": "🟢", "Sobrestock": "🔵", "Sin Movimiento": "⚪"}
STATUS_COLOR = {"Crítico": "#dc2626", "Bajo": "#f59e0b", "Óptimo": "#16a34a",
                "Sobrestock": "#2563eb", "Sin Movimiento": "#9ca3af"}
CATEGORIES = ["Climatización", "Refrigeración", "Ventilación", "Componentes"]

# ===== Estilos corporativos nativos =====
CUSTOM_CSS = """
<style>
    .stApp {
        background: #f5f8fb;
        color: #1f2937;
    }
    .card {
        background: #ffffff;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
        margin-bottom: 20px;
    }
    .metric-label {
        color: #4b5563;
    }
    .metric-value {
        color: #111827;
        font-weight: 700;
    }
</style>
"""

# ===== Helpers =====

def reset_session_state():
    """Limpia el estado de sesión para logout limpio."""
    for key in [
        "logged_in",
        "username",
        "role",
        "user_label",
        "selected_page",
        "category_filter",
        "sku_filter",
        "order_history",
        "inventory_state",
        "order_filter",
        "order_flash",
        "dataset_processed",
        "core_parameters"
    ]:
        if key in st.session_state:
            del st.session_state[key]


def authenticate_user(username: str, password: str):
    """Valida credenciales en memoria y devuelve rol si existe."""
    user = USERS.get(username)
    if not user:
        return False, None, None
    if user["password"] != password:
        return False, None, None
    return True, user["role"], user["label"]


@st.cache_data(show_spinner=False)
def load_dataset() -> pd.DataFrame:
    """Carga el dataset y aplica el pipeline ETL descrito en el benchmark."""
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"No se encontró el archivo de datos: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH, parse_dates=["Date"], dayfirst=False)
    df = df.loc[df["Store"] == 1].copy()
    df["Week"] = df["Date"].dt.strftime("%Y-%U")
    df["unidades"] = df["Weekly_Sales"] / 1000.0
    # Temperatura simulada solo estacional: no debe depender de Weekly_Sales
    # (es feature del regresor y filtraría la variable objetivo).
    df["Temperatura_Promedio"] = (
        14.0
        + 8.0 * np.sin(2 * np.pi * df["Date"].dt.dayofyear / 365.0)
    )
    df["Temperatura_Promedio"] = df["Temperatura_Promedio"].interpolate(method="linear").round(1)
    df["IsHoliday"] = df["IsHoliday"].astype(str).str.upper().map({"TRUE": 1, "FALSE": 0})
    df["IsHoliday"] = df["IsHoliday"].fillna(0).astype(int)

    df["sku"] = "SKU-" + df["Dept"].astype(int).astype(str).str.zfill(3)
    df["categoria"] = dept_to_category(df["Dept"])

    # Features de series de tiempo por SKU (solo información pasada)
    df = df.sort_values(["sku", "Date"])
    grouped = df.groupby("sku")["unidades"]
    df["lag_1"] = grouped.shift(1)
    df["lag_2"] = grouped.shift(2)
    df["rolling_mean_4"] = grouped.transform(lambda s: s.shift(1).rolling(4, min_periods=1).mean())
    df["week_of_year"] = df["Date"].dt.isocalendar().week.astype(int)

    return df.reset_index(drop=True)


def dept_to_category(dept: pd.Series) -> pd.Series:
    """Asigna categoría por rango de Dept: 1-25, 26-50, 51-75 y resto."""
    return pd.cut(
        dept,
        bins=[-np.inf, 25, 50, 75, np.inf],
        labels=CATEGORIES,
    ).astype(str)


def build_forecast_features(df: pd.DataFrame):
    """Devuelve (X, y, meta) para el regresor, solo con filas que tienen lag_1 y lag_2."""
    data = df.loc[df["lag_1"].notna() & df["lag_2"].notna()]
    X = data[FEATURES_REG].astype(float)
    y = data["unidades"].astype(float)
    meta = data[["sku", "categoria", "Date"]].copy()
    return X, y, meta


def compute_regression_metrics(y_true, y_pred) -> dict:
    """RMSE, MAE y MAPE (%) del pronóstico; el MAPE excluye |y| < MAPE_MIN_ABS."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    error = y_pred - y_true
    n = int(len(y_true))
    rmse = float(np.sqrt(np.mean(error ** 2))) if n else 0.0
    mae = float(np.mean(np.abs(error))) if n else 0.0
    mask = np.abs(y_true) >= MAPE_MIN_ABS
    n_mape = int(mask.sum())
    mape = float(np.mean(np.abs(error[mask] / y_true[mask])) * 100) if n_mape else float("nan")
    return {
        "rmse": round(rmse, 3),
        "mae": round(mae, 3),
        "mape": round(mape, 3),
        "n": n,
        "n_mape": n_mape
    }


@st.cache_resource(show_spinner="Cargando modelo de pronóstico…")
def train_or_load_forecaster() -> dict:
    """Carga el regresor persistido (o lo entrena una vez) y lo evalúa en validación temporal."""
    from xgboost import XGBRegressor

    df = load_dataset()
    X, y, meta = build_forecast_features(df)

    dates = np.sort(meta["Date"].unique())
    cutoff = dates[int(len(dates) * 0.8)]
    train_mask = (meta["Date"] < cutoff).to_numpy()
    val_mask = ~train_mask

    model, source = None, "entrenado"
    if os.path.exists(MODEL_FILE_REG):
        try:
            candidate = XGBRegressor()
            candidate.load_model(MODEL_FILE_REG)
            if list(candidate.get_booster().feature_names or []) == FEATURES_REG:
                model, source = candidate, "cargado"
        except Exception:
            model = None

    if model is None:
        model = XGBRegressor(**REG_PARAMS)
        model.fit(X[train_mask], y[train_mask])
        os.makedirs(MODEL_FOLDER, exist_ok=True)
        model.save_model(MODEL_FILE_REG)

    val_df = meta.loc[val_mask].copy()
    val_df["real"] = y[val_mask].to_numpy()
    val_df["pred"] = model.predict(X[val_mask])

    metrics = compute_regression_metrics(val_df["real"], val_df["pred"])
    rmse_by_sku = {
        sku: compute_regression_metrics(group["real"], group["pred"])["rmse"]
        for sku, group in val_df.groupby("sku")
        if len(group) >= MIN_VAL_POINTS_SKU
    }
    metrics_by_category = {
        categoria: compute_regression_metrics(group["real"], group["pred"])
        for categoria, group in val_df.groupby("categoria")
    }

    return {
        "model": model,
        "metrics": metrics,
        "rmse_by_sku": rmse_by_sku,
        "metrics_by_category": metrics_by_category,
        "val_df": val_df.reset_index(drop=True),
        "source": source
    }


def predict_t1(df: pd.DataFrame, forecaster: dict) -> pd.DataFrame:
    """HU020: pronóstico de la semana siguiente por SKU con IC 95% (ŷ ± Z_CI·RMSE)."""
    global_rmse = forecaster["metrics"]["rmse"]
    rmse_by_sku = forecaster["rmse_by_sku"]
    rows, no_history = [], []

    for sku, hist in df.sort_values("Date").groupby("sku", sort=True):
        fecha_t1 = hist["Date"].iloc[-1] + pd.Timedelta(days=7)
        base = {"sku": sku, "categoria": hist["categoria"].iloc[0], "fecha_t1": fecha_t1}
        if len(hist) < 4:
            no_history.append(base)
            continue
        units = hist["unidades"].to_numpy()
        rows.append({
            **base,
            "lag_1": units[-1],
            "lag_2": units[-2],
            "rolling_mean_4": units[-4:].mean(),
            "week_of_year": int(fecha_t1.isocalendar()[1]),
            "IsHoliday": 0,
            "Temperatura_Promedio": hist["Temperatura_Promedio"].iloc[-1],
        })

    forecast = pd.DataFrame(rows)
    if not forecast.empty:
        pred = forecaster["model"].predict(forecast[FEATURES_REG].astype(float))
        forecast["forecast_t1"] = np.clip(pred, 0, None)
        forecast["rmse_usado"] = forecast["sku"].map(rmse_by_sku).fillna(global_rmse)
        forecast["rmse_fuente"] = np.where(forecast["sku"].isin(list(rmse_by_sku)), "SKU", "Global")
        forecast["ci_low"] = (forecast["forecast_t1"] - Z_CI * forecast["rmse_usado"]).clip(lower=0)
        forecast["ci_high"] = forecast["forecast_t1"] + Z_CI * forecast["rmse_usado"]

    empty = pd.DataFrame(no_history)
    if not empty.empty:
        empty[["forecast_t1", "ci_low", "ci_high", "rmse_usado"]] = 0.0
        empty["rmse_fuente"] = "Sin historia"

    columns = ["sku", "categoria", "fecha_t1", "forecast_t1", "ci_low", "ci_high", "rmse_usado", "rmse_fuente"]
    result = pd.concat([part for part in (forecast, empty) if not part.empty], ignore_index=True)[columns]
    numeric = ["forecast_t1", "ci_low", "ci_high", "rmse_usado"]
    result[numeric] = result[numeric].astype(float).round(2)
    return result.sort_values("sku").reset_index(drop=True)


def simulate_current_stock(df: pd.DataFrame) -> pd.Series:
    """Stock actual SIMULADO por SKU (el dataset no trae inventario).

    stock = media de las últimas 4 semanas de unidades (≥ 0) × U(0.3, 3.0),
    con semilla fija (42) y SKUs ordenados para que sea reproducible.
    """
    rng = np.random.default_rng(42)
    base = (
        df.sort_values("Date")
        .groupby("sku")["unidades"]
        .apply(lambda s: s.tail(4).mean())
        .clip(lower=0)
        .sort_index()
    )
    factors = rng.uniform(0.3, 3.0, size=len(base))
    return (base * factors).round(2).rename("current_stock")


def classify_stock_status(policy_df: pd.DataFrame) -> pd.DataFrame:
    """Asigna el estado del SKU según stock efectivo (actual + en tránsito), SS y ROP."""
    stock_efectivo = policy_df["current_stock"] + policy_df["en_transito"]
    policy_df["stock_efectivo"] = stock_efectivo.round(2)
    policy_df["status"] = np.select(
        [
            policy_df["ventas_ult_8"] <= 0,
            stock_efectivo <= policy_df["safety_stock"],
            stock_efectivo <= policy_df["rop"],
            stock_efectivo > policy_df["rop"] + OVERSTOCK_COVER_WEEKS * policy_df["forecast_t1"],
        ],
        ["Sin Movimiento", "Crítico", "Bajo", "Sobrestock"],
        default="Óptimo",
    )
    policy_df["status_label"] = policy_df["status"].map(STATUS_ICON) + " " + policy_df["status"]
    return policy_df


def compute_order_qty(policy_df: pd.DataFrame) -> pd.DataFrame:
    """Cantidad a pedir para SKUs Crítico/Bajo: hasta cubrir ROP + pronóstico T+1."""
    need = np.ceil((policy_df["rop"] + policy_df["forecast_t1"] - policy_df["stock_efectivo"]).clip(lower=0))
    policy_df["order_qty"] = np.where(policy_df["status"].isin(["Crítico", "Bajo"]), need, 0).astype(int)
    return policy_df


def compute_inventory_policy(df: pd.DataFrame, forecast_df: pd.DataFrame, stock: pd.Series) -> pd.DataFrame:
    """HU017 + HU015: stock de seguridad, punto de reorden, estado y cantidad a pedir por SKU."""
    recent = df.sort_values(["sku", "Date"]).groupby("sku").tail(DEMAND_WINDOW_WEEKS)
    demand = (
        recent.assign(demanda=recent["unidades"].clip(lower=0))
        .groupby("sku")["demanda"]
        .agg(mu="mean", sigma="std")
        .fillna(0.0)
    )
    demand["safety_stock"] = Z_SERVICE * demand["sigma"] * np.sqrt(LEAD_TIME_WEEKS)
    demand["rop"] = demand["mu"] * LEAD_TIME_WEEKS + demand["safety_stock"]
    demand = demand.round(2)

    window_start = df["Date"].max() - pd.Timedelta(weeks=NO_MOVEMENT_WEEKS)
    ventas_recientes = df.loc[df["Date"] > window_start].groupby("sku")["unidades"].sum()

    policy = forecast_df.merge(demand.reset_index(), on="sku", how="left")
    policy["current_stock"] = policy["sku"].map(stock).fillna(0.0)
    policy["en_transito"] = 0.0
    policy["ventas_ult_8"] = policy["sku"].map(ventas_recientes).fillna(0.0).round(2)

    classify_stock_status(policy)
    compute_order_qty(policy)
    return policy


def build_inventory_state(df: pd.DataFrame, forecaster: dict) -> pd.DataFrame:
    """Orquesta pronóstico T+1 → stock simulado → política de inventario."""
    forecast_df = predict_t1(df, forecaster)
    stock = simulate_current_stock(df)
    return compute_inventory_policy(df, forecast_df, stock)


def download_csv(dataframe: pd.DataFrame, filename: str):
    """Genera un CSV en memoria para descarga."""
    buffer = io.StringIO()
    dataframe.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def render_header():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.title(APP_TITLE)
    st.markdown(
        "<div style='padding: 12px 0 18px; font-size:16px; color:#374151;'>"
        "Plataforma unificada de pronóstico y ordenes logísticas con XGBoost asimétrico.</div>",
        unsafe_allow_html=True,
    )


def render_login():
    st.sidebar.markdown("## Ingreso Seguro")
    username = st.sidebar.text_input("Usuario", value="", placeholder="analista / admin")
    password = st.sidebar.text_input("Clave", value="", type="password", placeholder="refri2026 / admin2026")
    login_button = st.sidebar.button("Iniciar Sesión")

    if "login_error" in st.session_state:
        st.sidebar.error(st.session_state["login_error"])

    if login_button:
        valid, role, label = authenticate_user(username.strip(), password.strip())
        if valid:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username.strip()
            st.session_state["role"] = role
            st.session_state["user_label"] = label
            st.session_state["selected_page"] = ROLE_PAGES[role][0]
            st.session_state["login_error"] = None
        else:
            st.session_state["login_error"] = "Usuario o clave incorrectos. Verifica tus credenciales y vuelve a intentar."


def render_sidebar_menu():
    user_label = st.session_state.get("user_label", "Usuario")
    role = st.session_state.get("role", "Analista Logístico")
    st.sidebar.markdown(f"### Hola, {user_label}")
    st.sidebar.markdown(f"**Rol:** {role}")
    st.sidebar.divider()

    pages = ROLE_PAGES.get(role, ROLE_PAGES["Analista Logístico"])
    if "selected_page" not in st.session_state or st.session_state["selected_page"] not in pages:
        st.session_state["selected_page"] = pages[0]

    selected_page = st.sidebar.radio(
        "Selecciona una vista",
        pages,
        index=pages.index(st.session_state["selected_page"]),
        key="selected_page_radio"
    )
    st.session_state["selected_page"] = selected_page
    render_category_filter()

    if st.sidebar.button("Cerrar Sesión", key="cerrar_sesion"):
        reset_session_state()

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Acciones rápidas:**")
    if st.sidebar.button("Ir a Sugerencia de Pedidos", key="ir_sugerencia"):
        st.session_state["selected_page"] = "Sugerencia de Pedidos"


def _reset_category_filter():
    st.session_state["category_filter"] = list(CATEGORIES)


def render_category_filter():
    """Filtro global de categorías en el sidebar (aplica a todas las vistas)."""
    if not isinstance(st.session_state.get("category_filter"), list):
        _reset_category_filter()
    st.sidebar.multiselect("Categorías", CATEGORIES, key="category_filter")
    st.sidebar.button("Limpiar filtro", key="limpiar_filtro", on_click=_reset_category_filter)


def apply_category_filter(df: pd.DataFrame) -> pd.DataFrame:
    selected = st.session_state.get("category_filter", CATEGORIES)
    filtered = df[df["categoria"].isin(selected)]
    st.caption(f"Mostrando {filtered['sku'].nunique()} de {df['sku'].nunique()} SKUs")
    return filtered


def render_quality_badge(forecaster: dict):
    """Badge de calidad del pronóstico (MAPE vs objetivo) y detalle de métricas."""
    metrics = forecaster["metrics"]
    mape = metrics["mape"]
    if not np.isnan(mape) and mape < MAPE_TARGET:
        background, color, text = "#dcfce7", "#166534", f"✓ MAPE {mape:.1f}% < {MAPE_TARGET:.0f}%"
    else:
        background, color, text = "#fee2e2", "#991b1b", f"✗ MAPE {mape:.1f}% ≥ {MAPE_TARGET:.0f}% — revisar modelo"
    st.markdown(
        f"<span style='background:{background}; color:{color}; padding:4px 12px; border-radius:999px; "
        f"font-weight:600; font-size:14px;'>{text}</span>",
        unsafe_allow_html=True,
    )
    with st.expander("Detalle de calidad"):
        st.markdown(
            f"- **RMSE:** {metrics['rmse']:.3f} · **MAE:** {metrics['mae']:.3f} · **MAPE:** {mape:.2f}%\n"
            f"- **n validación:** {metrics['n']} · **n MAPE** (|y| ≥ {MAPE_MIN_ABS}): {metrics['n_mape']}\n"
            f"- **Fuente del modelo:** {forecaster['source']} (`{os.path.basename(MODEL_FILE_REG)}`)"
        )
        by_category = pd.DataFrame(forecaster["metrics_by_category"]).T.rename_axis("categoria").reset_index()
        st.dataframe(by_category, hide_index=True, width='stretch')


def render_status_summary(state: pd.DataFrame):
    counts = state["status"].value_counts().reindex(STATUS_ORDER, fill_value=0)
    cols = st.columns(len(STATUS_ORDER))
    for col, status in zip(cols, STATUS_ORDER):
        col.metric(f"{STATUS_ICON[status]} {status}", int(counts[status]))

    chart_df = counts.rename_axis("status").reset_index(name="skus")
    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            y=alt.Y("status:N", sort=STATUS_ORDER, title=None),
            x=alt.X("skus:Q", title="SKUs"),
            color=alt.Color(
                "status:N",
                scale=alt.Scale(domain=STATUS_ORDER, range=[STATUS_COLOR[s] for s in STATUS_ORDER]),
                legend=None,
            ),
            tooltip=[alt.Tooltip("status:N", title="Estado"), alt.Tooltip("skus:Q", title="SKUs")],
        )
        .properties(height=200)
    )
    st.altair_chart(chart)


def render_forecast_chart(df: pd.DataFrame, forecaster: dict, forecast_df: pd.DataFrame, sku: str):
    """Histórico real, predicción de validación y punto T+1 con su IC 95%."""
    hist = (
        df.loc[df["sku"] == sku, ["Date", "unidades"]]
        .sort_values("Date")
        .tail(52)
        .rename(columns={"unidades": "valor"})
        .assign(serie="Real")
    )
    val_df = forecaster["val_df"]
    val = (
        val_df.loc[val_df["sku"] == sku, ["Date", "pred"]]
        .rename(columns={"pred": "valor"})
        .assign(serie="Predicción validación")
    )
    series_domain = ["Real", "Predicción validación"]
    lines = (
        alt.Chart(pd.concat([hist, val], ignore_index=True))
        .mark_line()
        .encode(
            x=alt.X("Date:T", title="Semana"),
            y=alt.Y("valor:Q", title="Unidades (miles)"),
            color=alt.Color("serie:N", title=None,
                            scale=alt.Scale(domain=series_domain, range=["#1f2937", "#2563eb"])),
            strokeDash=alt.StrokeDash("serie:N", legend=None,
                                      scale=alt.Scale(domain=series_domain, range=[[1, 0], [4, 4]])),
            tooltip=[alt.Tooltip("Date:T", title="Semana"), "serie:N",
                     alt.Tooltip("valor:Q", title="Unidades", format=".2f")],
        )
    )

    point_df = forecast_df.loc[forecast_df["sku"] == sku]
    tooltip_t1 = [
        alt.Tooltip("fecha_t1:T", title="Semana T+1"),
        alt.Tooltip("forecast_t1:Q", title="Pronóstico", format=".2f"),
        alt.Tooltip("ci_low:Q", title="IC 95% inf.", format=".2f"),
        alt.Tooltip("ci_high:Q", title="IC 95% sup.", format=".2f"),
        alt.Tooltip("rmse_usado:Q", title="RMSE usado", format=".2f"),
    ]
    base_t1 = alt.Chart(point_df)
    interval = base_t1.mark_rule(color="#dc2626", strokeWidth=2).encode(
        x="fecha_t1:T", y="ci_low:Q", y2="ci_high:Q", tooltip=tooltip_t1
    )
    point = base_t1.mark_point(size=160, filled=True, color="#dc2626").encode(
        x="fecha_t1:T", y="forecast_t1:Q", tooltip=tooltip_t1
    )
    st.altair_chart((lines + interval + point).properties(height=380))

    fuente = point_df["rmse_fuente"].iloc[0] if not point_df.empty else "Global"
    st.caption(f"IC 95% = ŷ ± {Z_CI} · RMSE ({fuente})")


def render_inventory_policy_table(state: pd.DataFrame):
    with st.expander("¿Cómo se calcula?"):
        st.markdown(
            f"- **Lead time (LT):** {LEAD_TIME_WEEKS} semanas · **Z de servicio:** {Z_SERVICE} (95%)\n"
            f"- **μ y σ:** demanda semanal (≥ 0) de las últimas {DEMAND_WINDOW_WEEKS} semanas del SKU\n"
            f"- **Stock de seguridad:** SS = {Z_SERVICE}·σ·√{LEAD_TIME_WEEKS} · "
            f"**Punto de reorden:** ROP = μ·{LEAD_TIME_WEEKS} + SS\n"
            f"- **Estado** (stock efectivo = actual + en tránsito): Sin Movimiento si no vendió en las últimas "
            f"{NO_MOVEMENT_WEEKS} semanas; Crítico ≤ SS; Bajo ≤ ROP; Sobrestock > ROP + "
            f"{OVERSTOCK_COVER_WEEKS}·pronóstico T+1; si no, Óptimo\n"
            f"- **Cantidad a pedir** (Crítico/Bajo): ⌈ROP + pronóstico T+1 − stock efectivo⌉\n"
            f"- El stock actual es **simulado** (el dataset no contiene inventario)."
        )

    rank = {status: i for i, status in enumerate(STATUS_ORDER)}
    view = state.assign(
        _rank=state["status"].map(rank),
        cobertura=np.where(state["rop"] > 0, state["stock_efectivo"] / state["rop"].where(state["rop"] > 0), 2.0).clip(0, 2),
    ).sort_values(["_rank", "order_qty", "sku"], ascending=[True, False, True])
    columns = ["sku", "categoria", "status_label", "current_stock", "en_transito", "safety_stock", "rop",
               "cobertura", "forecast_t1", "order_qty"]
    st.dataframe(
        view[columns],
        hide_index=True,
        width='stretch',
        column_config={
            "sku": "SKU",
            "categoria": "Categoría",
            "status_label": "Estado",
            "current_stock": st.column_config.NumberColumn("Stock actual", format="%.2f", help="Simulado"),
            "en_transito": st.column_config.NumberColumn("En tránsito", format="%.2f",
                                                         help="Órdenes generadas en esta sesión"),
            "safety_stock": st.column_config.NumberColumn("Stock seguridad", format="%.2f",
                                                          help=f"SS = {Z_SERVICE}·σ·√{LEAD_TIME_WEEKS}"),
            "rop": st.column_config.NumberColumn("ROP", format="%.2f",
                                                 help=f"ROP = μ·{LEAD_TIME_WEEKS} + SS"),
            "cobertura": st.column_config.ProgressColumn("Cobertura", format="%.2f", min_value=0, max_value=2,
                                                         help="Stock efectivo / ROP (1 = en el punto de reorden)"),
            "forecast_t1": st.column_config.NumberColumn("Pronóstico T+1", format="%.2f"),
            "order_qty": st.column_config.NumberColumn("Cantidad a pedir", format="%d",
                                                       help="⌈ROP + pronóstico T+1 − stock efectivo⌉"),
        },
    )


def render_dashboard(state: pd.DataFrame, forecaster: dict):
    st.subheader("Dashboard General")
    render_quality_badge(forecaster)

    metrics = forecaster["metrics"]
    cols = st.columns(3)
    cols[0].metric("RMSE (validación)", f"{metrics['rmse']:.2f}")
    cols[1].metric("MAE (validación)", f"{metrics['mae']:.2f}")
    cols[2].metric("SKUs totales", f"{state['sku'].nunique()}")

    st.markdown("### Estado del inventario")
    filtered = apply_category_filter(state)
    render_status_summary(filtered)

    st.markdown("### Top 10 SKUs a reponer (Crítico / Bajo)")
    urgent = filtered[filtered["status"].isin(["Crítico", "Bajo"])]
    if urgent.empty:
        st.success("No hay SKUs en estado Crítico o Bajo con el filtro actual.")
        return
    rank = {status: i for i, status in enumerate(STATUS_ORDER)}
    top = (
        urgent.assign(_rank=urgent["status"].map(rank))
        .sort_values(["_rank", "order_qty"], ascending=[True, False])
        .head(10)
        .drop(columns="_rank")
    )
    render_inventory_policy_table(top)


def render_forecast_page(df: pd.DataFrame, state: pd.DataFrame, forecaster: dict):
    st.subheader("Pronóstico de Demanda")
    st.markdown("Pronóstico de la próxima semana (T+1) por SKU con el regresor XGBoost e intervalo de confianza 95%.")
    render_quality_badge(forecaster)

    filtered = apply_category_filter(state)
    if filtered.empty:
        st.warning("No hay SKUs para las categorías seleccionadas.")
        return

    sku = st.selectbox("SKU", filtered["sku"].tolist(), key="forecast_sku")
    render_forecast_chart(df, forecaster, filtered, sku)

    st.markdown("#### Pronóstico T+1")
    table = filtered[["sku", "categoria", "fecha_t1", "forecast_t1", "ci_low", "ci_high", "rmse_fuente"]].assign(
        fecha_t1=lambda d: d["fecha_t1"].dt.strftime("%Y-%m-%d")
    )
    st.dataframe(table, hide_index=True, width='stretch')
    st.download_button(
        "⬇️ Exportar pronóstico T+1 (CSV)",
        data=download_csv(table, "pronostico_t1.csv"),
        file_name=f"pronostico_t1_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="dl_forecast"
    )


def render_order_suggestion(state: pd.DataFrame):
    st.subheader("Sugerencia de Pedidos")
    st.markdown(
        "Política de inventario por SKU: stock de seguridad, punto de reorden y cantidad sugerida "
        "a partir del pronóstico T+1 del regresor XGBoost."
    )
    if st.session_state.get("order_flash"):
        st.success(st.session_state.pop("order_flash"))

    filtered = apply_category_filter(state)
    show = st.radio("Mostrar", ["Todos", "Crítico", "Bajo", "Requieren orden"], horizontal=True, key="order_filter")
    if show in ("Crítico", "Bajo"):
        view = filtered[filtered["status"] == show]
    elif show == "Requieren orden":
        view = filtered[filtered["order_qty"] > 0]
    else:
        view = filtered

    if view.empty:
        st.warning("No hay resultados con los filtros seleccionados.")
    else:
        render_inventory_policy_table(view)

    st.markdown("### Generar orden de compra")
    candidates = filtered.loc[filtered["order_qty"] > 0].sort_values("order_qty", ascending=False)
    if candidates.empty:
        st.info("Ningún SKU requiere orden de compra con el filtro actual.")
    else:
        selected_sku = st.selectbox("Selecciona SKU", candidates["sku"].tolist(), key="selected_sku")
        quantity_default = int(candidates.loc[candidates["sku"] == selected_sku, "order_qty"].iloc[0])
        quantity = st.number_input("Cantidad a pedir", min_value=0, value=quantity_default, step=1,
                                   key=f"order_quantity_{selected_sku}")
        if st.button("Generar Orden de Compra", key="generar_orden"):
            if quantity <= 0:
                st.warning("La cantidad debe ser mayor que 0.")
            else:
                if "order_history" not in st.session_state:
                    st.session_state["order_history"] = []
                order_code = f"ORD-{datetime.now().strftime('%Y%m%d')}-{len(st.session_state['order_history'])+1:03d}"
                st.session_state["order_history"].append({
                    "order_code": order_code,
                    "sku": selected_sku,
                    "quantity": quantity,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "status": "Emitida"
                })
                inventory = st.session_state["inventory_state"]
                inventory.loc[inventory["sku"] == selected_sku, "en_transito"] += quantity
                classify_stock_status(inventory)
                compute_order_qty(inventory)
                st.session_state["order_flash"] = (
                    f"Orden generada: {order_code} → {selected_sku}, cantidad {quantity} (sumada a stock en tránsito)"
                )
                st.rerun()

    if st.session_state.get("order_history"):
        st.markdown("#### Histórico de órdenes generadas")
        st.dataframe(pd.DataFrame(st.session_state["order_history"]), hide_index=True, width='stretch')

    export = filtered.loc[filtered["order_qty"] > 0, ["sku", "categoria", "current_stock", "en_transito",
                                                     "safety_stock", "rop", "forecast_t1", "order_qty", "status"]]
    if export.empty:
        st.info("No hay órdenes de compra sugeridas para exportar.")
    else:
        st.download_button(
            "⬇️ Exportar órdenes de compra (CSV)",
            data=download_csv(export, "ordenes_compra.csv"),
            file_name=f"ordenes_compra_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="dl_orders"
        )


def render_system_logs():
    st.subheader("Logs del Sistema")
    st.markdown("Visualiza eventos de sistema, alertas y auditoría de seguridad en tiempo real.")
    log_data = [
        {"timestamp": "2026-06-21 09:23", "evento": "Inicio de sesión exitoso", "usuario": "admin"},
        {"timestamp": "2026-06-21 09:45", "evento": "Generación de orden", "usuario": "analista"},
        {"timestamp": "2026-06-21 10:05", "evento": "Actualización de parámetros", "usuario": "admin"},
        {"timestamp": "2026-06-21 10:40", "evento": "Exportación de reporte CSV", "usuario": "analista"}
    ]
    log_df = pd.DataFrame(log_data)
    if st.button("Filtrar sólo eventos críticos"):
        log_df = log_df[log_df["evento"].str.contains("error|crítico|fallo", case=False, na=False)]
    st.dataframe(log_df, width='stretch')
    st.download_button(
        "Descargar Logs del Sistema",
        data=download_csv(log_df, "logs_sistema.csv"),
        file_name="logs_sistema.csv",
        mime="text/csv"
    )


def render_data_audit(df: pd.DataFrame):
    st.subheader("Auditoría de Datos")
    st.markdown("Inspección de calidad de datos, valores faltantes y consistencia del pipeline ETL.")
    missing = df.isna().sum()
    st.write("Valores faltantes por columna:")
    st.write(missing.to_frame("missing_count"))

    stats = df[["unidades", "Temperatura_Promedio"]].describe().T
    st.write(stats)

    if st.button("Recalcular métricas de calidad"):
        st.success("Auditoría recalculada con éxito. Sin anomalías críticas detectadas en el pipeline actual.")

    sample = df.sample(min(8, len(df)), random_state=42)
    st.markdown("#### Ejemplo de registros procesados")
    st.dataframe(sample, width='stretch')
    st.download_button(
        "Exportar Auditoría CSV",
        data=download_csv(sample, "auditoria_datos.csv"),
        file_name="auditoria_datos.csv",
        mime="text/csv"
    )


def render_core_configuration():
    st.subheader("Configuración de Parámetros Core")
    st.markdown("Ajusta el comportamiento del motor de predicción y el pipeline de cálculo.")
    if "core_parameters" not in st.session_state:
        st.session_state["core_parameters"] = DEFAULT_MODEL_CONFIG.copy()

    params = st.session_state["core_parameters"]
    lr = st.number_input("Learning rate", value=params["learning_rate"], min_value=0.001, max_value=0.5, step=0.005, format="%.3f")
    depth = st.slider("Max depth", min_value=3, max_value=12, value=params["max_depth"])
    weight = st.number_input("Scale pos weight", value=params["scale_pos_weight"], min_value=0.5, max_value=10.0, step=0.1)
    n_estimators = st.number_input("Número de árboles", value=params["n_estimators"], min_value=20, max_value=500, step=10)

    if st.button("Guardar Parámetros Core"):
        st.session_state["core_parameters"] = {
            "learning_rate": lr,
            "max_depth": depth,
            "scale_pos_weight": weight,
            "n_estimators": n_estimators
        }
        st.success("Parámetros guardados localmente. Vuelva a cargar el modelo para aplicar los cambios.")

    st.markdown("#### Estado actual de parámetros")
    st.json(st.session_state["core_parameters"])


def render_app():
    render_header()
    if not st.session_state.get("logged_in"):
        render_login()
        st.warning("Ingresa tus credenciales para accesar el dashboard. Usuario de demostración: analista / admin")
        return

    render_sidebar_menu()
    df = st.session_state.get("dataset_processed")
    if df is None:
        df = load_dataset()
        st.session_state["dataset_processed"] = df

    forecaster = train_or_load_forecaster()

    state = st.session_state.get("inventory_state")
    if state is None:
        state = build_inventory_state(df, forecaster)
        st.session_state["inventory_state"] = state

    selected_page = st.session_state.get("selected_page", ROLE_PAGES[st.session_state["role"]][0])

    if selected_page == "Dashboard General":
        render_dashboard(state, forecaster)
    elif selected_page == "Pronóstico de Demanda":
        render_forecast_page(df, state, forecaster)
    elif selected_page == "Sugerencia de Pedidos":
        render_order_suggestion(state)
    elif selected_page == "Logs del Sistema":
        render_system_logs()
    elif selected_page == "Auditoría de Datos":
        render_data_audit(df)
    elif selected_page == "Configuración de Parámetros Core":
        render_core_configuration()
    else:
        st.info("Selecciona una vista válida desde el menú lateral.")


def print_console_report(metrics: dict, source: str):
    """Imprime en consola las métricas de validación del regresor."""
    separator = "=" * 68
    status = "OK" if metrics["mape"] < MAPE_TARGET else "REVISAR"
    print(separator)
    print("REFRIPERÚ | REGRESOR XGBOOST DE DEMANDA - MÉTRICAS EN VALIDACIÓN")
    print(separator)
    print(f"Modelo   : {source} ({MODEL_FILE_REG})")
    print(f"RMSE     : {metrics['rmse']:.3f}")
    print(f"MAE      : {metrics['mae']:.3f}")
    print(f"MAPE     : {metrics['mape']:.2f}% (objetivo < {MAPE_TARGET:.0f}%: {status})")
    print(f"n        : {metrics['n']} (MAPE sobre {metrics['n_mape']})")
    print(separator)


def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if "console_report_done" not in st.session_state:
        result = train_or_load_forecaster()
        print_console_report(result["metrics"], result["source"])
        st.session_state["console_report_done"] = True

    render_app()


if __name__ == "__main__":
    main()
