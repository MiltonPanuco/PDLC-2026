import asyncio
import time
import aiohttp
from aiohttp import web
from circuit_breaker import CircuitBreaker, CircuitBreakerException

# ==============================================================================
# INTEGRACIÓN DEL CLIENTE ROBUSTO CON INTERCEPTOR DE DISYUNTOR
# ==============================================================================

class ClienteRobusto:
    """
    Cliente HTTP asíncrono para EcoMarket equipado con protección proactiva 
    mediante el patrón Circuit Breaker.
    """
    def __init__(self, session: aiohttp.ClientSession, base_url: str = "http://localhost:8080"):
        self.session = session
        self.base_url = base_url
        # Inicializamos el disyuntor con un umbral de 3 fallos y un aislamiento corto de 3 segundos
        self.disyuntor = CircuitBreaker(failure_threshold=3, recovery_timeout=3.0)

    async def realizar_peticion(self, endpoint: str) -> dict:
        """
        Ejecuta una petición HTTP asíncrona verificando y actualizando el estado 
        del Circuit Breaker antes y después de interactuar con la red.
        """
        url = f"{self.base_url}{endpoint}"
        status_code = None

        # 1. Fase de Verificación Estricta (Mecanismo Fail-Fast local)
        try:
            self.disyuntor.verificar_estado()
        except CircuitBreakerException as e:
            print(f"[ClienteRobusto] -> PETICIÓN ABORTADA LOCALMENTE: {e}")
            return {"status": "blocked_by_circuit_breaker", "error": str(e)}

        # 2. Fase de Envío e Intercepción de Red de Alta Disponibilidad
        try:
            # Añadimos un timeout corto para que el modo 'timeout' del mock sea capturado de forma eficiente
            timeout_politica = aiohttp.ClientTimeout(total=2.0)
            
            async with self.session.get(url, timeout=timeout_politica) as response:
                status_code = response.status
                
                if status_code == 200:
                    # El servidor respondió de forma íntegra
                    self.disyuntor.registrar_exito()
                    return await response.json()
                else:
                    # El servidor devolvió una respuesta de error (Ej. 503 o 401)
                    self.disyuntor.registrar_fallo(status_code)
                    return {"status": "http_error", "code": status_code}

        except (aiohttp.ClientError, asyncio.TimeoutError) as error_red:
            # Captura excepciones físicas de red o vencimiento de socket (None en status_code)
            print(f"[ClienteRobusto] -> Excepción física de red detectada: {type(error_red).__name__}")
            self.disyuntor.registrar_fallo(status_code=None)
            return {"status": "network_failure", "error": str(error_red)}


# ==============================================================================
# SERVIDOR MOCK SUMINISTRADO (Integrado para ejecución en hilos asíncronos)
# ==============================================================================

class ServidorMockEcoMarket:
    def __init__(self):
        self.modo = 'normal'
        self._peticiones_recibidas = 0
        self.app = web.Application()
        self.app.router.add_get('/api/inventario', self._handler)

    async def _handler(self, request):
        self._peticiones_recibidas += 1
        print(f"   [MOCK SERVIDOR] Recibida Petición #{self._peticiones_recibidas} | Modo Actual = {self.modo}")

        if self.modo == 'fallo_503':
            return web.Response(status=503, text='Service Unavailable')
        elif self.modo == 'timeout':
            await asyncio.sleep(5.0)  # Supera el límite del ClientTimeout de 2s
            return web.Response(status=200, text='tardísimo')
        elif self.modo == 'auth':
            return web.Response(status=401, text='Unauthorized')
        else:
            return web.json_response({'productos': 42, 'timestamp': 'ahora'})


# ==============================================================================
# SCRIPT DE DEMOSTRACIÓN AUTOMATIZADA DE RESILIENCIA
# ==============================================================================

async def main():
    print("=======================================================================")
    print("🔋 INICIANDO SCRIPT DE DEMOSTRACIÓN DE RESILIENCIA (EcoMarket 2026)")
    print("Estudiante: VAZQUEZ TALAVERA MARIA BELEN (Matrícula: 24213132)")
    print("=======================================================================\n")

    # 1. Levantar el Servidor Mock en segundo plano de manera asíncrona
    servidor_mock = ServidorMockEcoMarket()
    runner = web.AppRunner(servidor_mock.app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("[Sistema] Servidor Mock desplegado con éxito en http://localhost:8080\n")

    # 2. Iniciar la sesión HTTP del cliente robusto
    async with aiohttp.ClientSession() as session:
        cliente = ClienteRobusto(session, base_url="http://localhost:8080")

        # ----------------------------------------------------------------------
        # SECUENCIA (1): Modo Normal -> 3 Peticiones Exitosas
        # ----------------------------------------------------------------------
        print("--- SECUENCIA 1: Servidor Operando en Modo Normal ---")
        servidor_mock.modo = 'normal'
        for i in range(3):
            res = await cliente.realizar_peticion("/api/inventario")
            print(f" -> Resultado recibido por la UI: {res}\n")
            await asyncio.sleep(0.2)

        # ----------------------------------------------------------------------
        # SECUENCIA (2): Activar modo fallo_503 -> Observar circuito abrirse
        # ----------------------------------------------------------------------
        print("--- SECUENCIA 2: Activación del Modo 'fallo_503' (Inyección de Fallas) ---")
        servidor_mock.modo = 'fallo_503'
        
        # Disparamos peticiones sucesivas para forzar la superación del umbral (threshold = 3)
        for i in range(4):
            print(f"[UI] Disparando petición ejecutada #{i+1}...")
            res = await cliente.realizar_peticion("/api/inventario")
            print(f" -> Resultado recibido por la UI: {res}\n")
            await asyncio.sleep(0.1)

        # ----------------------------------------------------------------------
        # SECUENCIA (3): Esperar timeout -> Observar el estado Semiabierto
        # ----------------------------------------------------------------------
        print("--- SECUENCIA 3: Aislamiento Fail-Fast y Espera del Timeout de Recuperación ---")
        print("[UI] El usuario intenta dar clic al botón de actualizar datos de manera inmediata...")
        res = await cliente.realizar_peticion("/api/inventario")
        print(f" -> Resultado recibido por la UI: {res}\n")

        print("[Sistema] Congelando tráfico y esperando 3.2 segundos (Superando recovery_timeout de 3s)...")
        await asyncio.sleep(3.2)

        # ----------------------------------------------------------------------
        # SECUENCIA (4): Restaurar modo normal -> Observar la recuperación (Canary)
        # ----------------------------------------------------------------------
        print("--- SECUENCIA 4: Restauración del Modo Normal y Prueba Canary de Éxito ---")
        servidor_mock.modo = 'normal'

        print("[UI] Disparando petición de renovación tras la espera...")
        # Esta petición transicionará a SEMIABIERTO, pasará al mock, recibirá 200 y CERRARÁ el circuito
        res = await cliente.realizar_peticion("/api/inventario")
        print(f" -> Resultado recibido por la UI en Canary: {res}\n")

        print("[UI] Disparando petición ordinaria con el circuito re-establecido...")
        res = await cliente.realizar_peticion("/api/inventario")
        print(f" -> Resultado recibido por la UI: {res}\n")

    # 3. Apagar el servidor mock de forma limpia al concluir las pruebas
    await site.stop()
    await runner.cleanup()
    print("=======================================================================")
    print("🏁 SECUENCIA DE AUDITORÍA CONCLUIDA EXITOSAMENTE.")
    print("=======================================================================")

if __name__ == '__main__':
    asyncio.run(main())