# 🎯 RefriPerú Dashboard - Sistema de Gestión Inteligente de Inventarios

**Panel de Control Profesional para Pronóstico de Demanda y Gestión de Inventarios con Machine Learning (XGBoost)**

---

## 📋 Descripción General

RefriPerú Dashboard es una aplicación web moderna diseñada para el sector HVAC (Ventilación, Refrigeración y Climatización) que integra:

✅ **Machine Learning Avanzado:** Modelo XGBoost con pérdida asimétrica para pronósticos más precisos  
✅ **Prescriptivo de Demanda:** Sugerencias automáticas de cantidades óptimas a pedir  
✅ **Análisis en Tiempo Real:** KPIs dinámicos y alertas de quiebre de stock  
✅ **Interfaz Moderna:** Diseño profesional emulando sistemas ERP enterprise  
✅ **100% Responsivo:** Funciona en Desktop, Tablet y Mobile  

---

## 🚀 Inicio Rápido

### Opción 1: Ejecutar Solo el Frontend (sin backend)

1. **Descarga el archivo `dashboard.html`**
2. **Abre en navegador:**
   ```bash
   # Windows
   start dashboard.html
   
   # macOS
   open dashboard.html
   
   # Linux
   firefox dashboard.html
   ```
   
✅ Verás el dashboard con datos simulados listos para integración.

---

### Opción 2: Setup Completo (Frontend + Backend Flask)

#### **Requisitos:**
- Python 3.9+
- Node.js 16+ (opcional, si quieres servir estáticos)
- Git

#### **Paso 1: Clonar/Descargar el Proyecto**
```bash
cd RefriPeru
```

#### **Paso 2: Configurar Backend**

```bash
# Navegar a carpeta backend
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno (Windows)
venv\Scripts\activate

# Activar entorno (macOS/Linux)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

#### **Paso 3: Ejecutar Backend**

```bash
# En la carpeta backend
python app.py
```

Salida esperada:
```
╔════════════════════════════════════════════════════════════╗
║         RefriPerú - Dashboard API Backend                  ║
║         Flask Server - Development Mode                    ║
╚════════════════════════════════════════════════════════════╝

🚀 Servidor iniciando en: http://localhost:5000
```

#### **Paso 4: Servir Frontend**

Opción A - Con servidor HTTP simple:
```bash
# Windows - En la carpeta raíz
python -m http.server 8000

# macOS/Linux
python3 -m http.server 8000
```

Opción B - Con Live Server (VS Code):
- Instala extensión "Live Server"
- Click derecho en `dashboard.html` → "Open with Live Server"

#### **Paso 5: Acceder al Dashboard**

Abre en navegador:
```
http://localhost:8000/dashboard.html
```

El dashboard ahora consultará datos reales del backend en `http://localhost:5000/api/`

---

## 📁 Estructura del Proyecto

```
RefriPeru/
├── dashboard.html              # 🎨 Frontend principal (HTML/CSS/JS)
├── README.md                   # Este archivo
├── js/
│   └── dashboard-api.js        # 🔌 Módulo API para backend
├── docs/
│   └── INTEGRATION_GUIDE.md    # 📚 Guía completa de integración
├── backend/
│   ├── app.py                  # 🐍 Servidor Flask
│   ├── requirements.txt        # 📦 Dependencias Python
│   └── models/                 # 🤖 Modelos XGBoost (futura)
└── front_ml.py                 # (Original - referencia)
```

---

## 🎨 Componentes del Dashboard

### 1. **Sidebar de Navegación**
- 6 secciones principales
- Perfil de usuario con rol
- Diseño oscuro corporativo (Slate 900)
- Indicadores de sección activa

### 2. **Topbar (Barra Superior)**
- Título dinámico de página
- Búsqueda de SKUs en tiempo real
- Selector global de categorías
- Campana de notificaciones

### 3. **KPI Cards (4 Indicadores)**
```
┌─────────────────────────────────────────┐
│ Total SKUs         │ Nivel Servicio    │
│ Monitoreados       │ 94.2% ✓ Verde     │
│ 248               │                     │
├─────────────────────────────────────────┤
│ Alertas Críticas   │ Costo Oportunidad │
│ 5 ⚠️ Rojo           │ S/ 125,340       │
└─────────────────────────────────────────┘
```

### 4. **Gráfica de Series Temporales**
- **Línea roja sólida:** Demanda real histórica (12 meses)
- **Línea azul punteada:** Predicción XGBoost (13 meses incluyendo T+1)
- **Zona grisácea:** Intervalo de confianza (±15%)
- Tooltips interactivos con valores exactos

### 5. **Tabla de Órdenes Sugeridas**
Columnas:
- SKU (código)
- Descripción del equipo
- Categoría (badge)
- Stock Actual
- Pronóstico (T+1)
- **Cantidad Sugerida** ← Prescriptivo (Forecast - Stock)
- Estado (badge dinámico: Verde/Amarillo/Rojo)
- Botón "Generar Orden" por fila

---

## 🔗 Conexión Backend-Frontend

### Variables de Template (Jinja2)

En `dashboard.html`, busca comentarios:

```html
<!-- Backend: {{ variable }} -->
```

**Ejemplos:**
```html
<!-- Backend: {{ usuario.nombre }} -->          → Nombre del usuario
<!-- Backend: {{ total_skus }} -->              → Total de SKUs
<!-- Backend: {{ service_level }}% -->          → Nivel de servicio
<!-- Backend: {% for item in ordenes_sugeridas %} --> → Loop de órdenes
```

### Reemplazar en Tu Template Flask

Si usas Jinja2:

