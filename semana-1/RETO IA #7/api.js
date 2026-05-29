/**
 * CONFIGURACIÓN Y CLIENTE BASE
 * Centralizamos la lógica para que las funciones de negocio sean limpias.
 */
const API_URL = 'https://api.ecomarket.com/api';

async function apiRequest(endpoint, { method = 'GET', body = null, timeout = 8000 } = {}) {
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

        // Validamos si la respuesta es JSON antes de parsear
        const contentType = respuesta.headers.get('content-type');
        let datos = null;
        if (contentType && contentType.includes('application/json')) {
            datos = await respuesta.json();
        }

        if (!respuesta.ok) {
            // Error de negocio (400, 404, 500) con data del servidor si existe
            const errorMsg = datos?.message || `Error ${respuesta.status}`;
            throw new Error(errorMsg);
        }

        return datos;
    } catch (error) {
        if (error.name === 'AbortError') throw new Error('Tiempo de espera agotado');
        throw error; // Propagamos el error para que el llamador decida qué hacer
    }
}

/**
 * 1. OBTENER TODOS LOS PRODUCTOS
 * Cambio: Ahora es una función pura que retorna datos o lanza error.
 */
async function listarProductos() {
    try {
        const productos = await apiRequest('productos');
        console.table(productos.map(p => ({ ID: p.id, Nombre: p.nombre, Precio: `$${p.precio}` })));
        return productos;
    } catch (error) {
        console.error("❌ Fallo al listar:", error.message);
    }
}

/**
 * 2. OBTENER PRODUCTO POR ID
 * Cambio: Uso de encodeURIComponent para seguridad en la URL.
 */
async function obtenerProducto(id) {
    try {
        // Sanitización del ID para evitar rutas rotas
        const producto = await apiRequest(`productos/${encodeURIComponent(id)}`);
        return producto;
    } catch (error) {
        console.warn(`⚠️ Producto ${id} no encontrado o error de red.`);
        return null;
    }
}

/**
 * 3. CREAR PRODUCTO
 * Cambio: Lógica de validación 201 vs 400 ahora es manejada por el cliente base.
 */
async function crearProducto(datosProducto) {
    try {
        const nuevo = await apiRequest('productos', { method: 'POST', body: datosProducto });
        console.log("🎉 ¡Producto creado!", nuevo);
        return nuevo;
    } catch (error) {
        console.error("❌ Error al crear producto:", error.message);
    }
}