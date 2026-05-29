import logging

logger = logging.getLogger(__name__)

class TokenManager:
    """
    Manejador Singleton del ciclo de vida de credenciales JWT.
    INV-B1: No conoce ni referencia el estado del CircuitBreaker.
    INV-B2: El token nunca se concatena ni expone en logs.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._access_token = "token_antiguo_expirado"
            cls._instance._refresh_token = "mock.refresh.token.valid"
        return cls._instance

    def get_auth_header(self) -> dict:
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}

    def refresh_access_token(self) -> str:
        logger.info("[TokenManager] Ejecutando renovación segura de sesión...")
        self._access_token = (
            "eyJhbGciOiJIUzI1NiJ9"
            ".eyJzdWIiOiJvcDEiLCJyb2wiOiJ2aWV3ZXIiLCJuZXZvX2V4cCI6dHJ1ZX0"
            ".mock_sig"
        )
        return self._access_token

    def logout(self):
        logger.info("[TokenManager] Sesión invalidada localmente.")
        self._access_token = None