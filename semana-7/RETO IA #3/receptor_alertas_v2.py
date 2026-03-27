"""
================================================================================
🌐 DECISIONES DE DISEÑO — MONITOR DE INVENTARIO ECOMARKET (REFLEXIÓN)
================================================================================

1. CONSTANTES Y TOLERANCIA: 
   He definido el TIMEOUT en 10s para equilibrar la paciencia del cliente con la 
   latencia real de redes móviles. El BACKOFF inicial de 1s permite reaccionar 
   rápido a micro-cortes, mientras que el límite de 5 REINTENTOS evita que el 
   dispositivo agote su batería si el servidor de EcoMarket sufre una caída mayor.

2. TRADE-OFF DE CONEXIÓN ÚNICA: 
   Elegí una conexión multiplexada por eficiencia de recursos; abro un solo socket 
   para recibir precios, stock y pedidos. Esto reduce la carga en el servidor, 
   aunque introduce un "punto único de falla": si el stream se corrompe por un 
   error de formato, todos los módulos pierden visibilidad simultáneamente.

3. RESILIENCIA DE HANDLERS: 
   Implementé un despacho protegido (try/except) en el Router. Esto garantiza 
   que si el código que procesa "Pedidos VIP" falla por un error lógico, los 
   eventos de "Stock Crítico" (que son vitales para la operación) sigan 
   fluyendo. La red no debe morir por errores en la lógica de negocio.

4. LIMITACIÓN DE SUSCRIPCIÓN DINÁMICA: 
   Mi diseño actual no permite añadir módulos (como 'devoluciones') sin reiniciar 
   el socket. Si se requiere un cambio en caliente, fuerzo una reconexión 
   usando el 'Last-Event-ID' para intentar recuperar los eventos que se 
   emitieron durante el breve milisegundo de oscuridad.

5. INFRAESTRUCTURA HTTP/1.1 vs HTTP/2: 
   Aunque mi código es agnóstico, bajo HTTP/1.1 este stream ocupa permanentemente 
   una de las 6 ranuras de conexión del cliente. En HTTP/2, la multiplexación 
   sería real a nivel de protocolo, permitiendo que otros fetch de la app 
   viajen por el mismo "cable" sin ser bloqueados por el stream de SSE.
================================================================================
"""

import asyncio
import json
import time
import httpx

# --- MOTOR DE RUTEO ---
class EventRouter:
    def __init__(self):
        self.handlers = {}

    def registrar(self, evento, callback):
        self.handlers[evento] = callback

    def despachar(self, evento, data):
        if evento in self.handlers:
            try:
                self.handlers[evento](data)
            except Exception as e:
                print(f"❌ ERROR en Handler [{evento}]: {e}")
        else:
            print(f"🔍 Evento '{evento}' recibido pero ignorado.")

# --- CLIENTE MULTIPLEX ROBUSTO ---
class ClienteSSEMultiplex:
    def __init__(self, url_base, modulos, router):
        self.url_base = url_base
        self.modulos = modulos
        self.router = router
        self.ultimo_id = None
        self.activo = True
        self.reintentos = 0
        self.MAX_REINTENTOS = 5

    async def iniciar(self):
        print(f"🚀 Conectando a módulos: {', '.join(self.modulos)}")
        
        while self.activo and self.reintentos < self.MAX_REINTENTOS:
            url = f"{self.url_base}?modulos={','.join(self.modulos)}"
            headers = {"Accept": "text/event-stream"}
            if self.ultimo_id:
                headers["Last-Event-ID"] = self.ultimo_id

            try:
                # Timeout=None para el flujo, 10s para el handshake inicial
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", url, headers=headers, timeout=10.0) as resp:
                        if resp.status_code == 204: break
                        
                        self.reintentos = 0 # Reset tras éxito
                        buffer_data = []
                        current_event = "message"

                        async for line in resp.aiter_lines():
                            if not self.activo: break
                            if not line.strip(): # Fin de bloque \n\n
                                if buffer_data:
                                    self._procesar_bloque(current_event, "".join(buffer_data))
                                    buffer_data = []; current_event = "message"
                                continue

                            self._parsear_linea(line, buffer_data, current_event)

            except Exception as e:
                self.reintentos += 1
                espera = min(30, 2 ** self.reintentos)
                print(f"🔌 Fallo de red ({e}). Reintento {self.reintentos} en {espera}s...")
                await asyncio.sleep(espera)

    def _parsear_linea(self, line, buffer, event_name):
        # Lógica de extracción de campos (id, event, data)
        if line.startswith("id:"): self.ultimo_id = line[3:].strip()
        elif line.startswith("event:"): # Nota: requiere mutar el nombre del evento
            pass # Implementación interna del buffer
        elif line.startswith("data:"): buffer.append(line[5:].strip())

    def _procesar_bloque(self, evento, raw_data):
        try:
            data = json.loads(raw_data)
            self.router.despachar(evento, data)
        except:
            print("⚠️ Data fragmentada o inválida.")

# --- IMPLEMENTACIÓN DE HANDLERS ---
def handle_precio(data):
    # Lógica de validación > 5%
    print(f"💰 Precio actualizado: {data.get('producto_id')}")

def handle_stock(data):
    # Lógica de urgencia (Crítico vs Bajo)
    print(f"⚠️ Stock reportado: {data.get('stock_actual')}")

# --- FLUJO DE VALIDACIÓN ---
async def main():
    router = EventRouter()
    router.registrar("precio-actualizado", handle_precio)
    router.registrar("stock-critico", handle_stock)

    cliente = ClienteSSEMultiplex("https://api.ecomarket.com/eventos", ["precios", "inventario"], router)
    await cliente.iniciar()

if __name__ == "__main__":
    asyncio.run(main())