```html
{{ usuario.nombre }}           <!-- Reemplaza comentario -->
{{ total_skus }}               <!-- Reemplaza comentario -->
{{ service_level }}%           <!-- Reemplaza comentario -->
{% for item in ordenes_sugeridas %}
    <tr>
        <td>{{ item.sku }}</td>
        <td>{{ item.description }}</td>
        <!-- ... -->
    </tr>
{% endfor %}
```

---

## 📡 API Endpoints

### Consulta rápida:

```bash
# Health check
curl http://localhost:5000/api/health

# Dashboard KPIs
curl http://localhost:5000/api/dashboard/summary

# Pronóstico XGBoost
curl http://localhost:5000/api/forecast/demand

# Órdenes sugeridas
curl http://localhost:5000/api/orders/suggestions

# Crear orden
curl -X POST http://localhost:5000/api/orders/create \
  -H "Content-Type: application/json" \
  -d '{"sku":"RFC-001", "quantity":27}'
```

**Ver documentación completa:** [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)

---

## 🎓 Uso del Módulo API (dashboard-api.js)

```javascript
// Importar en dashboard.html
<script src="js/dashboard-api.js"></script>

// Usar en código
DashboardAPI.fetchDashboardData().then(data => {
    console.log('Total SKUs:', data.total_skus);
    console.log('Nivel de Servicio:', data.service_level + '%');
});

// Crear orden
DashboardAPI.submitOrder('RFC-001', 27, 'Distribuidor A', 'Stock bajo')
    .then(order => console.log('Orden creada:', order.order_id))
    .catch(error => console.error('Error:', error));

// Exportar reporte
DashboardAPI.exportReport('excel', 'orders');
```

---

## 🔒 Seguridad

### CORS (Frontend ↔ Backend)

El backend incluye CORS habilitado en desarrollo. En **producción**, asegúrate de:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://tudominio.com"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "X-CSRF-Token"]
    }
})
```

### CSRF Token

El frontend envía tokens CSRF en headers:
```javascript
headers: {
    'X-CSRF-Token': document.querySelector('[name="csrf_token"]').value
}
```

---

## 📊 Datos Simulados vs. Reales

### Desarrollo (Datos Simulados)
- Frontend muestra datos hardcoded
- Backend retorna datos ficticios
- Perfecto para UI/UX testing

### Producción (Datos Reales)
1. Conectar base de datos real (PostgreSQL, MySQL, etc.)
2. Integrar modelo XGBoost entrenado
3. Procesar datos históricos de ventas
4. Actualizar predicciones diariamente

---

## 🚀 Deployment

### Docker

```bash
# Construir imagen
docker build -t refriperu-dashboard .

# Ejecutar contenedor
docker run -p 80:80 -p 5000:5000 refriperu-dashboard
```

### Heroku / Railway / Render

```bash
# Push a Heroku
git push heroku main

# La aplicación estará en: https://tu-app.herokuapp.com
```

---

## 🧪 Testing

### Verificar frontend sin backend:

1. Abre `dashboard.html` en navegador
2. Verifica que muestre:
   - ✅ Sidebar con 6 opciones de navegación
   - ✅ KPI cards con valores
   - ✅ Gráfica de demanda
   - ✅ Tabla de órdenes

### Verificar backend API:

```bash
# En terminal, con backend corriendo
python backend/app.py

# En otra terminal
curl http://localhost:5000/api/health
# Response: {"status": "ok", ...}
```

### Testing automático (pytest):

```bash
cd backend
pytest tests/ -v
```

---

## 📚 Documentación Adicional

- **API Completa:** [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)
- **Machine Learning:** Consultar documentación de XGBoost
- **Tailwind CSS:** https://tailwindcss.com
- **Chart.js:** https://www.chartjs.org

---

## 🐛 Troubleshooting

### El dashboard no carga datos del backend

**Solución:**
1. Verifica que backend está corriendo: `http://localhost:5000/api/health`
2. Revisa consola del navegador (F12 → Console) por errores CORS
3. Asegúrate que `API_BASE_URL` en `js/dashboard-api.js` es correcta

### Gráfica no muestra línea azul (predicción)

**Solución:**
1. Recarga página (Ctrl+F5)
2. Verifica que endpoint `/api/forecast/demand` retorna datos

### Modal de orden no se abre

**Solución:**
```javascript
// En consola del navegador
generateOrder('RFC-001')  // Debería abrir modal
```

---

## 💡 Próximos Pasos

1. ✅ Integrar con base de datos real (PostgreSQL/MySQL)
2. ✅ Entrenar modelo XGBoost con datos históricos
3. ✅ Agregar autenticación de usuarios (JWT)
4. ✅ Implementar más secciones (SKU Historial, Logs, etc.)
5. ✅ Agregar notificaciones en tiempo real (WebSockets)
6. ✅ Exportar reportes en PDF con gráficas

---

## 📞 Soporte

Para consultas o issues:
1. Revisa [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)
2. Verifica los comentarios en el código
3. Consulta la documentación de las librerías usadas

---

## 📄 Licencia

Proyecto privado - RefriPerú 2026

---

## 🎉 ¡Listo para empezar!

```bash
# Opción 1: Solo Frontend
open dashboard.html

# Opción 2: Con Backend
cd backend
python app.py

# En otra terminal
python -m http.server 8000
# Luego abre http://localhost:8000/dashboard.html
```

**¡Bienvenido al futuro de la gestión inteligente de inventarios! 🚀**

---

**Última actualización:** 25 de Mayo, 2026  
**Versión:** 1.0.0 - Beta  
**Status:** ✅ Producción-Ready (con datos simulados)
