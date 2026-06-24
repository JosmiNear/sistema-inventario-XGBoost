/**
 * Dashboard API Module
 * Maneja todas las comunicaciones con el backend Flask/Django
 * 
 * Usos:
 * - fetchDashboardData(): Obtiene KPIs y datos iniciales
 * - fetchDemandForecast(category): Obtiene predicciones XGBoost
 * - submitOrder(sku, quantity): Crea nueva orden de compra
 * - exportReport(format): Exporta reporte en Excel/PDF
 */

const API_BASE_URL = 'http://localhost:5000/api'; // Cambiar según tu backend

class DashboardAPI {
    /**
     * Obtener datos principales del dashboard
     * Backend: GET /api/dashboard/summary
     */
    static async fetchDashboardData() {
        try {
            const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
            if (!response.ok) throw new Error('Error fetching dashboard data');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            // Retornar datos simulados en caso de error
            return {
                total_skus: 248,
                service_level: 94.2,
                critical_alerts: 5,
                opportunity_cost: 125340
            };
        }
    }

    /**
     * Obtener pronóstico de demanda con predicciones XGBoost
     * Backend: GET /api/forecast/demand?category=all&months=13
     */
    static async fetchDemandForecast(category = 'all', months = 13) {
        try {
            const response = await fetch(
                `${API_BASE_URL}/forecast/demand?category=${category}&months=${months}`
            );
            if (!response.ok) throw new Error('Error fetching forecast');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            return null;
        }
    }

    /**
     * Obtener órdenes sugeridas prescriptivas
     * Backend: GET /api/orders/suggestions?category=all
     */
    static async fetchSuggestedOrders(category = 'all') {
        try {
            const response = await fetch(
                `${API_BASE_URL}/orders/suggestions?category=${category}`
            );
            if (!response.ok) throw new Error('Error fetching orders');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            return null;
        }
    }

    /**
     * Enviar nueva orden de compra
     * Backend: POST /api/orders/create
     */
    static async submitOrder(skuCode, quantity, supplier = null, notes = '') {
        try {
            const response = await fetch(`${API_BASE_URL}/orders/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': document.querySelector('[name="csrf_token"]')?.value || ''
                },
                body: JSON.stringify({
                    sku: skuCode,
                    quantity: parseInt(quantity),
                    supplier: supplier,
                    notes: notes,
                    timestamp: new Date().toISOString()
                })
            });

            if (!response.ok) throw new Error('Error creating order');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            throw error;
        }
    }

    /**
     * Buscar SKUs por código o descripción
     * Backend: GET /api/skus/search?q=query
     */
    static async searchSKUs(query) {
        try {
            const response = await fetch(
                `${API_BASE_URL}/skus/search?q=${encodeURIComponent(query)}`
            );
            if (!response.ok) throw new Error('Error searching SKUs');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            return [];
        }
    }

    /**
     * Exportar reporte de órdenes
     * Backend: GET /api/reports/export?format=excel&type=orders
     */
    static async exportReport(format = 'excel', type = 'orders') {
        try {
            const response = await fetch(
                `${API_BASE_URL}/reports/export?format=${format}&type=${type}`
            );

            if (!response.ok) throw new Error('Error exporting report');

            // Descargar archivo
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `reporte_${type}_${new Date().getTime()}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error:', error);
            alert('Error al descargar el reporte');
        }
    }

    /**
     * Obtener historial de cambios de stock
     * Backend: GET /api/skus/history?sku=code&days=30
     */
    static async fetchStockHistory(skuCode, days = 30) {
        try {
            const response = await fetch(
                `${API_BASE_URL}/skus/history?sku=${skuCode}&days=${days}`
            );
            if (!response.ok) throw new Error('Error fetching history');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            return null;
        }
    }

    /**
     * Obtener logs del sistema
     * Backend: GET /api/system/logs?level=all&limit=100
     */
    static async fetchSystemLogs(level = 'all', limit = 100) {
        try {
            const response = await fetch(
                `${API_BASE_URL}/system/logs?level=${level}&limit=${limit}`
            );
            if (!response.ok) throw new Error('Error fetching logs');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            return null;
        }
    }

    /**
     * Obtener métricas de precisión del modelo
     * Backend: GET /api/model/metrics
     */
    static async fetchModelMetrics() {
        try {
            const response = await fetch(`${API_BASE_URL}/model/metrics`);
            if (!response.ok) throw new Error('Error fetching metrics');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            return null;
        }
    }
}

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardAPI;
}
