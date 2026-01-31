/**
 * ============================================================
 * ECO-MARKET API CLIENT (Versión Resiliente & Observable)
 * ============================================================
 */

const API_URL = 'https://api.ecomarket.com/api';
const MAX_RETRIES = 3;

/**
 * 1. CAPA DE OBSERVABILIDAD
 * Gestiona el logging estructurado y telemetría.
 */
const Telemetry = {
    level: 'DEBUG', // Cambiar a 'INFO' en producción

    maskHeaders: (headers) => {
        const masked = { ...headers };
        if (masked['Authorization']) masked['Authorization'] = 'Bearer ********';
        return masked;
    },

    write: (level, msg, context = {}) => {
        const levels = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };
        if (levels[level] < levels[Telemetry.level]) return;

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
 * Maneja peticiones, timeouts, reintentos y logs.
 */
async function apiRequest(endpoint, { method = 'GET', body = null, timeout = 8000 } = {}, retryCount = 0) {
    const startTime = performance.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    const url = `${API_URL}/${endpoint}`;

    // Log de inicio
    Telemetry.write('DEBUG', `🚀 Petición: ${method} ${endpoint}`, {
        url,
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
        const contentType = respuesta.headers.get('content-type');
        let datos = null;

        // Validar si la respuesta es JSON
        if (contentType && contentType.includes('application/json')) {
            datos = await respuesta.json();
        } else if (respuesta.ok) {
            throw new Error("Respuesta del servidor no es JSON (Posible error de Proxy/HTML)");
        }

        // Manejar errores HTTP (4xx, 5xx)
        if (!respuesta.ok) {
            const errorMsg = datos?.message || `Error HTTP ${respuesta.status}`;
            throw new Error(errorMsg);
        }

        // Registro de éxito
        const logLeven = duration > 2000 ? 'WARN' : 'INFO';
        Telemetry.write(logLeven, `✅ Completado: ${endpoint}`, {
            status: respuesta.status,
            duration: `${duration}ms`,
            method
        });

        return datos;

    } catch (error) {
        clearTimeout(timer);
        const duration = Math.round(performance.now() - startTime);

        // Lógica de Reintentos (Caos/Resiliencia)
        const esReintentable = error.name === 'AbortError' || !window.navigator.onLine || error.message.includes('Failed to fetch');

        if (esReintentable && retryCount < MAX_RETRIES) {
            Telemetry.write('WARN', `♻️ Reintentando (${retryCount + 1}/${MAX_RETRIES}): ${endpoint}`, {
                motivo: error.message
            });
            return apiRequest(endpoint, { method, body, timeout }, retryCount + 1);
        }

        // Log de error final
        Telemetry.write('ERROR', `❌ Fallo crítico: ${endpoint}`, {
            error: error.message,
            duration: `${duration}ms`,
            stack: error.stack
        });
        
        throw error;
    }
}

/**
 * 3. FUNCIONES DE NEGOCIO
 */

async function listarProductos() {
    try {
        const productos = await apiRequest('productos');
        const listaSegura = Array.isArray(productos) ? productos : [];
        
        if (listaSegura.length === 0) {
            console.log("ℹ️ No se encontraron productos.");
            return [];
        }

        console.table(listaSegura.map(p => ({ 
            ID: p.id, 
            Nombre: p.nombre, 
            Precio: `$${p.precio}` 
        })));
        
        return listaSegura;
    } catch (error) {
        // El error ya fue logueado por el apiRequest, aquí solo manejamos la UI
        return [];
    }
}

async function obtenerProducto(id) {
    try {
        return await apiRequest(`productos/${encodeURIComponent(id)}`);
    } catch (error) {
        console.warn(`⚠️ No se pudo cargar el producto ${id}.`);
        return null;
    }
}

async function crearProducto(datosProducto) {
    try {
        return await apiRequest('productos', { 
            method: 'POST', 
            body: datosProducto 
        });
    } catch (error) {
        alert("Error al guardar el producto: " + error.message);
        throw error;
    }
}