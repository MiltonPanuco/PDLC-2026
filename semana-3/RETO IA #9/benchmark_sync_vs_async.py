import asyncio
import time
import requests
import aiohttp
import statistics
from tabulate import tabulate # pip install tabulate

API_MOCK_DELAY = 0.2  # 200ms de latencia simulada

# --- CLIENTE SÍNCRONO (Requests) ---
def run_sync_bench(n_requests):
    inicio = time.perf_counter()
    with requests.Session() as session:
        for _ in range(n_requests):
            # Simulamos la latencia de red
            time.sleep(API_MOCK_DELAY) 
    return time.perf_counter() - inicio

# --- CLIENTE ASÍNCRONO (aiohttp) ---
async def run_async_bench(n_requests):
    inicio = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        async def fetch():
            await asyncio.sleep(API_MOCK_DELAY)
        
        await asyncio.gather(*(fetch() for _ in range(n_requests)))
    return time.perf_counter() - inicio

def comparar(n_peticiones):
    print(f"🧪 Corriendo benchmark para {n_peticiones} peticiones...")
    
    # Ejecución Síncrona
    t_sync = run_sync_bench(n_peticiones)
    
    # Ejecución Asíncrona
    t_async = asyncio.run(run_async_bench(n_peticiones))
    
    speedup = t_sync / t_async
    return [n_peticiones, f"{t_sync:.3f}s", f"{t_async:.3f}s", f"{speedup:.1f}x"]

if __name__ == "__main__":
    headers = ["Peticiones", "Tiempo Síncrono", "Tiempo Asíncrono", "Speedup"]
    resultados = [comparar(n) for n in [1, 5, 20, 50]]
    
    print("\n📊 RESULTADOS DEL BENCHMARK")
    print(tabulate(resultados, headers=headers, tablefmt="grid"))