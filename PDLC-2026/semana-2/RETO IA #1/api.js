/**
 * ============================================================
 * ECO-MARKET API CLIENT (Versión RESTful & Resiliente)
 * ============================================================
 */

const API_URL = 'https://api.ecomarket.com/api';
const MAX_RETRIES = 3;

/**
 * 1. CAPA DE OBSERVABILIDAD
 */
const Telemetry = {
    level: 'DEBUG',
    maskHeaders: (headers) => {
        const masked = { ...headers };
        if (masked['Authorization']) masked['Authorization'] = 'Bearer ********';
        return masked;
    },
    write: (level, msg, context = {}) => {
        const entry = {
            timestamp: new Date().toISOString(),
            level,
            message: msg,
            ...context
        };
        const icons = { DEBUG: '🟣', INFO: '🟢', WARN: '🟠', ERROR: '🔴' };
        console.log(`${icons[level]} [${entry.timestamp}] ${msg}`, entry);
    }
};

/**
 * 2. CLIENTE HTTP BASE
 */
async function apiRequest(endpoint, { method = 'GET', body = null, timeout = 8000 } = {}, retryCount = 0) {
    const startTime = performance.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    const url = `${API_URL}/${endpoint}`;

    Telemetry.write('DEBUG', `🚀 Petición: ${method} ${endpoint}`, {
        attempt: retryCount + 1,
        headers: Telemetry.maskHeaders({ 'Accept': 'application/json' })
    });

    try {
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            signal: controller.signal
        };

        if (body) config.body = JSON.stringify(body);

        const respuesta = await fetch(url, config);
        clearTimeout(timer);

        const duration = Math.round(performance.now() - startTime);
        let datos = null;

        const contentType = respuesta.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            datos = await respuesta.json();
        }

        // --- MANEJO DE ERRORES ESPECÍFICOS ---
        if (!respuesta.ok) {
            // Caso Especial: Conflicto de eliminación (409)
            if (respuesta.status === 409) {
                Telemetry.write('WARN', `⚠️ Conflicto detectado en ${endpoint}`, datos);
                throw { status: 409, ...datos };
            }

            const errorMsg = datos?.message || `Error HTTP ${respuesta.status}`;
            throw new Error(errorMsg);
        }

        Telemetry.write('INFO', `✅ Completado: ${endpoint}`, { status: respuesta.status, duration: `${duration}ms` });
        return datos;

    } catch (error) {
        clearTimeout(timer);
        
        // No reintentar si es un error de cliente (4xx) o conflicto (409)
        const esReintentable = (error.name === 'AbortError' || !window.navigator.onLine) && retryCount < MAX_RETRIES;

        if (esReintentable) {
            return apiRequest(endpoint, { method, body, timeout }, retryCount + 1);
        }

        Telemetry.write('ERROR', `❌ Fallo final: ${endpoint}`, { error: error.message || 'Conflict', status: error.status });
        throw error;
    }
}

/**
 * 3. FUNCIONES DE NEGOCIO ACTUALIZADAS (MAPEO CRUD)
 */

// --- PRODUCTOS ---

/** * Búsqueda por nombre (Caso especial 2: Query Params)
 */
async function buscarProductos(nombre = '') {
    const query = nombre ? `?nombre=${encodeURIComponent(nombre)}` : '';
    return await apiRequest(`productos${query}`);
}

/** * Actualización parcial (Caso especial 3: PATCH)
 */
async function actualizarPrecioProducto(id, nuevoPrecio) {
    return await apiRequest(`productos/${id}`, {
        method: 'PATCH',
        body: { precio: nuevoPrecio }
    });
}

// --- PRODUCTORES ---

/** * Obtener productos de un productor (Caso especial 1: Recurso anidado)
 */
async function listarProductosDeProductor(productorId) {
    return await apiRequest(`productores/${productorId}/productos`);
}

/** * Eliminar productor con manejo de conflicto (Caso especial 4: DELETE 409)
 */
async function eliminarProductor(id) {
    try {
        await apiRequest(`productores/${id}`, { method: 'DELETE' });
        console.log("✅ Productor eliminado exitosamente.");
    } catch (error) {
        if (error.status === 409) {
            alert(`No se puede eliminar: ${error.message}\nAcción sugerida: ${error.action}`);
        } else {
            console.error("Fallo inesperado al eliminar:", error);
        }
    }
}

// --- PEDIDOS ---

async function crearPedido(datosPedido) {
    return await apiRequest('pedidos', {
        method: 'POST',
        body: datosPedido
    });
}