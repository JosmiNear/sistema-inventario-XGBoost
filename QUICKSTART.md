# ⚡ QUICK START - Comienza en 60 Segundos

## 🎯 3 Opciones: Elige La Tuya

---

## OPCIÓN 1: VER EL DASHBOARD AHORA (5 SEGUNDOS ⚡)

**Solo necesitas un navegador web.**

```
Navega a: c:\Users\LOQ\Desktop\RefriPeru\dashboard.html
```

O en terminal:
```bash
# Windows
start c:\Users\LOQ\Desktop\RefriPeru\dashboard.html

# macOS
open /Users/LOQ/Desktop/RefriPeru/dashboard.html

# Linux
firefox /home/username/RefriPeru/dashboard.html
```

✅ **Verás al instante:**
- Dashboard profesional completo
- 4 KPI Cards con valores simulados
- Gráfica de demanda interactiva
- Tabla de órdenes con 8 SKUs
- Sidebar funcional
- Todo responsivo

🎉 **¡Listo! No hay más configuración necesaria.**

---

## OPCIÓN 2: FRONTEND + BACKEND EN LOCALHOST (5 MINUTOS ⏱️)

**Para ver datos dinámicos del backend y probar la API.**

### Paso 1: Abrir 2 Terminales

**Terminal 1 - Backend Flask:**
```bash
cd c:\Users\LOQ\Desktop\RefriPeru\backend

# Crear entorno virtual (primera vez)
python -m venv venv

# Activar entorno
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python app.py
```

Verás:
```
╔════════════════════════════════════════════════════════════╗
║         RefriPerú - Dashboard API Backend                  ║
║         Flask Server - Development Mode                    ║
╚════════════════════════════════════════════════════════════╝

🚀 Servidor iniciando en: http://localhost:5000
```

✅ Backend corriendo en `http://localhost:5000`

---

**Terminal 2 - Frontend:**
```bash
cd c:\Users\LOQ\Desktop\RefriPeru

# Servir archivos estáticos
python -m http.server 8000
```

Verás:
```
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

✅ Frontend corriendo en `http://localhost:8000`

---

### Paso 2: Abrir en Navegador

```
http://localhost:8000/dashboard.html
```

✅ **Ahora el dashboard consumirá datos reales del backend**

---

### Paso 3: Probar Endpoints (Opcional)

En Terminal 3, prueba la API:

```bash
# Health check
curl http://localhost:5000/api/health

# KPIs del dashboard
curl http://localhost:5000/api/dashboard/summary

# Pronóstico XGBoost
curl http://localhost:5000/api/forecast/demand

# Órdenes sugeridas
curl http://localhost:5000/api/orders/suggestions

# Crear orden (POST)
curl -X POST http://localhost:5000/api/orders/create ^
  -H "Content-Type: application/json" ^
  -d "{\"sku\":\"RFC-001\", \"quantity\":27}"
```

---

## OPCIÓN 3: PRODUCCIÓN - DOCKER (3 MINUTOS 🐳)

**Para deployment en cualquier servidor.**

### Paso 1: Crear Dockerfile

En `c:\Users\LOQ\Desktop\RefriPeru\Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Backend
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .

# Frontend
COPY dashboard.html .
COPY dashboard-compact.html .
COPY js/ js/

# Exponer puertos
EXPOSE 5000 8000

# Comando de inicio
CMD ["python", "app.py"]
```

### Paso 2: Construir imagen

```bash
cd c:\Users\LOQ\Desktop\RefriPeru
docker build -t refriperu-dashboard:latest .
```

### Paso 3: Ejecutar contenedor

```bash
docker run -p 5000:5000 -p 8000:8000 refriperu-dashboard:latest
```

✅ Accede en: `http://localhost:5000`

---

## 📱 Testing Rápido

### Verificar que Dashboard funciona:

1. **Abre dashboard.html en navegador**
2. **Verifica que ves:**

```
✅ Sidebar izquierdo (oscuro)
✅ 4 KPI Cards con números
✅ Gráfica con 2 líneas (roja y azul)
✅ Tabla con 3+ filas
✅ Botones "Generar Orden"
✅ Responsive (redimensiona navegador)
```

### Verificar que Backend funciona:

```bash
# En terminal
curl http://localhost:5000/api/health

# Esperado:
{"status": "ok", "service": "RefriPerú Dashboard API", ...}
```

---

## 🔌 Conectar Con Tu Código Backend Existente

### Si tienes Flask ya corriendo:

1. **En tu `app.py` existente, agrega CORS:**

