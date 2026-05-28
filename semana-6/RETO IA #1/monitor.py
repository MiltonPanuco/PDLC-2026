"""
# =============================================================================
# TRAZA DE RED SSE: MONITOR DE INVENTARIO ECOMARKET (ESTÁNDAR SEMANA 6)
# =============================================================================
# Flujo esperado de la sesión:
# t=00s [CLIENTE] -> GET /api/alertas (Accept: text/event-stream)
# t=00s [SERVER ] <- 200 OK (Content-Type: text/event-stream)
# -----------------------------------------------------------------------------
# t=02s [SERVER ] >> id: 1\nevent: precio-actualizado\ndata: {"prod":"A01","p":47}\n\n
# t=08s [SERVER ] >> id: 2\nevent: stock-critico\ndata: {"prod":"B07","s":1}\n\n
# t=15s [SERVER ] >> : ping\n\n (Keep-alive para evitar timeout de red)
# t=20s [SERVER ] >> id: 3\nevent: precio-actualizado\ndata: {"prod":"A01","p":45}\n\n
# -----------------------------------------------------------------------------
# t=25s [RED    ] !! CORTE DE CONEXIÓN (La red de Tepic parpadea)
# t=28s [CLIENTE] -> RECONEXIÓN AUTOMÁTICA (Retry 3s)
# t=28s [CLIENTE] -> GET /api/alertas (Header: Last-Event-ID: 3)
# =============================================================================
"""

import asyncio
import time
import httpx

class Observable:
    """Implementación del Patrón Observer para desacoplar lógica de EcoMarket."""
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

class ServicioSSE(Observable):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.ultimo_id = None
        self._activo = False

    async def iniciar(self):
        self._activo = True
        print(f"🚀 [EcoMarket] Iniciando Stream en {self.url}...")
        
        while self._activo:
            try:
                # 1. Preparar Headers: Si hubo un corte, enviamos el último ID recibido
                headers = {"Accept": "text/event-stream"}
                if self.ultimo_id:
                    headers["Last-Event-ID"] = str(self.ultimo_id)

                async with httpx.AsyncClient(timeout=None) as client:
                    # 2. Conexión persistente: No cerramos el socket tras el primer byte
                    async with client.stream("GET", self.url, headers=headers) as response:
                        if response.status_code != 200:
                            print(f"⚠️ Error {response.status_code}. Reintentando...")
                            await asyncio.sleep(5)
                            continue

                        print("🔗 Canal abierto. Escuchando cambios en inventario...")
                        
                        # 3. Lectura por líneas (Protocolo text/event-stream)
                        async for line in response.aiter_lines():
                            if not self._activo: break
                            if not line.strip(): continue # Ignora saltos de línea de separación

                            self._parsear_protocolo(line)

            except Exception as e:
                # 4. Manejo de desconexión: El cliente espera y reconecta solo
                print(f"⏳ Red inestable: {e}. Reintentando en 3s...")
                await asyncio.sleep(3) 

    def _parsear_protocolo(self, line):
        """Parsea los campos clave del estándar SSE."""
        # Comentarios (Pings)
        if line.startswith(":"):
            self.notificar("keep_alive", "Keep-alive: El servidor sigue ahí.")
            return

        # Actualización de ID (Para persistencia en reconexión)
        if line.startswith("id:"):
            self.ultimo_id = line.replace("id:", "").strip()
            return
        
        # Datos del evento
        if line.startswith("data:"):
            payload = line.replace("data:", "").strip()
            self.notificar("datos_actualizados", payload)

    def detener(self):
        self._activo = False
        print("🛑 Monitor SSE detenido.")

# --- OBSERVADORES (Tus funciones de la Semana 4 siguen intactas) ---

def observador_ui(datos):
    print(f"📺 [UI] Actualización recibida: {datos}")

def observador_alertas(datos):
    # Lógica para detectar stock bajo en tiempo real
    print(f"🚨 [ALERTA] Procesando cambios de inventario...")

# --- MAIN ---

async def main():
    # URL de ejemplo (Cambiar por tu endpoint de Laravel/Node)
    monitor = ServicioSSE("http://localhost:8000/api/alertas")
    
    # Registro de observadores
    monitor.suscribir("datos_actualizados", observador_ui)
    monitor.suscribir("datos_actualizados", observador_alertas)

    tarea = asyncio.create_task(monitor.iniciar())
    
    try:
        await asyncio.sleep(60) # Ejecutar por un minuto
    finally:
        monitor.detener()
        await tarea

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass