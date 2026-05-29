import asyncio
import aiohttp
import time
import pandas as pd
from typing import Dict

class SmartSession(aiohttp.ClientSession):
    """
    Extensión de ClientSession con observabilidad avanzada y 
    gestión de infraestructura de conexiones.
    """
    def __init__(self, limit: int = 100, limit_per_host: int = 0, *args, **kwargs):
        connector = aiohttp.TCPConnector(
            limit=limit, 
            limit_per_host=limit_per_host,
            keepalive_timeout=60
        )
        super().__init__(connector=connector, *args, **kwargs)
        self._metrics = {
            "total_requests": 0,
            "start_time": time.time()
        }

    @property
    def pool_stats(self) -> Dict:
        """Retorna el estado actual del pool de conexiones."""
        conn = self.connector
        return {
            "limit": conn.limit,
            "active_connections": len(conn._conns),
            "acquired": len(conn._acquired),
            "waiting_in_queue": len(conn._waiters) if conn._waiters else 0,
            "free": conn.limit - len(conn._acquired) if conn.limit else "∞"
        }

    async def fetch(self, url: str):
        """Wrapper para peticiones con registro de métricas."""
        self._metrics["total_requests"] += 1
        try:
            async with self.get(url) as response:
                return await response.read()
        except Exception as e:
            return str(e)

# --- Engine de Benchmark ---
async def run_benchmark(pool_size: int, requests_count: int = 50):
    url = "https://httpbin.org/delay/0.1"  # Simula 100ms de delay de red
    async with SmartSession(limit=pool_size) as session:
        start_ts = time.perf_counter()
        
        # Ejecución concurrente
        tasks = [session.fetch(url) for _ in range(requests_count)]
        await asyncio.gather(*tasks)
        
        end_ts = time.perf_counter()
        duration = end_ts - start_ts
        
        stats = session.pool_stats
        return {
            "Pool Size": pool_size,
            "Total Time (s)": round(duration, 3),
            "Throughput (req/s)": round(requests_count / duration, 2),
            "Max Active Conns": stats["active_connections"]
        }

async def main():
    print("🚀 Iniciando Benchmark de Conexiones para EcoMarket...\n")
    results = []
    for size in [5, 20, 100]: # 100 actúa como 'ilimitado' para este volumen
        res = await run_benchmark(size)
        results.append(res)
    
    df = pd.DataFrame(results)
    print(df.to_string(index=False))

if __name__ == "__main__":
    asyncio.run(main())