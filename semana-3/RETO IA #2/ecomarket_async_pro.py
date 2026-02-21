import asyncio
import time
from typing import Dict, List, Any
# Importamos tus validadores que ya tienes en validadores.py
from validadores import validar_producto, ValidationError

# --- SIMULACIÓN DE INTERNALS ---
async def peticion_api_simulada(endpoint: str, delay: float, retornar_error: bool = False):
    """Simula el comportamiento de aiohttp.get"""
    print(f"🚀 [Loop] Disparando petición a: {endpoint}")
    await asyncio.sleep(delay) # Aquí el event loop pausa esta tarea y busca otra
    
    if retornar_error:
        print(f"❌ [Loop] Error 500 en: {endpoint}")
        raise Exception(f"Error de servidor en {endpoint}")
    
    print(f"✅ [Loop] Datos recibidos de: {endpoint}")
    # Datos de prueba basados en tu modelo de EcoMarket
    datos_mock = {
        "/productos": [{"id": 1, "nombre": "Miel de Abeja", "precio": 150.0, "categoria": "miel"}],
        "/categorias": ["frutas", "verduras", "lacteos", "miel", "conservas"],
        "/perfil": {"usuario": "Milton Cruz", "rol": "Programador"}
    }
    return datos_mock.get(endpoint, {})

async def obtener_datos_ecomarket():
    inicio = time.time()
    print("--- INICIO DE CARGA ASÍNCRONA ---")

    # 1. Creamos las coroutines (no se ejecutan todavía)
    tarea_prod = peticion_api_simulada("/productos", 1.5)
    tarea_cat = peticion_api_simulada("/categorias", 2.0) # Esta tardará más
    tarea_perfil = peticion_api_simulada("/perfil", 1.0)

    # 2. asyncio.gather registra las tareas en el Loop y espera
    # Usamos return_exceptions=True para que si algo truena, lo demás siga vivo
    print("⏳ [Gather] Registrando tareas y cediendo el control al Event Loop...")
    resultados = await asyncio.gather(tarea_prod, tarea_cat, tarea_perfil, return_exceptions=True)

    productos, categorias, perfil = resultados

    # 3. Procesamiento y Validación (Uso de tus validadores.py)
    print("\n--- PROCESANDO RESULTADOS ---")
    
    if not isinstance(productos, Exception):
        try:
            # Validamos el primer producto de la lista
            validar_producto(productos[0])
            print(f"✔️ Producto '{productos[0]['nombre']}' validado correctamente.")
        except ValidationError as e:
            print(f"⚠️ Error de validación en productos: {e}")
    else:
        print(f"❌ No se pudieron cargar productos: {productos}")

    if not isinstance(perfil, Exception):
        print(f"👤 Bienvenido de nuevo, {perfil.get('usuario')}.")

    total = time.time() - inicio
    print(f"\n✨ Carga completa en {total:.2f} segundos.")

if __name__ == "__main__":
    # 4. asyncio.run crea el Event Loop desde cero
    asyncio.run(obtener_datos_ecomarket())