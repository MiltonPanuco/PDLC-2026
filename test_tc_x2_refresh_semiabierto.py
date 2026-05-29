# test_tc_x2_refresh_semiabierto.py
import asyncio
import pytest
import aiohttp
from cliente_integrado import ClienteRobusto, TokenManager, CircuitBreaker, EstadoCircuito

class MockSessionCanaryConRefresh:
    """Simulador de sesión para forzar la secuencia exacta del caso TC-X2 sin depender del server externo"""
    def __init__(self):
        self.intentos = 0

    def get(self, url, headers=None, timeout=None):
        self.intentos += 1
        class AsyncContext:
            def __init__(self, intento):
                self.intento = intento
            async def __aenter__(self):
                class FakeResponse:
                    # El primer intento falla con 401 para obligar al refresh en Semiabierto
                    status = 401 if self.intento == 1 else 200
                    async def json(self):
                        return {"productos": 150, "recuperado": True, "status": "success"}
                return FakeResponse()
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return AsyncContext(self.intentos)

@pytest.mark.asyncio
async def test_orden_ejecucion_refresh_en_semiabierto():
    # 1. SETUP: Instanciamos usando nuestro simulación de red controlada
    session_mock = MockSessionCanaryConRefresh()
    cliente = ClienteRobusto(session=session_mock, base_url="http://localhost:8080")
    
    # Forzamos manualmente al breaker a estar en SEMIABIERTO
    cliente.disyuntor.estado = EstadoCircuito.SEMIABIERTO
    cliente.manager._access_token = "token_viejo_caducado" 
    
    orden_eventos = []
    
    # Creamos los espías para verificar el orden secuencial estricto
    original_refresh = cliente.manager.refresh_access_token
    def spy_refresh(*args, **kwargs):
        orden_eventos.append("EJECUTÓ_REFRESH")
        return original_refresh(*args, **kwargs)
    cliente.manager.refresh_access_token = spy_refresh

    original_verificar = cliente.disyuntor.verificar_estado
    def spy_verificar(*args, **kwargs):
        orden_eventos.append("VERIFICÓ_ESTADO")
        return original_verificar(*args, **kwargs)
    cliente.disyuntor.verificar_estado = spy_verificar

    # 2. ACCIÓN: Disparamos la petición Canary
    resultado = await cliente.realizar_peticion("/api/inventario")

    # 3. VERIFICACIÓN: Comprobamos el cumplimiento de las restricciones asíncronas
    print(f"\nOrden cronológico detectado: {orden_eventos}")
    
    # Invariante 1: Primero se evalúa el estado local del disyuntor (Fail-Fast)
    assert orden_eventos[0] == "VERIFICÓ_ESTADO"
    
    # Invariante 2: Se ejecuta el refresh al detectar el 401 en el canal Canary
    assert "EJECUTÓ_REFRESH" in orden_eventos
    
    # Invariante 3: Al completarse el reintento exitoso (200), el circuito cierra limpio
    assert cliente.disyuntor.estado == EstadoCircuito.CERRADO
    assert cliente.disyuntor._fallos == 0