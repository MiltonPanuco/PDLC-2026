"""
RECEPTOR ALERTAS ECOMARKET — Decisiones de arquitectura (cliente)

ESCENARIO A (10k usuarios / Cambios lentos): 
Decisión: Polling con ETag. SSE mantendría 10,000 hilos abiertos innecesariamente 
para datos que cambian 2 veces por hora. El polling libera memoria entre peticiones, 
siendo más escalable para audiencias masivas con baja frecuencia de actualización.

ESCENARIO B (Servidor Legacy / Stock 1s): 
Decisión: Polling (Short Polling). Aunque la latencia de 1s es alta, un servidor 
legacy sin soporte para HTTP Streaming (text/event-stream) hace técnicamente 
imposible el uso de SSE. El polling es la única vía de compatibilidad hacia atrás.

ESCENARIO C (Red 3G Inestable): 
Decisión: SSE. Elegido por su resiliencia nativa; el manejo automático de 
'Last-Event-ID' permite recuperar alertas perdidas tras micro-cortes de red 
sin lógica extra en el cliente, optimizando el ancho de banda en conexiones móviles.

ESCENARIO D (Alertas + Filtros Dinámicos): 
Decisión: SSE + HTTP POST. SSE es superior para recibir (unidireccional), mientras 
que los filtros se envían por peticiones POST independientes. Esto evita la 
complejidad de estado y protocolos (WebSockets) que dificultan el balanceo de carga.
"""

import asyncio
import time
import httpx
import json

class ReceptorAlertas:
    def __init__(self, url):
        self.url = url
        self.ultimo_id = None
        self.retry_ms = 3000
        self.activo = True
        self.intentos = 0
        self.max_intentos = 5

    async def conectar(self):
        """
        Implementación del flujo SSE con recuperación de estado.
        """
        print(f"🚀 [{self._ts()}] Iniciando Receptor de Alertas...")
        
        while self.activo and self.intentos < self.max_intentos:
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            }
            # ETAPA 3: Persistencia de ID para reconexión
            if self.ultimo_id:
                headers["Last-Event-ID"] = str(self.ultimo_id)

            try:
                # ETAPA 1: Conexión asíncrona con timeout de handshake
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream("GET", self.url, headers=headers) as resp:
                        
                        if resp.status_code == 204: 
                            print(f"🛑 [{self._ts()}] Flujo finalizado por servidor (204).")
                            self.activo = False
                            break
                        
                        self.intentos = 0 # Conexión exitosa, reseteamos contador
                        buffer = {"id": None, "event": "message", "data": []}

                        # ETAPA 2: Parsing de eventos por tipo
                        async for line in resp.aiter_lines():
                            if not self.activo: break
                            
                            if not line.strip(): # Fin de bloque de evento (\n\n)
                                if buffer["data"]:
                                    self._procesar_evento(buffer)
                                    buffer = {"id": None, "event": "message", "data": []}
                                continue

                            self._parse_linea(line, buffer)

            except Exception as e:
                self.intentos += 1
                # Backoff exponencial para no saturar el servidor de EcoMarket
                espera = (self.retry_ms / 1000) * (2 ** (self.intentos - 1))
                print(f"🔌 [{self._ts()}] Error: {e}. Reintentando en {espera}s...")
                await asyncio.sleep(espera)

    def _parse_linea(self, line, buffer):
        if line.startswith("id:"):
            buffer["id"] = line[3:].strip()
            self.ultimo_id = buffer["id"]
        elif line.startswith("event:"):
            buffer["event"] = line[6:].strip()
        elif line.startswith("data:"):
            buffer["data"].append(line[5:].strip())

    def _procesar_evento(self, buffer):
        tipo = buffer["event"]
        data_raw = "".join(buffer["data"])
        
        try:
            data = json.loads(data_raw)
        except:
            data = data_raw

        # Lógica de negocio segmentada
        if tipo == "precio-actualizado":
            print(f"💰 [CAMBIO PRECIO] {data.get('producto')}: ${data.get('precio')}")
        elif tipo == "stock-critico":
            print(f"⚠️ [ALERTA STOCK] ¡PRODUCTO AGOTÁNDOSE! -> {data.get('producto')}")
        else:
            print(f"🔍 [SISTEMA] Evento '{tipo}' recibido.")

    def _ts(self):
        return time.strftime("%H:%M:%S")

    def detener(self):
        self.activo = False

if __name__ == "__main__":
    # Prueba con servidor de test o local
    monitor = ReceptorAlertas("https://sse.dev/test")
    try:
        asyncio.run(monitor.conectar())
    except KeyboardInterrupt:
        monitor.detener()
        print("\nMonitor detenido correctamente.")