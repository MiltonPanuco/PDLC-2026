import asyncio
import time
import httpx  # pip install httpx

# Clase base proporcionada en el material
class Observable:
    def __init__(self):
        self._observadores = {}

    def suscribir(self, evento, callback):
        if evento not in self._observadores:
            self._observadores[evento] = []
        self._observadores[evento].append(callback)

    def notificar(self, evento, datos):
        if evento in self._observadores:
            for cb in self._observadores[evento]:
                try:
                    cb(datos)
                except Exception as e:
                    print(f"❌ Error en observador: {e}")

class ServicioPolling(Observable):
    def __init__(self, url, intervalo_base=5):
        super().__init__()
        self.url = url
        self.intervalo_base = intervalo_base
        self.intervalo_actual = intervalo_base
        self.intervalo_max = 60
        self.ultimo_etag = None
        self._activo = False

    async def _consultar(self):
        headers = {"If-None-Match": self.ultimo_etag} if self.ultimo_etag else {}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.url, headers=headers)
                
                if resp.status_code == 200:
                    self.ultimo_etag = resp.headers.get("ETag")
                    self.intervalo_actual = self.intervalo_base
                    print(f"🔄 [200 OK] Datos nuevos. Reset intervalo a {self.intervalo_actual}s")
                    self.notificar("datos_actualizados", resp.json())
                
                elif resp.status_code == 304:
                    self.intervalo_actual = min(self.intervalo_actual * 1.5, self.intervalo_max)
                    print(f"😴 [304] Sin cambios. Backoff: {self.intervalo_actual:.2f}s")
                
                elif resp.status_code >= 500:
                    self.intervalo_actual = min(self.intervalo_actual * 2, self.intervalo_max)
                    self.notificar("error_servidor", f"Error {resp.status_code}")
                    print(f"⚠️ [500] Error servidor. Backoff: {self.intervalo_actual:.2f}s")

        except httpx.TimeoutException:
            self.intervalo_actual = min(self.intervalo_actual * 2, self.intervalo_max)
            self.notificar("timeout", "La petición expiró")
            print(f"⏳ [Timeout] Servidor lento. Backoff: {self.intervalo_actual:.2f}s")

    async def iniciar(self):
        self._activo = True
        print(f"🚀 Iniciando monitor en {self.url}...")
        while self._activo:
            await self._consultar()
            await asyncio.sleep(self.intervalo_actual)

    def detener(self):
        self._activo = False
        print("🛑 Deteniendo monitor limpiamente...")

# --- ETAPA 2: Integración ---

def observador_ui(datos):
    print(f"📺 [UI] Actualizando lista de {len(datos)} productos.")

def observador_alertas(datos):
    # Simulamos detección de stock agotado
    for p in datos[:2]: # Solo checamos los primeros para el ejemplo
        if p.get('userId') == 1: # Simulación de 'agotado'
            print(f"🚨 [ALERTA] Producto con ID {p['id']} está crítico.")

def observador_logs(error):
    timestamp = time.strftime("%H:%M:%S")
    print(f"📝 [LOG {timestamp}] Evento: {error}")

async def main():
    # Usamos JSONPlaceholder para probar la lógica asíncrona
    monitor = ServicioPolling("https://jsonplaceholder.typicode.com/posts")
    
    # Suscribimos las funciones independientes (Fase Aplica)
    monitor.suscribir("datos_actualizados", observador_ui)
    monitor.suscribir("datos_actualizados", observador_alertas)
    monitor.suscribir("error_servidor", observador_logs)
    monitor.suscribir("timeout", observador_logs)

    # Ejecutamos ciclo de demostración
    tarea = asyncio.create_task(monitor.iniciar())
    await asyncio.sleep(20) # Dejamos que corra unos ciclos
    monitor.detener()
    await tarea

if __name__ == "__main__":
    asyncio.run(main())