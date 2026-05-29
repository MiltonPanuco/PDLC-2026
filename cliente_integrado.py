# cliente_integrado.py
import asyncio
import time
import aiohttp
import logging
from enum import Enum

# CONFIGURACIÓN AUTOMÁTICA DE BITÁCORA EN LA RAÍZ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("demo_resiliencia.log", mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class EstadoCircuito(Enum):
    CERRADO = "CERRADO"
    ABIERTO = "ABIERTO"
    SEMIABIERTO = "SEMIABIERTO"

class CircuitBreakerException(Exception):
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=3.0, on_open_cb=None, on_close_cb=None):
        self.estado = EstadoCircuito.CERRADO
        self._umbral = failure_threshold
        self._timeout_recuperacion = recovery_timeout
        self._fallos = 0
        self._tiempo_apertura = None
        self.on_open_cb = on_open_cb
        self.on_close_cb = on_close_cb

    def verificar_estado(self):
        if self.estado == EstadoCircuito.ABIERTO:
            if time.time() - self._tiempo_apertura >= self._timeout_recuperacion:
                self.estado = EstadoCircuito.SEMIABIERTO
                logging.info("[BREAKER] Tiempo de aislamiento concluido. Transición a SEMIABIERTO. Intentando petición de prueba...")
            else:
                segundos_restantes = self._timeout_recuperacion - (time.time() - self._tiempo_apertura)
                raise CircuitBreakerException(f"Circuito abierto. Modo Fail-Fast activo. Reintente en {segundos_restantes:.1f}s")

    def registrar_exito(self):
        if self.estado == EstadoCircuito.SEMIABIERTO:
            self.estado = EstadoCircuito.CERRADO
            if self.on_close_cb:
                self.on_close_cb()
        self._fallos = 0

    def registrar_fallo(self, status_code=None):
        if status_code in (401, 403):
            logging.info(f"[BREAKER] Detectado error de autorización ({status_code}). Ignorado en métricas de caída de red.")
            return

        self._fallos += 1
        logging.info(f"[BREAKER] Registrar Fallo #{self._fallos} acumulado. Estado Actual: {self.estado.value}")
        
        if self.estado == EstadoCircuito.SEMIABIERTO or self._fallos >= self._umbral:
            self.estado = EstadoCircuito.ABIERTO
            self._tiempo_apertura = time.time()
            logging.info("[BREAKER] ¡UMBRAL ALCANZADO! Abriendo circuito de red proactivamente.")
            if self.on_open_cb:
                self.on_open_cb()

class TokenManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TokenManager, cls).__new__(cls)
            cls._instance._access_token = "token_antiguo_expirado_ana"
        return cls._instance

    def get_auth_header(self) -> dict:
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}

    def refresh_access_token(self) -> str:
        logging.info("[TokenManager] Ejecutando renovación segura de sesión (Refresh)...")
        self._access_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJvcDEiLCJyb2wiOiJ2aWV3ZXIiLCJuZXZvX2V4cCI6dHJ1ZX0.mock_sig"
        return self._access_token

    def logout(self):
        logging.info("[TokenManager] Sesión invalidada localmente. Punteros eliminados.")
        self._access_token = None

