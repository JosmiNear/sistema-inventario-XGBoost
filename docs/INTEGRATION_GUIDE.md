# Guía de Integración Frontend-Backend - RefriPerú Dashboard

## 📋 Estructura del Proyecto

```
RefriPeru/
├── dashboard.html              # Frontend principal (Tailwind + Chart.js)
├── js/
│   └── dashboard-api.js        # Módulo API para comunicación backend
├── css/
│   └── (estilos adicionales si necesitas)
└── docs/
    └── INTEGRATION_GUIDE.md    # Este archivo
```

---

## 🔌 Endpoints Flask/Django Requeridos

Tu backend debe exponer los siguientes endpoints API REST (JSON):

### 1. **Dashboard - Datos Principales**
```
GET /api/dashboard/summary
```
**Response esperado:**
```json
{
  "total_skus": 248,
  "service_level": 94.2,
  "critical_alerts": 5,
  "opportunity_cost": 125340.50,
  "timestamp": "2026-05-25T10:30:00Z"
}
```

### 2. **Pronóstico de Demanda**
```
GET /api/forecast/demand?category=all&months=13
```
**Response esperado:**
```json
{
  "labels": ["Ene", "Feb", "Mar", ...],
  "real_demand": [1200, 1300, 1400, ...],
  "predicted_demand": [1250, 1280, 1350, ...],
  "confidence_upper": [1437, 1472, 1555, ...],
  "confidence_lower": [1062, 1088, 1147, ...],
  "model_info": {
    "name": "XGBoost v2.0",
    "mape": 12.3,
    "rmse": 45.2,
    "last_trained": "2026-05-24T08:00:00Z"
  }
}
```

### 3. **Órdenes Sugeridas Prescriptivas**
```
GET /api/orders/suggestions?category=all&page=1&limit=50
```
**Response esperado:**
```json
{
  "total": 248,
  "page": 1,
  "items": [
    {
      "sku": "RFC-001",
      "description": "Aire Acondicionado Split 12K BTU",
      "category": "Climatización",
      "current_stock": 18,
      "forecast_t1": 45,
      "suggested_order": 27,
      "status": "warning",
      "mape": 9.2,
      "confidence": "Alta"
    },
    ...
  ]
}
```

### 4. **Crear Nueva Orden**
```
POST /api/orders/create
Content-Type: application/json
```
**Body enviado:**
```json
{
  "sku": "RFC-001",
  "quantity": 27,
  "supplier": "Distribuidor A",
  "notes": "Urgente - Stock bajo",
  "timestamp": "2026-05-25T10:45:00Z"
}
```

**Response esperado:**
```json
{
  "order_id": "ORD-2026-000543",
  "status": "created",
  "sku": "RFC-001",
  "quantity": 27,
  "estimated_arrival": "2026-05-30",
  "cost": 8100.00
}
```

### 5. **Búsqueda de SKUs**
```
GET /api/skus/search?q=aire+acondicionado
```
**Response esperado:**
```json
{
  "results": [
    {
      "sku": "RFC-001",
      "description": "Aire Acondicionado Split 12K BTU",
      "category": "Climatización",
      "current_stock": 18
    },
    ...
  ]
}
```

### 6. **Exportar Reporte**
```
GET /api/reports/export?format=excel&type=orders
```
Retorna un archivo binario (Excel/PDF) para descargar.

### 7. **Historial de Stock**
```
GET /api/skus/history?sku=RFC-001&days=30
```
**Response esperado:**
```json
{
  "sku": "RFC-001",
  "history": [
    {
      "date": "2026-05-25",
      "stock": 18,
      "sales": 5,
      "orders": 0
    },
    ...
  ]
}
```

### 8. **Logs del Sistema**
```
GET /api/system/logs?level=all&limit=100
```
**Response esperado:**
```json
{
  "logs": [
    {
      "timestamp": "2026-05-25T09:30:00Z",
      "level": "INFO",
      "message": "Modelo XGBoost ejecutado exitosamente",
      "module": "forecast"
    },
    ...
  ]
}
```

### 9. **Métricas del Modelo**
```
GET /api/model/metrics
```
**Response esperado:**
```json
{
  "model_version": "2.0",
  "mape_global": 12.3,
  "rmse_global": 45.2,
  "accuracy_by_category": {
    "climatizacion": 11.5,
    "refrigeracion": 12.8,
    "ventilacion": 12.1,
    "componentes": 8.9
  },
  "last_training": "2026-05-24T08:00:00Z",
  "next_training": "2026-05-26T08:00:00Z"
}
```

---

## 🚀 Uso del Módulo API en JavaScript

El archivo `js/dashboard-api.js` encapsula todas las llamadas. Ejemplo:

```javascript
// Cargar datos del dashboard
DashboardAPI.fetchDashboardData().then(data => {
    document.getElementById('kpiTotalSKUs').textContent = data.total_skus;
    document.getElementById('kpiServiceLevel').textContent = data.service_level + '%';
    document.getElementById('kpiCriticalAlerts').textContent = data.critical_alerts;
});

// Obtener pronóstico para gráfica
DashboardAPI.fetchDemandForecast('all').then(data => {
    // Actualizar gráfica con datos reales
    updateDemandChart(data);
});

// Crear orden
DashboardAPI.submitOrder('RFC-001', 27, 'Distribuidor A', 'Stock bajo').then(result => {
    console.log('Orden creada:', result.order_id);
    closeOrderModal();
});

// Exportar reporte
DashboardAPI.exportReport('excel', 'orders');
```

---

## 🔧 Configuración del Backend (Flask)

### Ejemplo mínimo con Flask-CORS:

