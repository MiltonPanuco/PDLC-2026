"""
RECEPTOR ALERTAS ECOMARKET V2 — Decisiones de arquitectura

TRADE-OFFS DE DISEÑO:
- Escenario A (Escalabilidad): Se usa composición para el Observable. Esto permite 
  cambiar el motor de notificaciones (ej. a Redis o RabbitMQ) sin tocar la lógica SSE.
- Escenario B (Legacy): El parser de líneas es tolerante a fallos; si el servidor 
  legacy envía basura, el buffer se limpia sin tumbar el proceso.
- Escenario C (3G): Implementa Backoff Exponencial (2^n) para evitar saturar la 
  antena móvil en reconexiones infinitas.
"""

import asyncio
import time
import httpx
import json

class Observable:
    def __init__(self):
        self._suscriptores = {}

    def suscribir(self, evento, callback):
        if evento not in self._suscriptores:
            self._suscriptores[evento] = []
        self._suscriptores[evento].append(callback)

    def notificar(self, evento, datos):
        if evento in self._suscriptores:
            for cb in self._suscriptores[evento]:
                cb(datos)

class ReceptorAlertasV2:
    def __init__(self, url):
        self.url = url
        self.notifier = Observable() # Composición
        self.ultimo_id = None
        self.activo = True
        self.reintentos = 0

    async def conectar(self):
        print(f"🚀 [{self._ts()}] Conectando al Stream de EcoMarket...")
        
        while self.activo:
            headers = {"Accept": "text/event-stream"}
            if self.ultimo_id:
                headers["Last-Event-ID"] = str(self.ultimo_id)

            try:
                # Timeout=None es vital para no cortar el stream por silencio
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", self.url, headers=headers) as resp:
                        if resp.status_code == 204: break
                        
                        self.reintentos = 0
                        buffer_data = []
                        current_event = "message"

                        async for line in resp.aiter_lines():
                            if not self.activo: break
                            
                            if not line.strip(): # Fin de bloque \n\n
                                if buffer_data:
                                    payload = "".join(buffer_data)
                                    self.notifier.notificar(current_event, payload)
                                    buffer_data = []; current_event = "message"
                                continue

                            if line.startswith("id:"): self.ultimo_id = line[3:].strip()
                            elif line.startswith("event:"): current_event = line[6:].strip()
                            elif line.startswith("data:"): buffer_data.append(line[5:].strip())

            except Exception as e:
                self.reintentos += 1
                espera = min(30, 2 ** self.reintentos)
                print(f"🔌 [{self._ts()}] Error de red. Reintento en {espera}s...")
                await asyncio.sleep(espera)

    def _ts(self):
        return time.strftime("%H:%M:%S")

# --- SUSCRIPTORES (Lógica de Negocio) ---

def suscriptor_ui(datos):
    print(f"📺 [INTERFAZ] Renderizando producto: {datos}")

def suscriptor_alertas(datos):
    if "1" in datos: # Simulación de stock bajo
        print("🚨 [ALERTA] ¡Stock Crítico detectado!")

def suscriptor_logs(datos):
    print(f"📝 [LOGS] Evento guardado en base de datos local.")

# --- EJECUCIÓN ---

async def main():
    receptor = ReceptorAlertasV2("https://sse.dev/test")
    
    # Registro de los 3 suscriptores
    receptor.notifier.suscribir("precio-actualizado", suscriptor_ui)
    receptor.notifier.suscribir("stock-critico", suscriptor_alertas)
    receptor.notifier.suscribir("message", suscriptor_logs)

    await receptor.conectar()

if __name__ == "__main__":
    asyncio.run(main())