class ClienteRobusto:
    def __init__(self, session: aiohttp.ClientSession, base_url: str = "http://localhost:8080"):
        self.session = session
        self.base_url = base_url
        self.manager = TokenManager()
        self.disyuntor = CircuitBreaker(
            failure_threshold=3, 
            recovery_timeout=3.0,
            on_open_cb=self.onCircuitOpen,
            on_close_cb=self.onCircuitClosed
        )

    def onCircuitOpen(self):
        logging.info("[UI] banner=Servidor temporalmente no disponible · action=disable_checkout")

    def onCircuitClosed(self):
        logging.info("[UI] banner=oculto · action=enable_checkout")

    async def realizar_peticion(self, endpoint: str) -> dict:
        url = f"{self.base_url}{endpoint}"
        status_code = None

        try:
            self.disyuntor.verificar_estado()
        except CircuitBreakerException as e:
            return {"status": "blocked_by_circuit_breaker", "error": str(e)}

        headers = {"Content-Type": "application/json"}
        headers.update(self.manager.get_auth_header())

        try:
            timeout_politica = aiohttp.ClientTimeout(total=2.0)
            logging.info(f"[ClienteRobusto] Despachando llamada a {endpoint}...")
            async with self.session.get(url, headers=headers, timeout=timeout_politica) as response:
                status_code = response.status
                
                if status_code == 401:
                    self.disyuntor.registrar_fallo(401)
                    logging.info("[ClienteRobusto] ¡Primer intento fallido (401 Unauthorized)! Renovando credenciales...")
                    self.manager.refresh_access_token()
                    headers.update(self.manager.get_auth_header())
                    
                    logging.info("[ClienteRobusto] Reintentando petición original con credenciales frescas...")
                    async with self.session.get(url, headers=headers, timeout=timeout_politica) as re_response:
                        status_code = re_response.status
                        if status_code == 200:
                            logging.info("[LOGIN] Nuevo token almacenado y verificado · rol=viewer")
                            self.disyuntor.registrar_exito()
                            return await re_response.json()
                        elif status_code == 401:
                            logging.info("[ClienteRobusto] ¡Error crítico! El token refrescado también fue rechazado.")
                            self.manager.logout()
                            self.disyuntor.registrar_fallo(status_code)
                            return {"status": "http_error", "code": status_code}

                if status_code == 200:
                    self.disyuntor.registrar_exito()
                    return await response.json()
                else:
                    self.disyuntor.registrar_fallo(status_code)
                    return {"status": "http_error", "code": status_code}

        except (aiohttp.ClientError, asyncio.TimeoutError) as error_red:
            logging.error(f"Excepción física de red capturada: {type(error_red).__name__}")
            self.disyuntor.registrar_fallo(status_code=None)
            return {"status": "network_failure", "error": str(error_red)}

async def main():
    logging.info("=======================================================================")
    logging.info("INICIANDO SCRIPT DE DEMOSTRACIÓN DE RESILIENCIA (EcoMarket 2026)")
    logging.info("=======================================================================\n")
    
    async with aiohttp.ClientSession() as session:
        cliente = ClienteRobusto(session, base_url="http://localhost:8080")

        logging.info("--- SECUENCIA 1: Servidor Operando en Modo Normal ---")
        for _ in range(3):
            res = await cliente.realizar_peticion("/api/inventario")
            logging.info(f" -> Resultado recibido por la UI: {res}\n")
            await asyncio.sleep(0.2)

        logging.info("--- SECUENCIA 2: Activación del Modo 'fallo_503' (Inyección de Fallas) ---")
        for i in range(4):
            logging.info(f"[UI] Disparando petición ejecutada #{i+1}...")
            res = await cliente.realizar_peticion("/api/inventario")
            logging.info(f" -> Resultado recibido por la UI: {res}\n")
            await asyncio.sleep(0.1)

        logging.info("--- SECUENCIA 3: Aislamiento Fail-Fast y Espera del Timeout ---")
        res = await cliente.realizar_peticion("/api/inventario")
        logging.info(f" -> Resultado recibido por la UI: {res}\n")

        logging.info("[Sistema] Congelando tráfico y esperando 3.2 segundos...")
        await asyncio.sleep(3.2)

        logging.info("--- SECUENCIA 4: Restauración del Modo Normal y Prueba Canary de Éxito ---")
        res = await cliente.realizar_peticion("/api/inventario")
        logging.info(f" -> Resultado recibido por la UI en Canary: {res}\n")

        res = await cliente.realizar_peticion("/api/inventario")
        logging.info(f" -> Resultado recibido por la UI: {res}\n")

if __name__ == '__main__':
    asyncio.run(main())