```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # ← Agregar esto
```

2. **Instala flask-cors:**
```bash
pip install flask-cors
```

3. **Implementa los endpoints que necesitas:**

```python
@app.route('/api/dashboard/summary', methods=['GET'])
def get_summary():
    return jsonify({
        "total_skus": 248,
        "service_level": 94.2,
        "critical_alerts": 5,
        "opportunity_cost": 125340.50
    })
```

4. **Apunta el frontend a tu backend:**

En `js/dashboard-api.js`, línea 2:
```javascript
const API_BASE_URL = 'http://localhost:5000/api'; // ← Cambiar aquí
```

5. **Recarga dashboard.html en navegador**

---

## 📊 Archivos Principales

| Archivo | Propósito | Acción |
|---------|-----------|--------|
| `dashboard.html` | Frontend completo | ⭐ ABRIR EN NAVEGADOR |
| `dashboard-compact.html` | Versión simplificada | Alternativa mobile |
| `backend/app.py` | Servidor Flask | `python app.py` |
| `js/dashboard-api.js` | Módulo API | Importar en HTML |
| `README.md` | Documentación | Leer para detalles |
| `INTEGRATION_GUIDE.md` | Integración backend | Referencia técnica |

---

## 🎨 Personalizar Colores

En `dashboard.html`, busca `<style>` y modifica:

```css
:root {
    --primary-dark: #1e293b;      /* Sidebar - cambia aquí */
    --primary-blue: #1e40af;      /* Botones azules */
    --accent-blue: #3b82f6;       /* Botones secundarios */
    --success-green: #10b981;     /* Verde (Stock Seguro) */
    --warning-yellow: #f59e0b;    /* Amarillo (Riesgo) */
    --danger-red: #ef4444;        /* Rojo (Crítico) */
}
```

---

## 🚨 Troubleshooting

### ❌ "El dashboard no carga datos"

**Solución:**
1. Abre F12 → Console
2. Verifica si hay error CORS
3. Asegúrate que backend está corriendo
4. Verifica `API_BASE_URL` en `js/dashboard-api.js`

### ❌ "Error de Puerto 5000 en Uso"

**Solución:**
```bash
# Encontrar proceso usando puerto 5000
netstat -tuln | grep 5000

# O matar proceso
taskkill /PID <pid> /F

# O usar puerto diferente
python app.py --port 5001
```

### ❌ "ModuleNotFoundError: No module named 'flask'"

**Solución:**
```bash
# Asegúrate que venv está activado
venv\Scripts\activate

# Instala dependencias
pip install -r requirements.txt
```

---

## 📚 Documentación Completa

- **README.md** → Instalación completa y arquitectura
- **INTEGRATION_GUIDE.md** → Todos los endpoints API
- **RESUMEN_EJECUTIVO.md** → Visión general del proyecto

---

## 🎯 Próximos Pasos

### Semana 1:
- ✅ Ver dashboard funcionando
- ✅ Conectar con base de datos real
- ✅ Cargar datos históricos

### Semana 2:
- ✅ Entrenar modelo XGBoost
- ✅ Integrar predicciones
- ✅ Calibrar pérdida asimétrica

### Semana 3:
- ✅ Agregar autenticación
- ✅ Implementar alertas
- ✅ Exportación de reportes

---

## 💬 ¿Necesitas Ayuda?

1. **Revisa comentarios en código** - Tienen instrucciones
2. **Lee INTEGRATION_GUIDE.md** - Responde 99% de preguntas
3. **Consola del navegador (F12)** - Te mostrará errores
4. **Logs del servidor** - Muestra qué falla

---

## ✅ Confirmación de Setup

Cuando tengas todo corriendo, verifica:

```bash
# Terminal 1: Backend
✅ python app.py está ejecutándose
✅ Puerto 5000 responde a curl
✅ JSON válido en respuestas

# Terminal 2: Frontend
✅ python -m http.server 8000 ejecutándose
✅ http://localhost:8000/dashboard.html abre en navegador
✅ Gráficas y tablas visibles

# Navegador
✅ Sin errores en F12 Console
✅ KPIs muestran valores
✅ Botones responden al click
✅ Tabla con datos poblada
```

---

## 🚀 ¡LISTO!

```bash
# El comando más importante:
start dashboard.html
```

**¡Todo está listo para que empieces! 🎉**

---

**Versión:** 1.0.0  
**Última actualización:** 25 de Mayo, 2026  
**Tiempo total de setup:** 5 segundos a 5 minutos según opción
