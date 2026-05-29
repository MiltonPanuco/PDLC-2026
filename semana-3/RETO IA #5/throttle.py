import asyncio
import time
from contextlib import asynccontextmanager

class ThrottledClient:
    def __init__(self, max_concurrent: int, max_per_second: float):
        """
        Ingeniería de Tráfico para EcoMarket.
        :param max_concurrent: Límite de conexiones abiertas (Semáforo).
        :param max_per_second: Límite de ritmo (Token Bucket).
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limit_delay = 1.0 / max_per_second
        self.last_call = 0.0
        self._peticiones_en_vuelo = 0

    @asynccontextmanager
    async def throttle(self):
        # --- ESTRATEGIA 1: SEMÁFORO (CONCURRENCIA) ---
        async with self.semaphore:
            self._peticiones_en_vuelo += 1
            
            # --- ESTRATEGIA 2: TOKEN BUCKET (RATE LIMIT) ---
            ahora = time.perf_counter()
            tiempo_desde_ultima = ahora - self.last_call
            espera = max(0, self.rate_limit_delay - tiempo_desde_ultima)
            
            if espera > 0:
                await asyncio.sleep(espera)
            
            self.last_call = time.perf_counter()
            
            try:
                yield self._peticiones_en_vuelo
            finally:
                self._peticiones_en_vuelo -= 1

# --- TEST DE ESTRÉS SIMULADO ---
async def test_throttle():
    limiter = ThrottledClient(max_concurrent=3, max_per_second=5)
    
    async def tarea_fake(i):
        async with limiter.throttle() as en_vuelo:
            print(f"[{time.strftime('%H:%M:%S')}] Petición {i:02d} | En vuelo: {en_vuelo}")
            await asyncio.sleep(0.5) # Simula latencia de red

    print("🚀 Lanzando 10 peticiones controladas...")
    await asyncio.gather(*(tarea_fake(i) for i in range(10)))

if __name__ == "__main__":
    asyncio.run(test_throttle())