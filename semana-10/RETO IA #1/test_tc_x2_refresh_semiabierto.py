import asyncio
import pytest
from cliente_integrado import ClienteRobusto, TokenManager, CircuitBreaker, EstadoCircuito

class MockSessionFake:
    """Simulador básico para contar cuántas peticiones llegan al servidor."""
    def __init__(self):
        self.peticiones_enviadas = 0

    async def get(self, url, headers=None, timeout=None):
        self.peticiones_enviadas += 1
        # Simulamos un manejador asíncrono básico para la respuesta con un context manager
        class AsyncContext:
            async def __aenter__(self):
                class FakeResponse:
                    status = 200
                    async def json(self): return {"productos": 90, "status": "success"}
                return FakeResponse()
            async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        return AsyncContext()

@pytest.mark.asyncio
async def test_orden_ejecucion_refresh_en_semiabierto():
    # 1. SETUP: Instanciamos los componentes y forzamos el escenario
    tm = TokenManager()
    tm._access_token = "token_antiguo_expirado_ana" # Forzamos que requiera refresh
    
    session_fake = MockSessionFake()
    cliente = ClienteRobusto(session=session_fake, base_url="http://localhost:8080")
    
    # Forzamos manualmente al breaker a estar en SEMIABIERTO
    cliente.disyuntor.estado = EstadoCircuito.SEMIABIERTO
    
    # Llevaremos un registro del orden de los eventos mediante una lista compartida
    orden_eventos = []
    
    # Modificamos los métodos originales para registrar exactamente cuándo se ejecutan
    original_refresh = tm.refresh_access_token
    def spy_refresh():
        orden_eventos.append("EJECUTÓ_REFRESH")
        return original_refresh()
    tm.refresh_access_token = spy_refresh

    original_verificar = cliente.disyuntor.verificar_estado
    def spy_verificar():
        orden_eventos.append("VERIFICÓ_ESTADO")
        return original_verificar()
    cliente.disyuntor.verificar_estado = spy_verificar

    # 2. ACCIÓN: Disparamos la petición ordinaria al inventario
    resultado = await cliente.realizar_peticion("/api/inventario")

    # 3. VERIFICACIÓN: Comprobamos el orden de la pila distribuida
    # Primero se debió verificar el estado (Fail-Fast local del breaker)
    assert orden_eventos[0] == "VERIFICÓ_ESTADO"
    # Justo después, el ClienteRobusto nota el token expirado y corre el refresh antes de tocar el socket
    assert orden_eventos[1] == "EJECUTÓ_REFRESH"
    
    # Al final, el servidor mock solo debió recibir una sola petición física canary
    assert session_fake.peticiones_enviadas == 1
    assert resultado["status"] == "success"
    assert cliente.disyuntor.estado == EstadoCircuito.CERRADO