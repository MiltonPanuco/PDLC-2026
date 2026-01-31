/**
 * Configuración base
 * Centralizar la URL facilita cambios futuros (ej. pasar de local a producción).
 */
const API_URL = 'https://api.ecomarket.com/api';

/**
 * 1. OBTENER TODOS LOS PRODUCTOS (GET)
 */
async function listarProductos() {
    try {
        console.log("⏳ Cargando productos...");

        // Agregamos un timeout manual de 8 segundos
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);

        const respuesta = await fetch(`${API_URL}/productos`, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (!respuesta.ok) {
            throw new Error(`Error de servidor: ${respuesta.status}`);
        }

        const productos = await respuesta.json();

        console.log("✅ Productos obtenidos:");
        // Imprimimos una tabla legible en la consola
        console.table(productos.map(p => ({ ID: p.id, Nombre: p.nombre, Precio: `$${p.precio}` })));

    } catch (error) {
        if (error.name === 'AbortError') {
            console.error("❌ La petición expiró (Timeout). El servidor tarda demasiado.");
        } else {
            console.error("❌ Error de red o servidor no disponible:", error.message);
        }
    }
}

/**
 * 2. OBTENER PRODUCTO POR ID (GET con parámetro)
 */
async function obtenerProducto(id) {
    try {
        const respuesta = await fetch(`${API_URL}/productos/${id}`);

        if (respuesta.status === 404) {
            console.warn(`⚠️ El producto con ID ${id} no existe.`);
            return null;
        }

        if (!respuesta.ok) throw new Error("Error al consultar el producto.");

        const producto = await respuesta.json();
        console.log("🔍 Detalle encontrado:", producto);
        return producto;

    } catch (error) {
        console.error("❌ No pudimos completar la búsqueda. Intenta más tarde.");
    }
}

/**
 * 3. CREAR PRODUCTO (POST con Body JSON)
 */
async function crearProducto(datosProducto) {
    try {
        const respuesta = await fetch(`${API_URL}/productos`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json' // OBLIGATORIO para enviar JSON
            },
            body: JSON.stringify(datosProducto) // Convertimos objeto JS a texto
        });

        const resultado = await respuesta.json();

        if (respuesta.status === 201) {
            console.log("🎉 ¡Producto creado con éxito!", resultado);
        } else if (respuesta.status === 400) {
            console.error("❌ Error de validación:", resultado.errores || "Datos inválidos");
        }

    } catch (error) {
        console.error("❌ Fallo en la conexión al intentar crear.");
    }
}


// Prueba 1: Ver todo el inventario
listarProductos();

// Prueba 2: Buscar un producto específico (ejemplo ID 10)
obtenerProducto(10);

// Prueba 3: Crear un nuevo artículo
const nuevoItem = {
    nombre: "Detergente Biodegradable",
    precio: 85.50,
    categoria: "Limpieza"
};
crearProducto(nuevoItem);