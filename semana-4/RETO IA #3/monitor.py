"""
DECISIONES DE DISEÑO — MONITOR DE INVENTARIO ECOMARKET
=======================================================
INTERVALO_BASE = 5s
  → Trade-off: Los callbacks de los observadores se ejecutan síncronamente. 
    Si un observador (como el de logs) tarda 2s, el ciclo efectivo sube a 7s.
    Decisión: 5s es un balance aceptable para inventario; en sistemas críticos 
    se requeriría que los callbacks fueran asíncronos para no bloquear el loop.

INTERVALO_MAX = 60s
  → Trade-off: El cliente descansa y ahorra batería/datos, pero la información 
    puede tener hasta 1 minuto de retraso. Para EcoMarket esto es 
    aceptable, ya que el stock no suele cambiar por milisegundos.

TIMEOUT = 10s
  → Justificación: Protege al cliente de quedarse colgado en una petición eterna 
    si el servidor falla o la red es inestable. Sin esto, el ciclo 
    de eventos se detendría por completo.

BACKOFF ADAPTATIVO (1.5x / 2x)
  → Justificación: Ante respuestas 304 (sin cambios) o errores 5xx, el cliente 
    reduce la frecuencia de consulta. Esto protege la salud del 
    ciclo de eventos del cliente y evita "bombardear" a un servidor que ya 
    está sufriendo.
"""

import asyncio
import time
import httpx  # Requiere: pip install httpx

class Observable:
    """Implementación del Patrón Observer para desacoplar lógica."""
    def __init__(self):
        # Diccionario para almacenar eventos y sus listas de callbacks
        self._observadores = {}

    def suscribir(self, evento, callback):
        """Agrega un interesado a un evento específico."""
        if evento not in self._observadores:
            self._observadores[evento] = []
        self._observadores[evento].append(callback)

    def notificar(self, evento, datos):
        """Ejecuta los callbacks asociados al evento."""
        if evento in self._observadores:
            for cb in self._observadores[evento]:
                try:
                    # Se ejecutan de forma síncrona según el diseño actual
                    cb(datos)
                except Exception as e:
                    # Un observador roto no debe detener a los demás
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
        """Lógica central de petición con ETag y Backoff."""
        # Enviamos If-None-Match solo si tenemos un ETag guardado
        headers = {"If-None-Match": self.ultimo_etag} if self.ultimo_etag else {}
        
        try:
            # Invariante: Timeout configurado siempre
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.url, headers=headers)
                
                if resp.status_code == 200:
                    # Hay cambios: Guardamos ETag y reseteamos intervalo
                    self.ultimo_etag = resp.headers.get("ETag")
                    self.intervalo_actual = self.intervalo_base
                    print(f"🔄 [200 OK] Datos nuevos detectados. Intervalo reset a {self.intervalo_actual}s")
                    self.notificar("datos_actualizados", resp.json())
                
                elif resp.status_code == 304:
                    # Sin cambios: Aplicamos backoff incremental
                    self.intervalo_actual = min(self.intervalo_actual * 1.5, self.intervalo_max)
                    print(f"😴 [304] Sin cambios. Backoff aplicado: {self.intervalo_actual:.2f}s")
                
                elif resp.status_code >= 500:
                    # Error de servidor: Backoff más agresivo
                    self.intervalo_actual = min(self.intervalo_actual * 2, self.intervalo_max)
                    self.notificar("error_servidor", f"Error {resp.status_code}")
                    print(f"⚠️ [500] Fallo en backend. Reintentando en {self.intervalo_actual:.2f}s")

        except httpx.TimeoutException:
            # Manejo de timeout para no bloquear el loop
            self.intervalo_actual = min(self.intervalo_actual * 2, self.intervalo_max)
            self.notificar("error_red", "Timeout alcanzado")
            print(f"⏳ [Timeout] Servidor lento. Backoff: {self.intervalo_actual:.2f}s")

    async def iniciar(self):
        """Ciclo principal de vida del monitor."""
        self._activo = True
        print(f"🚀 Iniciando monitor en {self.url}...")
        while self._activo:
            await self._consultar()
            # Espera no bloqueante usando asyncio
            await asyncio.sleep(self.intervalo_actual)

    def detener(self):
        """Detención limpia mediante bandera."""
        self._activo = False
        print("🛑 Deteniendo monitor limpiamente...")

# --- ETAPA 2: Funciones Independientes (Observadores) ---

def observador_ui(datos):
    """Simula la actualización de la interfaz."""
    print(f"📺 [UI] Mostrando {len(datos)} productos actualizados.")

def observador_alertas(datos):
    """Detecta condiciones críticas como stock en cero."""
    # Ejemplo: Si el userId es 1, simulamos que el stock está bajo
    for item in datos[:1]: 
        if item.get('userId') == 1:
            print("🚨 [ALERTA] Revisar inventario de Quinoa Orgánica: Stock crítico.")

def observador_logs(mensaje):
    """Registro de eventos con marca de tiempo."""
    ahora = time.strftime("%H:%M:%S")
    print(f"📝 [LOG {ahora}] Evento registrado: {mensaje}")

async def main():
    # Contra JSONPlaceholder para validar lógica de red
    monitor = ServicioPolling("https://jsonplaceholder.typicode.com/posts")
    
    # Registro de observadores (Cumpliendo desacoplamiento)
    monitor.suscribir("datos_actualizados", observador_ui)
    monitor.suscribir("datos_actualizados", observador_alertas)
    monitor.suscribir("error_servidor", observador_logs)
    monitor.suscribir("error_red", observador_logs)

    # Demostración de funcionamiento
    tarea = asyncio.create_task(monitor.iniciar())
    
    # Dejamos correr 30 segundos para ver el backoff en acción
    await asyncio.sleep(30)
    
    monitor.detener()
    await tarea

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass