/**
 * CONFIGURACIÓN Y CLIENTE BASE RESILIENTE
 */
const API_URL = 'https://api.ecomarket.com/api';
const MAX_RETRIES = 3; // Intentos máximos ante fallos de red o timeout

async function apiRequest(endpoint, { method = 'GET', body = null, timeout = 8000 } = {}, retryCount = 0) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    const config = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        signal: controller.signal
    };

    if (body) config.body = JSON.stringify(body);

    try {
        const respuesta = await fetch(`${API_URL}/${endpoint}`, config);
        clearTimeout(timer);

        const contentType = respuesta.headers.get('content-type');
        let datos = null;

        // Verificamos si la respuesta es JSON
        if (contentType && contentType.includes('application/json')) {
            datos = await respuesta.json();
        } 
        // Si la respuesta es exitosa pero no es JSON, hay un error de formato (ej. HTML de un proxy)
        else if (respuesta.ok) {
            throw new Error("Formato de respuesta inesperado (No es JSON)");
        }

        if (!respuesta.ok) {
            // Error de negocio (400, 404, 500)
            const errorMsg = datos?.message || `Error del servidor: ${respuesta.status}`;
            throw new Error(errorMsg);
        }

        return datos;
    } catch (error) {
        clearTimeout(timer); // Limpieza de seguridad

        // LÓGICA DE CAOS: Reintento automático si es error de red o timeout
        const esErrorReintentable = error.name === 'AbortError' || error.message.includes('Failed to fetch');
        
        if (esErrorReintentable && retryCount < MAX_RETRIES) {
            console.warn(`♻️ Intento ${retryCount + 1} fallido. Reintentando...`);
            return apiRequest(endpoint, { method, body, timeout }, retryCount + 1);
        }

        // Si ya no hay más reintentos o el error no es reintentable
        if (error.name === 'AbortError') {
            throw new Error('Tiempo de espera agotado tras varios intentos.');
        }
        
        throw error;
    }
}

/**
 * 1. OBTENER TODOS LOS PRODUCTOS
 */
async function listarProductos() {
    try {
        const productos = await apiRequest('productos');
        
        // Protección: Si productos es null o no es array, usamos uno vacío
        const listaSegura = Array.isArray(productos) ? productos : [];
        
        if (listaSegura.length === 0) {
            console.log("ℹ️ No hay productos para mostrar.");
            return [];
        }

        console.table(listaSegura.map(p => ({ 
            ID: p.id, 
            Nombre: p.nombre, 
            Precio: `$${p.precio}` 
        })));
        
        return listaSegura;
    } catch (error) {
        console.error("❌ Fallo al listar:", error.message);
        return []; // Retornamos array vacío para evitar que el frontend rompa
    }
}

/**
 * 2. OBTENER PRODUCTO POR ID
 */
async function obtenerProducto(id) {
    try {
        const producto = await apiRequest(`productos/${encodeURIComponent(id)}`);
        return producto;
    } catch (error) {
        console.warn(`⚠️ Error al obtener producto ${id}: ${error.message}`);
        return null;
    }
}

/**
 * 3. CREAR PRODUCTO
 */
async function crearProducto(datosProducto) {
    try {
        const nuevo = await apiRequest('productos', { 
            method: 'POST', 
            body: datosProducto 
        });
        console.log("🎉 ¡Producto creado con éxito!", nuevo);
        return nuevo;
    } catch (error) {
        console.error("❌ Error al crear producto:", error.message);
        throw error; // En creación solemos propagar para que el formulario sepa que falló
    }
}