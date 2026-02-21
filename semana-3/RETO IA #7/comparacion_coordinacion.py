import asyncio
import time
from typing import Dict, Any

# Simulación de latencia de red para EcoMarket
async def fetch_mock(name: str, delay: float, should_fail: bool = False):
    await asyncio.sleep(delay)
    if should_fail:
        raise Exception(f"Fallo en {name}")
    return f"Datos de {name}"

# --- ESTRATEGIAS ---

async def run_gather(tareas):
    inicio = time.perf_counter()
    # Espera a que TODO termine o falle
    resultados = await asyncio.gather(*tareas, return_exceptions=True)
    return time.perf_counter() - inicio, "Todo o nada"

async def run_as_completed(tareas):
    inicio = time.perf_counter()
    tiempos_parciales = []
    # Entrega resultados conforme llegan
    for coro in asyncio.as_completed(tareas):
        await coro
        tiempos_parciales.append(time.perf_counter() - inicio)
    return tiempos_parciales[0], "Progresivo (Primer dato)"

async def run_wait_first(tareas):
    inicio = time.perf_counter()
    # Se detiene en cuanto el primero tiene éxito
    done, pending = await asyncio.wait(tareas, return_when=asyncio.FIRST_COMPLETED)
    for t in pending: t.cancel() # Limpieza
    return time.perf_counter() - inicio, "Carrera (Solo el más rápido)"

async def run_wait_exception(tareas):
    inicio = time.perf_counter()
    # Se detiene al primer error
    done, pending = await asyncio.wait(tareas, return_when=asyncio.FIRST_EXCEPTION)
    return time.perf_counter() - inicio, "Modo Pánico"

async def main():
    # Escenario: Categorías (0.1s), Productos (0.5s), Perfil (1.0s), Notif (Error @ 0.3s)
    escenario = [
        fetch_mock("Categorías", 0.1),
        fetch_mock("Productos", 0.5),
        fetch_mock("Perfil", 1.0),
        fetch_mock("Notif", 0.3, should_fail=True)
    ]

    print(f"{'Estrategia':<25} | {'Latencia Percibida':<15}")
    print("-" * 45)

    t1, desc = await run_gather(escenario)
    print(f"{desc:<25} | {t1:.2f}s (Carga total)")

    t2, desc = await run_as_completed(escenario)
    print(f"{desc:<25} | {t2:.2f}s (UX rápida)")

    t3, desc = await run_wait_first(escenario)
    print(f"{desc:<25} | {t3:.2f}s (El ganador)")

if __name__ == "__main__":
    asyncio.run(main())