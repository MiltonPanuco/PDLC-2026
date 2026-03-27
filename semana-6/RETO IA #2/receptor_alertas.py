import asyncio
import time
import httpx
import json

class ReceptorAlertas:
    """
    Motor SSE para EcoMarket.
    
    TRADE-OFF ETAPA 1 (Conexión): 
    Se usa httpx.stream en lugar de una petición GET tradicional para evitar 
    cargar todo el cuerpo en RAM, permitiendo procesar streams infinitos.
    
    TRADE-OFF ETAPA 2 (Parsing): 
    El procesamiento es síncrono. Si el procesamiento de un evento 'data' 
    es muy pesado, bloqueará la lectura de la siguiente línea del stream.
    
    TRADE-OFF ETAPA 3 (Reconexión): 
    El backoff exponencial protege al servidor de denegación de servicio (DoS) 
    involuntario cuando hay caídas masivas de clientes.
    """
    
    def __init__(self, url):
        self.url = url
        self.ultimo_id = None
        self.retry_ms = 3000
        self.activo = True
        self.intentos = 0
        self.max_intentos = 5

    async def iniciar(self):
        print(f"🚀 [{self._ts()}] Iniciando Receptor...")
        
        while self.activo and self.intentos < self.max_intentos:
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            }
            if self.ultimo_id:
                headers["Last-Event-ID"] = str(self.ultimo_id)
                print(f"📡 [{self._ts()}] Reintentando con Last-Event-ID: {self.ultimo_id}")

            try:
                # ETAPA 1: Timeout de 30s para el handshake inicial
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream("GET", self.url, headers=headers) as resp:
                        
                        if resp.status_code == 204: # Restricción: No Content
                            print(f"🛑 [{self._ts()}] Servidor cerró flujo (204).")
                            self.activo = False
                            break
                        
                        if resp.status_code != 200:
                            raise Exception(f"HTTP {resp.status_code}")

                        self.intentos = 0 # Reset de éxito
                        buffer = {"id": None, "event": "message", "data": []}

                        async for line in resp.aiter_lines():
                            if not self.activo: break
                            
                            # ETAPA 2: Acumular hasta línea en blanco
                            if not line.strip():
                                if buffer["data"]:
                                    self._dispatch(buffer)
                                    buffer = {"id": None, "event": "message", "data": []}
                                continue

                            self._parse_line(line, buffer)

            except Exception as e:
                self.intentos += 1
                espera = (self.retry_ms / 1000) * (2 ** (self.intentos - 1))
                print(f"🔌 [{self._ts()}] Error: {e}. Reconexión en {espera}s...")
                await asyncio.sleep(espera)

    def _parse_line(self, line, buffer):
        if line.startswith("id:"):
            buffer["id"] = line[3:].strip()
            self.ultimo_id = buffer["id"]
        elif line.startswith("event:"):
            buffer["event"] = line[6:].strip()
        elif line.startswith("data:"):
            buffer["data"].append(line[5:].strip())
        elif line.startswith("retry:"):
            self.retry_ms = int(line[6:].strip())

    def _dispatch(self, buffer):
        tipo = buffer["event"]
        raw = "".join(buffer["data"])
        
        try:
            data = json.loads(raw)
        except:
            data = raw

        if tipo == "precio-actualizado":
            print(f"💰 [PRECIO] {data['producto']} ahora cuesta ${data['precio']}")
        elif tipo == "stock-critico":
            print(f"⚠️ [STOCK] ¡URGENTE! {data['producto']} quedan {data['stock']} unidades.")
        else:
            print(f"🔍 [INFO] Evento '{tipo}' recibido (sin manejador específico).")

    def _ts(self):
        return time.strftime("%H:%M:%S")

if __name__ == "__main__":
    receptor = ReceptorAlertas("https://sse.dev/test")
    try:
        asyncio.run(receptor.iniciar())
    except KeyboardInterrupt:
        print("\nCierre limpio solicitado.")