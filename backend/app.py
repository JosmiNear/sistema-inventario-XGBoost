"""
RefriPerú - Backend Flask
Sistema de Gestión de Inventarios y Pronóstico de Demanda con ML

Estructura:
- app.py: Este archivo (servidor principal)
- requirements.txt: Dependencias de Python
- models/: Modelos XGBoost entrenados
- data/: Datos históricos y predicciones

Ejecutar: python app.py
API disponible en: http://localhost:5000/api
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
from io import BytesIO

# ===== Inicialización =====
app = Flask(__name__)
CORS(app)

# Configuración
app.config['JSON_SORT_KEYS'] = False
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'

# ===== Datos Simulados (Reemplazar con Base de Datos Real) =====
class DataStore:
    """Simulación de base de datos en memoria"""
    
    dashboard_data = {
        "total_skus": 248,
        "service_level": 94.2,
        "critical_alerts": 5,
        "opportunity_cost": 125340.50,
        "active_branches": 4,
        "branches": ["Lima", "Piura", "Trujillo", "Arequipa"]
    }

    categories = {
        "climatizacion": {"name": "Climatización", "count": 85},
        "refrigeracion": {"name": "Refrigeración", "count": 92},
        "ventilacion": {"name": "Ventilación", "count": 45},
        "componentes": {"name": "Componentes", "count": 26}
    }

    skus = [
        {
            "sku": "RFC-001",
            "description": "Aire Acondicionado Split 12K BTU",
            "category": "climatizacion",
            "current_stock": 18,
            "forecast_t1": 45,
            "status": "warning"
        },
        {
            "sku": "RFC-002",
            "description": "Aire Acondicionado Split 18K BTU",
            "category": "climatizacion",
            "current_stock": 32,
            "forecast_t1": 28,
            "status": "safe"
        },
        {
            "sku": "RFC-003",
            "description": "Compresor R410A 1.5HP",
            "category": "refrigeracion",
            "current_stock": 8,
            "forecast_t1": 35,
            "status": "critical"
        },
        {
            "sku": "RFC-004",
            "description": "Ventilador Industrial 36\"",
            "category": "ventilacion",
            "current_stock": 22,
            "forecast_t1": 18,
            "status": "safe"
        },
        {
            "sku": "RFC-005",
            "description": "Filtro HEPA Industrial",
            "category": "componentes",
            "current_stock": 5,
            "forecast_t1": 42,
            "status": "critical"
        },
    ]

    orders_history = []

    @classmethod
    def calculate_order_qty(cls, sku_code):
        """Lógica prescriptiva: Calcular cantidad óptima a pedir"""
        for sku in cls.skus:
            if sku['sku'] == sku_code:
                suggested = max(0, sku['forecast_t1'] - sku['current_stock'])
                return suggested
        return 0


# ===== ENDPOINTS API =====

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check del servidor"""
    return jsonify({
        "status": "ok",
        "service": "RefriPeru Dashboard API",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """GET /api/dashboard/summary - Obtener resumen del dashboard"""
    return jsonify({
        **DataStore.dashboard_data,
        "timestamp": datetime.now().isoformat(),
        "model_status": "optimal",
        "last_update": (datetime.now() - timedelta(minutes=15)).isoformat()
    }), 200


@app.route('/api/forecast/demand', methods=['GET'])
def get_demand_forecast():
    """GET /api/forecast/demand - Obtener pronóstico de demanda XGBoost"""
    
    category = request.args.get('category', 'all')
    months = request.args.get('months', 13, type=int)
    
    # Datos simulados del modelo (Backend: Reemplazar con predicciones reales de XGBoost)
    labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic', 'Próx']
    real_demand = [1200, 1300, 1400, 1150, 950, 850, 700, 650, 750, 1050, 1350, 1450, 1400]
    predicted_demand = [1250, 1280, 1350, 1200, 1000, 900, 720, 680, 800, 1100, 1380, 1470, 1420]
    
    # Calcular intervalo de confianza (±15%)
    confidence_upper = [int(p * 1.15) for p in predicted_demand]
    confidence_lower = [int(p * 0.85) for p in predicted_demand]
    
    return jsonify({
        "category": category,
        "labels": labels[:months],
        "real_demand": real_demand[:months],
        "predicted_demand": predicted_demand[:months],
        "confidence_upper": confidence_upper[:months],
        "confidence_lower": confidence_lower[:months],
        "model_info": {
            "name": "XGBoost v2.0 - Asymmetric Loss",
            "mape": 12.3,
            "rmse": 45.2,
            "asymmetric_penalty_ratio": 2.5,  # Penaliza más los subestimados
            "last_trained": (datetime.now() - timedelta(days=1)).isoformat(),
            "training_samples": 2400,
            "features": 18
        },
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/api/orders/suggestions', methods=['GET'])
def get_suggested_orders():
    """GET /api/orders/suggestions - Obtener órdenes sugeridas prescriptivas"""
    
    category = request.args.get('category', 'all')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    # Filtrar SKUs por categoría
    filtered_skus = DataStore.skus
    if category != 'all':
        filtered_skus = [s for s in DataStore.skus if s['category'] == category]
    
    # Calcular órdenes sugeridas
    items = []
    for sku in filtered_skus:
        suggested_qty = DataStore.calculate_order_qty(sku['sku'])
        
        # Mapear estado
        if sku['status'] == 'critical':
            badge_status = 'danger'
        elif sku['status'] == 'warning':
            badge_status = 'warning'
        else:
            badge_status = 'success'
        
        items.append({
            "sku": sku['sku'],
            "description": sku['description'],
            "category": DataStore.categories[sku['category']]['name'],
            "category_code": sku['category'],
            "current_stock": sku['current_stock'],
            "forecast_t1": sku['forecast_t1'],
            "suggested_order": suggested_qty,
            "status": badge_status,
            "mape": round(12.3 + (hash(sku['sku']) % 10), 1),  # MAPE por SKU
            "confidence": "Alta" if suggested_qty > 0 else "Muy Alta"
        })
    
    # Paginación
    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    paginated_items = items[start:end]
    
    return jsonify({
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "items": paginated_items,
        "summary": {
            "total_to_order": sum(item['suggested_order'] for item in items),
            "critical_count": len([i for i in items if i['status'] == 'danger']),
            "warning_count": len([i for i in items if i['status'] == 'warning'])
        }
    }), 200


@app.route('/api/orders/create', methods=['POST'])
def create_order():
    """POST /api/orders/create - Crear nueva orden de compra"""
    
    data = request.get_json()
    
    # Validación
    if not data or not data.get('sku') or not data.get('quantity'):
        return jsonify({
            "error": "Campos requeridos: sku, quantity",
            "timestamp": datetime.now().isoformat()
        }), 400
    
    # Validar que el SKU existe
    sku_found = next((s for s in DataStore.skus if s['sku'] == data['sku']), None)
    if not sku_found:
        return jsonify({"error": f"SKU {data['sku']} no encontrado"}), 404
    
    # Crear orden
    order_id = f"ORD-{datetime.now().strftime('%Y-%m-%d')}-{len(DataStore.orders_history) + 1:04d}"
    
    order = {
        "order_id": order_id,
        "status": "created",
        "sku": data['sku'],
        "quantity": int(data['quantity']),
        "supplier": data.get('supplier', 'Sin especificar'),
        "notes": data.get('notes', ''),
        "created_at": datetime.now().isoformat(),
        "estimated_arrival": (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
        "cost_per_unit": 300.00,  # Ejemplo
        "total_cost": int(data['quantity']) * 300.00
    }
    
    DataStore.orders_history.append(order)
    
    return jsonify(order), 201


@app.route('/api/skus/search', methods=['GET'])
def search_skus():
    """GET /api/skus/search?q=query - Buscar SKUs por código o descripción"""
    
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify({"results": []}), 200
    
    results = []
    for sku in DataStore.skus:
        if query in sku['sku'].lower() or query in sku['description'].lower():
            results.append({
                "sku": sku['sku'],
                "description": sku['description'],
                "category": DataStore.categories[sku['category']]['name'],
                "current_stock": sku['current_stock'],
                "status": sku['status']
            })
    
    return jsonify({
        "query": query,
        "results": results,
        "count": len(results)
    }), 200


@app.route('/api/skus/history', methods=['GET'])
def get_stock_history():
    """GET /api/skus/history?sku=CODE&days=30 - Obtener historial de stock"""
    
    sku_code = request.args.get('sku', '')
    days = request.args.get('days', 30, type=int)
    
    # Generar datos simulados históricos
    history = []
    for i in range(days, 0, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        history.append({
            "date": date,
            "stock": max(1, 18 - i + (hash(date) % 10)),
            "sales": hash(date) % 15,
            "orders": 0 if i > 5 else 25
        })
    
    return jsonify({
        "sku": sku_code,
        "days": days,
        "history": history
    }), 200


@app.route('/api/system/logs', methods=['GET'])
def get_system_logs():
    """GET /api/system/logs?level=all&limit=100 - Obtener logs del sistema"""
    
    level = request.args.get('level', 'all')
    limit = request.args.get('limit', 100, type=int)
    
    # Logs simulados
    logs = [
        {
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "level": "INFO",
            "message": "Modelo XGBoost ejecutado exitosamente",
            "module": "forecast"
        },
        {
            "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
            "level": "INFO",
            "message": "Órdenes sugeridas actualizadas",
            "module": "prescriptive"
        },
        {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": "Dashboard inicializado",
            "module": "api"
        },
    ]
    
    return jsonify({
        "level": level,
        "total": len(logs),
        "logs": logs[:limit]
    }), 200


@app.route('/api/model/metrics', methods=['GET'])
def get_model_metrics():
    """GET /api/model/metrics - Obtener métricas del modelo ML"""
    
    return jsonify({
        "model_version": "2.0",
        "algorithm": "XGBoost with Asymmetric Loss",
        "mape_global": 12.3,
        "rmse_global": 45.2,
        "mae_global": 38.7,
        "accuracy_by_category": {
            "climatizacion": {"mape": 11.5, "samples": 85},
            "refrigeracion": {"mape": 12.8, "samples": 92},
            "ventilacion": {"mape": 12.1, "samples": 45},
            "componentes": {"mape": 8.9, "samples": 26}
        },
        "training_info": {
            "last_training": (datetime.now() - timedelta(days=1)).isoformat(),
            "next_training": (datetime.now() + timedelta(days=1)).isoformat(),
            "training_duration_seconds": 245,
            "samples_trained": 2400,
            "features_used": 18
        },
        "asymmetric_penalty": {
            "underestimate_ratio": 2.5,
            "overestimate_ratio": 1.0,
            "rationale": "Penaliza más subestimaciones (quiebres) que sobreestimaciones (exceso)"
        }
    }), 200


@app.route('/api/reports/export', methods=['GET'])
def export_report():
    """GET /api/reports/export?format=excel&type=orders - Exportar reporte"""
    
    report_format = request.args.get('format', 'excel')
    report_type = request.args.get('type', 'orders')
    
    # Simulación: Generar CSV (en producción usar openpyxl, reportlab, etc.)
    if report_format == 'excel' or report_format == 'csv':
        csv_content = "SKU,Descripción,Stock Actual,Pronóstico,Cantidad Sugerida\n"
        for sku in DataStore.skus:
            suggested = DataStore.calculate_order_qty(sku['sku'])
            csv_content += f"{sku['sku']},{sku['description']},{sku['current_stock']},{sku['forecast_t1']},{suggested}\n"
        
        file_bytes = BytesIO(csv_content.encode())
        filename = f"reporte_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    else:
        return jsonify({"error": "Formato no soportado"}), 400
    
    return send_file(
        file_bytes,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/orders/history', methods=['GET'])
def get_orders_history():
    """GET /api/orders/history - Obtener historial de órdenes creadas"""
    
    limit = request.args.get('limit', 50, type=int)
    
    return jsonify({
        "total": len(DataStore.orders_history),
        "orders": DataStore.orders_history[-limit:]
    }), 200


# ===== Error Handlers =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint no encontrado",
        "status_code": 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Error interno del servidor",
        "status_code": 500,
        "message": str(error)
    }), 500


# ===== Ejecución =====

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║         RefriPerú - Dashboard API Backend                  ║
    ║         Flask Server - Development Mode                    ║
    ╚════════════════════════════════════════════════════════════╝
    
    🚀 Servidor iniciando en: http://localhost:5000
    📋 Documentación de API: Consultar docs/INTEGRATION_GUIDE.md
    
    Endpoints disponibles:
    - GET  /api/health                  - Health check
    - GET  /api/dashboard/summary       - Resumen del dashboard
    - GET  /api/forecast/demand         - Pronóstico XGBoost
    - GET  /api/orders/suggestions      - Órdenes sugeridas
    - POST /api/orders/create           - Crear nueva orden
    - GET  /api/skus/search            - Buscar SKUs
    - GET  /api/system/logs             - Logs del sistema
    - GET  /api/model/metrics           - Métricas del modelo
    """)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
