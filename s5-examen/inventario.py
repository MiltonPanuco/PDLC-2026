"""
Examen Práctico 1 - Monitor de Inventario EcoMarket
Programación Distribuida del Lado del Cliente
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import aiohttp

BASE_URL       = "http://ecomarket.local/api/v1"
TOKEN          = "eyJ0eXAiO..."
INTERVALO_BASE = 5
INTERVALO_MAX  = 60
TIMEOUT        = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


class Observador(ABC):
    @abstractmethod
    async def actualizar(self, inventario: dict) -> None:
        pass


class MonitorInventario:

    def __init__(self):
        self._observadores: list[Observador] = []
        self._ultimo_etag:   str | None = None
        self._ultimo_estado: dict | None = None
        self._ejecutando:    bool = False
        self._intervalo:     float = INTERVALO_BASE

    def suscribir(self, obs: Observador) -> None:
        if obs not in self._observadores:
            self._observadores.append(obs)
            log.info(f"Observador suscrito: {type(obs).__name__}")

    def desuscribir(self, obs: Observador) -> None:
        if obs in self._observadores:
            self._observadores.remove(obs)

    async def _notificar(self, inventario: dict) -> None:
        # try/except por observador para que si uno falla no corte a los demás
        for obs in self._observadores:
            try:
                await obs.actualizar(inventario)
            except Exception as e:
                log.error(f"Falló el observador {type(obs).__name__}: {e}")

    async def _consultar_inventario(self) -> dict | None:
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
        }
        if self._ultimo_etag:
            headers["If-None-Match"] = self._ultimo_etag

        timeout = aiohttp.ClientTimeout(total=TIMEOUT)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{BASE_URL}/inventario", headers=headers) as resp:

                    if resp.status == 200:
                        body = await resp.json()
                        if body.get("productos") is None:
                            log.warning("Respuesta 200 sin campo 'productos', se ignora")
                            return None
                        self._ultimo_etag   = resp.headers.get("ETag")
                        self._ultimo_estado = body
                        log.info(f"Inventario recibido — {len(body['productos'])} productos")
                        return body

                    elif resp.status == 304:
                        log.debug("304 - sin cambios")
                        return None

                    elif 400 <= resp.status < 500:
                        log.error(f"Error {resp.status} - revisar token o headers, no se reintenta")
                        return None

                    elif resp.status >= 500:
                        log.warning(f"Error {resp.status} en servidor")
                        return None

        except asyncio.TimeoutError:
            log.warning("Timeout - se reintenta en el próximo ciclo")
            return None

        except aiohttp.ClientConnectionError as e:
            log.warning(f"Sin conexión: {e} - se reintenta en el próximo ciclo")
            return None

        except Exception as e:
            log.error(f"Error inesperado: {e}")
            return None

    async def iniciar(self) -> None:
        # por ahora intervalo fijo, el backoff adaptativo lo agrego después
        self._ejecutando = True
        log.info("Monitor iniciado")

        while self._ejecutando:
            datos = await self._consultar_inventario()
            if datos is not None:
                await self._notificar(datos)
            await asyncio.sleep(self._intervalo)

    def detener(self) -> None:
        self._ejecutando = False
        log.info("Monitor detenido")


class ModuloCompras(Observador):
    async def actualizar(self, inventario: dict) -> None:
        productos_bajos = [
            p for p in inventario.get("productos", [])
            if p.get("status") == "BAJO_MINIMO"
        ]
        if productos_bajos:
            log.info(f"[COMPRAS] {len(productos_bajos)} producto(s) bajo mínimo:")
            for p in productos_bajos:
                print(
                    f"  ⚠️  {p['nombre']} (ID: {p['id']}) — "
                    f"Stock: {p['stock']} / Mínimo: {p['stock_minimo']} [{p['almacen']}]"
                )
        else:
            log.info("[COMPRAS] Todo en niveles normales")


class ModuloAlertas(Observador):
    async def actualizar(self, inventario: dict) -> None:
        productos_bajos = [
            p for p in inventario.get("productos", [])
            if p.get("status") == "BAJO_MINIMO"
        ]
        for producto in productos_bajos:
            await self._enviar_alerta(producto)

    async def _enviar_alerta(self, producto: dict) -> None:
        payload = {
            "producto_id":  producto["id"],
            "stock_actual": producto["stock"],
            "stock_minimo": producto["stock_minimo"],
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        }
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type":  "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{BASE_URL}/alertas", json=payload, headers=headers
                ) as resp:
                    if resp.status == 201:
                        log.info(f"[ALERTAS] Alerta enviada para {producto['id']}")
                    elif resp.status == 422:
                        log.error(f"[ALERTAS] 422 - payload inválido, no se reintenta")
                    else:
                        log.warning(f"[ALERTAS] Respuesta inesperada {resp.status}")

        except (asyncio.TimeoutError, aiohttp.ClientConnectionError) as e:
            log.warning(f"[ALERTAS] Error de red: {e}")

        except Exception as e:
            log.error(f"[ALERTAS] Error inesperado: {e}")


async def main():
    monitor = MonitorInventario()
    monitor.suscribir(ModuloCompras())
    monitor.suscribir(ModuloAlertas())
    await monitor.iniciar()


if __name__ == "__main__":
    asyncio.run(main())