```python
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Habilitar CORS para llamadas desde el frontend

# ===== Datos simulados (reemplazar con base de datos) =====
mock_dashboard_data = {
    "total_skus": 248,
    "service_level": 94.2,
    "critical_alerts": 5,
    "opportunity_cost": 125340.50
}

# ===== Endpoints API =====

@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """Obtener resumen del dashboard"""
    return jsonify({
        **mock_dashboard_data,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/forecast/demand', methods=['GET'])
def get_demand_forecast():
    """Obtener pronóstico de demanda"""
    category = request.args.get('category', 'all')
    months = request.args.get('months', 13, type=int)
    
    # Backend: Llamar modelo XGBoost aquí
    # predicciones = modelo_xgboost.predict(...)
    
    return jsonify({
        "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic", "Próx"],
        "real_demand": [1200, 1300, 1400, 1150, 950, 850, 700, 650, 750, 1050, 1350, 1450, 1400],
        "predicted_demand": [1250, 1280, 1350, 1200, 1000, 900, 720, 680, 800, 1100, 1380, 1470, 1420],
        "confidence_upper": [1437, 1472, 1555, 1380, 1150, 1035, 828, 782, 920, 1265, 1587, 1691, 1633],
        "confidence_lower": [1062, 1088, 1147, 1020, 850, 765, 612, 578, 680, 935, 1173, 1249, 1207],
        "model_info": {
            "name": "XGBoost v2.0",
            "mape": 12.3,
            "rmse": 45.2,
            "last_trained": "2026-05-24T08:00:00Z"
        }
    })

@app.route('/api/orders/suggestions', methods=['GET'])
def get_suggested_orders():
    """Obtener órdenes sugeridas"""
    category = request.args.get('category', 'all')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    # Backend: Lógica prescriptiva aquí
    # suggested = calculate_order_qty(stock, forecast, parameters)
    
    return jsonify({
        "total": 248,
        "page": page,
        "items": [
            {
                "sku": "RFC-001",
                "description": "Aire Acondicionado Split 12K BTU",
                "category": "Climatización",
                "current_stock": 18,
                "forecast_t1": 45,
                "suggested_order": 27,
                "status": "warning"
            }
            # ... más items
        ]
    })

@app.route('/api/orders/create', methods=['POST'])
def create_order():
    """Crear nueva orden de compra"""
    data = request.get_json()
    
    # Validación y lógica de negocio
    if not data.get('sku') or not data.get('quantity'):
        return jsonify({"error": "SKU y cantidad requeridos"}), 400
    
    # Guardar en base de datos
    order_id = f"ORD-{datetime.now().strftime('%Y-%m%d%H%M%S')}"
    
    return jsonify({
        "order_id": order_id,
        "status": "created",
        "sku": data['sku'],
        "quantity": data['quantity'],
        "estimated_arrival": "2026-05-30"
    }), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

---

## 🔐 Seguridad - CORS y CSRF

### Para producción, agrega configuración CORS restrictiva:

```python
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": ["https://tudominio.com"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "X-CSRF-Token"]
    }
})
```

### Validación CSRF:
El frontend envía token CSRF en headers. El backend debe validar:
```python
@app.before_request
def validate_csrf():
    if request.method in ['POST', 'PUT', 'DELETE']:
        token = request.headers.get('X-CSRF-Token')
        # Validar token aquí
```

---

## 🐳 Deployment con Docker

### Dockerfile para Flask:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### docker-compose.yml:
```yaml
version: '3.8'
services:
  frontend:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./dashboard.html:/usr/share/nginx/html/index.html
      - ./js:/usr/share/nginx/html/js

  backend:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
```

---

## 📊 Variables de Template para Backend Dinámico

Si usas template engines (Jinja2 en Flask), el HTML original contiene comentarios:

```html
<!-- Backend: {{ usuario.nombre }} -->
<!-- Backend: {{ total_skus }} -->
<!-- Backend: {{ service_level }}% -->
```

**Reemplazar en tu template Flask:**
```html
{{ usuario.nombre }}
{{ total_skus }}
{{ service_level }}%
```

---

## 🧪 Testing Endpoints

### Con cURL:
```bash
# Obtener datos del dashboard
curl -X GET http://localhost:5000/api/dashboard/summary

# Crear orden
curl -X POST http://localhost:5000/api/orders/create \
  -H "Content-Type: application/json" \
  -d '{"sku":"RFC-001", "quantity":27}'

# Exportar reporte
curl -X GET http://localhost:5000/api/reports/export?format=excel > reporte.xlsx
```

### Con Postman:
1. Importar endpoints en colección
2. Configurar variables de entorno (`{{base_url}}`)
3. Ejecutar requests

---

## 📱 Responsividad Verificada

El dashboard es totalmente responsivo:
- **Desktop (>1024px):** Sidebar fijo + contenido completo
- **Tablet (768-1023px):** Sidebar contraído automático
- **Mobile (<768px):** Sidebar colapsable + tabla en scroll horizontal

---

## 🚨 Manejo de Errores

El módulo API (`dashboard-api.js`) incluye try-catch en todos los endpoints. En producción:

1. Implementar reintentos con backoff exponencial
2. Logging centralizado de errores
3. Notificaciones visuales al usuario
4. Fallback a datos en caché

---

## 📚 Referencias

- **Tailwind CSS:** https://tailwindcss.com
- **Chart.js:** https://www.chartjs.org
- **Flask-CORS:** https://flask-cors.readthedocs.io
- **XGBoost:** https://xgboost.readthedocs.io

---

**Última actualización:** 25 de Mayo, 2026
