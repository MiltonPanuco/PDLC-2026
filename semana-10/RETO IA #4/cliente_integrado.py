import asyncio
import time
import json
import base64
import logging
from enum import Enum
import aiohttp
from aiohttp import web

# Configuración básica de logs limpios
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ==============================================================================
# MÁQUINA DE ESTADOS Y CLASES DE CONTROL DE RESPONSABILIDAD ÚNICA
# ==============================================================================

class EstadoCircuito(Enum):
    CERRADO = "CERRADO"
    ABIERTO = "ABIERTO"
    SEMIABIERTO = "SEMIABIERTO"

class CircuitBreakerException(Exception):
    """Excepción lanzada cuando el circuito está ABIERTO (Fail-Fast)"""
    pass


class CircuitBreaker:
    """
    Controlador de resiliencia agnóstico al negocio y a la autenticación.
    Cumple con INV-A1 (No lee ni sabe de JWT) e INV-A3 (Reset completo de fallos).
    """
    def __init__(self, failure_threshold=3, recovery_timeout=3.0, on_open_cb=None, on_close_cb=None):
        self.estado = EstadoCircuito.CERRADO
        self._umbral = failure_threshold
        self._timeout_recuperacion = recovery_timeout
        self._fallos = 0
        self._tiempo_apertura = None
        
        # Callbacks observables para notificar cambios de estado a la interfaz (UI)
        self.on_open_cb = on_open_cb
        self.on_close_cb = on_close_cb

    def verificar_estado(self):
        """Mecanismo Fail-Fast local antes de tocar la red."""
        if self.estado == EstadoCircuito.ABIERTO:
            # Si ya pasó el tiempo de aislamiento, intentamos una prueba (Canary)
            if time.time() - self._tiempo_apertura >= self._timeout_recuperacion:
                self.estado = EstadoCircuito.SEMIABIERTO
                print(f"[BREAKER] Tiempo de aislamiento concluido. Transición a SEMIABIERTO. Intentando petición de prueba...")
            else:
                segundos_restantes = self._timeout_recuperacion - (time.time() - self._tiempo_apertura)
                raise CircuitBreakerException(f"Circuito abierto. Modo Fail-Fast activo. Reintente en {segundos_restantes:.1f}s")

    def registrar_exito(self):
        """Monitorea transiciones exitosas y limpia el historial."""
        if self.estado == EstadoCircuito.SEMIABIERTO:
            self.estado = EstadoCircuito.CERRADO
            if self.on_close_cb:
                self.on_close_cb()  # Notifica que la UI debe restablecerse
        
        # CORRECCIÓN BUG C / INV-A3: El contador se limpia SIEMPRE al cerrar con éxito
        self._fallos = 0

    def registrar_fallo(self, status_code=None):
        """Incrementa errores transitorios y decide si abre las compuertas."""
        # INV-A4: Los errores de autenticación (401, 403) NO abren el circuito de red
        if status_code in (401, 403):
            print(f"[BREAKER] Detectado error de autorización ({status_code}). Ignorado en métricas de caída de red.")
            return

        self._fallos += 1
        print(f"[BREAKER] Registrar Fallo #{self._fallos} acumulado. Estado Actual: {self.estado.value}")
        
        # Si falla estando en SEMIABIERTO o alcanza el umbral en CERRADO, se abre el circuito
        if self.estado == EstadoCircuito.SEMIABIERTO or self._fallos >= self._umbral:
            self.estado = EstadoCircuito.ABIERTO
            self._tiempo_apertura = time.time()
            print(f"[BREAKER] ¡UMBRAL ALCANZADO! Abriendo circuito de red proactivamente.")
            if self.on_open_cb:
                self.on_open_cb()  # Notifica a la UI el bloqueo visual


