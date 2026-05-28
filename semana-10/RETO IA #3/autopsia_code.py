# cliente_robusto_con_bugs.py — Auditoría Interna TechNova
# Síntomas arriba. Encuentra las 3 líneas problema.

import time, base64, json, logging
from enum import Enum

logger = logging.getLogger(__name__)

class EstadoCircuito(Enum):
    CERRADO = "CERRADO"; ABIERTO = "ABIERTO"; SEMIABIERTO = "SEMIABIERTO"

class CircuitBreaker:
    def __init__(self, umbral=5, timeout=60):
        self.estado = EstadoCircuito.CERRADO
        self._umbral = umbral; self._timeout = timeout
        self._fallos = 0;     self._tiempo_apertura = None

    def ejecutar(self, fn, token_manager=None):
        # ─────────────────────────────────────── BUG A (síntoma A)
        if token_manager:
            token = token_manager.get_access_token()
            pad = 4 - len(token.split('.')[1]) % 4
            payload = json.loads(
                base64.urlsafe_b64decode(token.split('.')[1] + '=' * pad)
            )
            if payload.get('rol') not in ('admin', 'supervisor'):
                raise PermissionError(f"Rol '{payload['rol']}' no autorizado")
        # ────────────────────────────────────────────────────────────
        if self.estado == EstadoCircuito.ABIERTO:
            if time.time() - self._tiempo_apertura >= self._timeout:
                self.estado = EstadoCircuito.SEMIABIERTO
            else:
                raise Exception("CircuitOpenError")
        try:
            resultado = fn()
            self._on_exito()
            return resultado
        except Exception as e:
            self._on_fallo(e); raise

    def _on_exito(self):
        # ─────────────────────────────────────── BUG C (síntoma C)
        self.estado = EstadoCircuito.CERRADO
        # FALTA: self._fallos = 0
        # ────────────────────────────────────────────────────────────

    def _on_fallo(self, error):
        if not self._es_fallo_servidor(error): return
        self._fallos += 1
        if self._fallos >= self._umbral:
            self.estado = EstadoCircuito.ABIERTO
            self._tiempo_apertura = time.time()

    def _es_fallo_servidor(self, error):
        msg = str(error).lower()
        return '5' in str(error) or 'timeout' in msg or 'connection' in msg

class TokenManager:
    def __init__(self): self._access_token = 'dummy.access.token'
    def get_access_token(self): return self._access_token
    def get_auth_header(self): return {'Authorization': f'Bearer {self._access_token}'}
    def is_expiring_soon(self): return False

class ClienteRobusto:
    def __init__(self, tm, cb): self._tm = tm; self._cb = cb

    async def get_inventario(self):
        headers = self._tm.get_auth_header()
        try:
            return await self._cb.ejecutar(
                lambda: self._mock_http_get('/api/inventario'),
                token_manager=self._tm     # ← relacionado con Bug A
            )
        except Exception as e:
            # ─────────────────────────────────── BUG B (síntoma B)
            logger.error(
                f"Error: {e}. Auth: {headers['Authorization'][:40]}..."
            )
            # ────────────────────────────────────────────────────────
            raise

    def _mock_http_get(self, path):
        raise ConnectionError("503 Service Unavailable")