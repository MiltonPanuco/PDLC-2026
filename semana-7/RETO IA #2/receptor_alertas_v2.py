import asyncio
import json
import time
from datetime import datetime

# --- EVENT ROUTER (Semana Anterior) ---
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
            print(f"🔍 Evento '{evento}' ignorado (sin handler).")

# --- CLIENTE SSE MULTIPLEX ---
class ClienteSSEMultiplex:
    def __init__(self, base_url, modulos, router):
        self.base_url = base_url
        self.modulos = modulos # INV-C3: Lista no vacía
        self.router = router
        self.last_event_id = None
        self.activo = True
        self._buffer = {"id": None, "event": "message", "data": []}

    def construir_url(self):
        if not self.modulos:
            raise ValueError("INV-C3: La lista de módulos no puede estar vacía.")
        query = ",".join(self.modulos)
        return f"{self.base_url}?modulos={query}"

    def _parsear_linea(self, linea):
        # Caso Frontera: Comentario o línea vacía
        if not linea or linea.startswith(":"):
            return None, None
        
        # Caso Frontera: Línea sin ":" (campo sin valor)
        if ":" not in linea:
            return linea, ""
        
        # Caso Frontera: Múltiples ":" (el valor contiene ":")
        campo, valor = linea.split(":", 1)
        return campo.strip(), valor.strip()

    def _procesar_evento(self):
        # Unimos las líneas de data acumuladas
        raw_data = "".join(self._buffer["data"])
        if not raw_data: return

        try:
            parsed_data = json.loads(raw_data)
            # Despachamos al router
            self.router.despachar(self._buffer["event"], parsed_data)
        except json.JSONDecodeError:
            print("⚠️ Error: Data no es un JSON válido.")
        
        # Reset del buffer (Invariante de Estado Limpio)
        self._buffer = {"id": None, "event": "message", "data": []}

    async def _leer_stream(self, stream_iterable):
        """Simula la lectura de líneas desde un socket o mock."""
        for linea in stream_iterable:
            if not self.activo: break
            
            # Línea vacía = Fin de bloque SSE
            if not linea.strip():
                self._procesar_evento()
                continue
            
            campo, valor = self._parsear_linea(linea)
            if campo == "id":
                self.last_event_id = valor
            elif campo == "event":
                self._buffer["event"] = valor
            elif campo == "data":
                self._buffer["data"].append(valor)

# --- HANDLERS (Etapa 2) ---
ultima_conexion_activa = None

def handle_precio(data):
    if data['producto_id'] == "FORZAR_EXCEPCION":
        raise Exception("Fallo forzado para validación de robustez")
    
    cambio = abs(data['precio_nuevo'] - data['precio_anterior']) / data['precio_anterior']
    if cambio > 0.05:
        print(f"💰 [ALERTA PRECIO] {data['producto_id']} cambió {cambio:.1%}")

def handle_stock(data):
    s = data['stock_actual']
    urgencia = "CRITICO 🔴" if s <= 3 else "BAJO 🟡"
    print(f"⚠️ [STOCK {urgencia}] {data['producto_id']}: {s} unidades.")

def handle_pedido(data):
    if data['total'] > 500:
        print(f"📦 [PEDIDO VIP] ID: {data['pedido_id']} por ${data['total']}")

def handle_heartbeat(data):
    global ultima_conexion_activa
    ultima_conexion_activa = data['timestamp']
    print(f"💓 [SISTEMA] Heartbeat: {ultima_conexion_activa}")

# --- DEMOSTRACIÓN (Mock) ---
async def demo():
    router = EventRouter()
    router.registrar("precio-actualizado", handle_precio)
    router.registrar("stock-critico", handle_stock)
    router.registrar("pedido-nuevo", handle_pedido)
    router.registrar("sistema-ping", handle_heartbeat)

    cliente = ClienteSSEMultiplex("https://api.ecomarket.com/eventos", ["precios", "inventario"], router)

    mock_events = [
        "id: 001", "event: precio-actualizado", "data: {\"producto_id\": \"A1\", \"precio_anterior\": 100, \"precio_nuevo\": 110}", "",
        "id: 002", "event: stock-critico", "data: {\"producto_id\": \"B2\", \"stock_actual\": 2}", "",
        "id: 003", "event: pedido-nuevo", "data: {\"pedido_id\": \"P-99\", \"total\": 750}", "",
        "id: 004", "event: sistema-ping", "data: {\"timestamp\": \"2026-03-27T15:00:00Z\"}", "",
        "id: 005", "event: precio-actualizado", "data: {\"producto_id\": \"FORZAR_EXCEPCION\", \"precio_anterior\": 10, \"precio_nuevo\": 20}", "",
        "id: 006", "event: stock-critico", "data: {\"producto_id\": \"C3\", \"stock_actual\": 8}", "",
        ": linea de comentario ignorada", "data: Evento sin ID ni tipo explícito", ""
    ]

    print("--- INICIANDO VALIDACIÓN DE FLUJO ---")
    await cliente._leer_stream(mock_events)

if __name__ == "__main__":
    asyncio.run(demo())