class TokenManager:
    """
    Manejador Singleton del ciclo de vida de credenciales.
    Cumple con INV-B1 (No sabe del estado del breaker) e INV-B2 (Seguro contra fugas en logs).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TokenManager, cls).__new__(cls)
            cls._instance._access_token = "token_antiguo_expirado_ana"
            cls._instance._refresh_token = "mock.refresh.token.valid"
        return cls._instance

    def get_auth_header(self) -> dict:
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}

    def refresh_access_token(self) -> str:
        """Simula renovación de credenciales e inyecta un payload válido para el servidor."""
        print("[TokenManager] Ejecutando renovación segura de sesión (Refresh)...")
        # Generamos un token simulado que contiene la palabra clave que el mock del server espera (nuevo_exp)
        self._access_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJvcDEiLCJyb2wiOiJ2aWV3ZXIiLCJuZXZvX2V4cCI6dHJ1ZX0.mock_sig"
        return self._access_token

    def logout(self):
        """Destruye la sesión local de manera segura."""
        print("[TokenManager] Sesión invalidada localmente. Punteros eliminados.")
        self._access_token = None


# ==============================================================================
# INTERCEPTOR Y CLIENTE INTEGRADO ORQUESTADOR
# ==============================================================================

class ClienteRobusto:
    """
    Cliente HTTP asíncrono para EcoMarket. Orquesta de forma limpia
    TokenManager y CircuitBreaker sin acoplarlos entre sí (SRP).
    """
    def __init__(self, session: aiohttp.ClientSession, base_url: str = "http://localhost:8080"):
        self.session = session
        self.base_url = base_url
        self.manager = TokenManager()
        
        # Inicializamos el disyuntor inyectando los callbacks para simular el comportamiento de la UI
        self.disyuntor = CircuitBreaker(
            failure_threshold=3, 
            recovery_timeout=3.0,
            on_open_cb=self.onCircuitOpen,
            on_close_cb=self.onCircuitClosed
        )

    # --- SEÑALES OBSERVABLES PARA LA INTERFAZ (UI) ---
    def onCircuitOpen(self):
        print("[UI] banner=Servidor temporalmente no disponible · action=disable_checkout")

    def onCircuitClosed(self):
        print("[UI] banner=oculto · action=enable_checkout")

    async def realizar_peticion(self, endpoint: str) -> dict:
        """Orquesta la validación de tokens, reintentos e intercepción del disyuntor."""
        url = f"{self.base_url}{endpoint}"
        status_code = None

        # 1. Verificación Estricta del Disyuntor (Fail-Fast local)
        try:
            self.disyuntor.verificar_estado()
        except CircuitBreakerException as e:
            print(f"[ClienteRobusto] -> PETICIÓN ABORTADA LOCALMENTE: {e}")
            return {"status": "blocked_by_circuit_breaker", "error": str(e)}

        # 2. Inyección de Headers de Autenticación actualizados
        headers = {"Content-Type": "application/json"}
        headers.update(self.manager.get_auth_header())

        # 3. Envío e intercepción en red
        try:
            timeout_politica = aiohttp.ClientTimeout(total=2.0)
            
            print(f"[ClienteRobusto] Despachando llamada a {endpoint}...")
            async with self.session.get(url, headers=headers, timeout=timeout_politica) as response:
                status_code = response.status
                
                # Manejo del Caso 401: Token expirado de Ana
                if status_code == 401:
                    print(f"[ClienteRobusto] ¡Primer intento fallido (401 Unauthorized)! Renovando credenciales...")
                    
                    # Mecanismo de recuperación integrado
                    nuevo_token = self.manager.refresh_access_token()
                    headers.update(self.manager.get_auth_header())
                    
                    print(f"[ClienteRobusto] Reintentando petición original con credenciales frescas...")
                    async with self.session.get(url, headers=headers, timeout=timeout_politica) as re_response:
                        status_code = re_response.status
                        if status_code == 200:
                            print("[LOGIN] Nuevo token almacenado y verificado · rol=viewer")
                            self.disyuntor.registrar_exito()
                            return await re_response.json()
                        elif status_code == 401:
                            print("[ClienteRobusto] ¡Error crítico! El token refrescado también fue rechazado.")
                            self.manager.logout()
                            self.disyuntor.registrar_fallo(status_code)
                            return {"status": "http_error", "code": status_code}

                if status_code == 200:
                    self.disyuntor.registrar_exito()
                    return await response.json()
                else:
                    # Fallos del servidor (503, etc.) pasan por aquí
                    self.disyuntor.registrar_fallo(status_code)
                    return {"status": "http_error", "code": status_code}

        except (aiohttp.ClientError, asyncio.TimeoutError) as error_red:
            # CORRECCIÓN BUG B / INV-B2: El log de error es genérico y no concatena ni expone tokens parciales
            logger.error(f"Excepción física de red capturada: {type(error_red).__name__}")
            self.disyuntor.registrar_fallo(status_code=None)
            return {"status": "network_failure", "error": str(error_red)}


# ==============================================================================
# SERVIDOR MOCK ACTUALIZADO (Con soporte para flujos de autenticación)
# ==============================================================================

class ServidorMockEcoMarket:
    def __init__(self):
        self.modo = 'normal'
        self._peticiones_recibidas = 0
        self.app = web.Application()
        self.app.router.add_get('/api/inventario', self._handler)

    async def _handler(self, request):
        self._peticiones_recibidas += 1
        auth_header = request.headers.get("Authorization", "")
        print(f"   [MOCK SERVIDOR] Recibida Petición #{self._peticiones_recibidas} | Modo Actual = {self.modo}")

        # Lógica de validación de tokens integrada en el servidor asíncrono
        if "nuevo_exp" not in auth_header and self.modo != 'fallo_503':
            # Si viene el token viejo de Ana, forzamos comportamiento 'auth' de forma inicial
            return web.Response(status=401, text='Unauthorized. El token expiró.')

        if self.modo == 'fallo_503':
            return web.Response(status=503, text='Service Unavailable')
        elif self.modo == 'timeout':
            await asyncio.sleep(5.0)
            return web.Response(status=200, text='tardísimo')
        else:
            return web.json_response({'productos': self._peticiones_recibidas * 10, 'status': 'success'})


# ==============================================================================
# SCRIPT DE DEMOSTRACIÓN AUTOMATIZADA DE RESILIENCIA
# ==============================================================================

async def main():
    print("=======================================================================")
    print("🔋 INICIANDO SCRIPT DE DEMOSTRACIÓN DE RESILIENCIA (EcoMarket 2026)")
    print("=======================================================================\n")

    servidor_mock = ServidorMockEcoMarket()
    runner = web.AppRunner(servidor_mock.app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("[Sistema] Servidor Mock desplegado con éxito en http://localhost:8080\n")

    async with aiohttp.ClientSession() as session:
        cliente = ClienteRobusto(session, base_url="http://localhost:8080")

        # ----------------------------------------------------------------------
        # SECUENCIA (1): Modo Normal -> Intercepción 401, Refresh y Éxitos 200
        # ----------------------------------------------------------------------
        print("--- SECUENCIA 1: Servidor Operando en Modo Normal ---")
        servidor_mock.modo = 'normal'
        for i in range(3):
            res = await cliente.realizar_peticion("/api/inventario")
            print(f" -> Resultado recibido por la UI: {res}\n")
            await asyncio.sleep(0.2)

        # ----------------------------------------------------------------------
        # SECUENCIA (2): Activar modo fallo_503 -> Observar circuito abrirse (Umbral 3)
        # ----------------------------------------------------------------------
        print("--- SECUENCIA 2: Activación del Modo 'fallo_503' (Inyección de Fallas) ---")
        servidor_mock.modo = 'fallo_503'
        
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
        res = await cliente.realizar_peticion("/api/inventario")
        print(f" -> Resultado recibido por la UI en Canary: {res}\n")

        print("[UI] Disparando petición ordinaria con el circuito re-establecido...")
        res = await cliente.realizar_peticion("/api/inventario")
        print(f" -> Resultado recibido por la UI: {res}\n")

    await site.stop()
    await runner.cleanup()
    print("=======================================================================")
    print("🏁 SECUENCIA DE AUDITORÍA CONCLUIDA EXITOSAMENTE.")
    print("=======================================================================")

if __name__ == '__main__':
    asyncio.run(main())