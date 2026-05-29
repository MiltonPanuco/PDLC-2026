"""
Examen Práctico 1 - Monitor de Inventario EcoMarket
Programación Distribuida del Lado del Cliente
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import aiohttp

# Datos de conexión al servidor
BASE_URL       = "http://ecomarket.local/api/v1"
TOKEN          = "eyJ0eXAiO..."   # token que nos dieron
INTERVALO_BASE = 5                # cada cuántos segundos consultamos
INTERVALO_MAX  = 60               # no esperamos más de esto aunque haya backoff
TIMEOUT        = 10               # si en 10 seg no responde, timeout

# Para ver los logs en consola con fecha y nivel
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


# Clase base que deben implementar todos los observadores
# usamos ABC para forzar que cada subclase defina actualizar()
class Observador(ABC):
    @abstractmethod
    async def actualizar(self, inventario: dict) -> None:
        pass


class MonitorInventario:
    # Esta clase es el Observable del patrón Observer
    # mantiene la lista de quién quiere recibir notificaciones

    def __init__(self):
        self._observadores: list[Observador] = []
        self._ultimo_etag:   str | None = None   # para el header If-None-Match
        self._ultimo_estado: dict | None = None  # comparamos contra esto para ver si hubo cambio
        self._ejecutando:    bool = False
        self._intervalo:     float = INTERVALO_BASE

    def suscribir(self, obs: Observador) -> None:
        # evitamos duplicados por si alguien suscribe el mismo observador dos veces
        if obs not in self._observadores:
            self._observadores.append(obs)
            log.info(f"Observador suscrito: {type(obs).__name__}")

    def desuscribir(self, obs: Observador) -> None:
        if obs in self._observadores:
            self._observadores.remove(obs)
            log.info(f"Observador removido: {type(obs).__name__}")

    async def _notificar(self, inventario: dict) -> None:
        # notificamos a todos por igual, sin preguntar qué tipo son
        # el try/except adentro es importante: si un observador falla,
        # los demás todavía deben recibir la notificación
        for obs in self._observadores:
            try:
                await obs.actualizar(inventario)
            except Exception as e:
                log.error(f"Falló el observador {type(obs).__name__}: {e}")

    async def _consultar_inventario(self) -> dict | None:
        # construimos los headers, el ETag solo va si ya tenemos uno guardado
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
                        # validamos que venga el campo productos antes de usarlo
                        if body.get("productos") is None:
                            log.warning("Respuesta 200 sin campo 'productos', se ignora")
                            return None
                        # guardamos el nuevo ETag para la próxima consulta
                        self._ultimo_etag   = resp.headers.get("ETag")
                        self._ultimo_estado = body
                        self._intervalo     = INTERVALO_BASE  # resetear backoff si había
                        log.info(f"Inventario recibido — {len(body['productos'])} productos")
                        return body

                    elif resp.status == 304:
                        # el servidor dice que no cambió nada desde nuestro ETag
                        log.debug("304 - sin cambios en inventario")
                        return None

                    elif 400 <= resp.status < 500:
                        # error nuestro (token malo, header mal formado, etc.)
                        # no tiene sentido reintentar exactamente lo mismo
                        log.error(f"Error {resp.status} - revisar token o headers, no se reintenta")
                        return None

                    elif resp.status >= 500:
                        # el servidor está saturado, esperamos más tiempo
                        self._intervalo = min(self._intervalo * 2, INTERVALO_MAX)
                        log.warning(f"Error {resp.status} en servidor - backoff a {self._intervalo}s")
                        return None

        except asyncio.TimeoutError:
            # el servidor tardó más de TIMEOUT segundos, seguimos en el próximo ciclo
            log.warning(f"Timeout en /inventario (>{TIMEOUT}s) - se reintenta en el próximo ciclo")
            return None

        except aiohttp.ClientConnectionError as e:
            # no se pudo conectar (DNS, red caída, etc.)
            log.warning(f"Sin conexión: {e} - se reintenta en el próximo ciclo")
            return None

        except Exception as e:
            # cualquier otro error raro no debe matar el ciclo
            log.error(f"Error inesperado en _consultar_inventario: {e}")
            return None

    async def iniciar(self) -> None:
        self._ejecutando = True
        ciclos_sin_cambio = 0
        log.info("Monitor iniciado")

        while self._ejecutando:
            datos = await self._consultar_inventario()

            if datos is not None:
                # solo notificamos si el inventario realmente cambió
                if datos != self._ultimo_estado:
                    ciclos_sin_cambio = 0
                    self._intervalo   = INTERVALO_BASE
                    await self._notificar(datos)
                else:
                    ciclos_sin_cambio += 1
            else:
                ciclos_sin_cambio += 1
                # si llevamos varios ciclos sin novedad, aumentamos el intervalo
                if ciclos_sin_cambio >= 3:
                    self._intervalo = min(self._intervalo * 1.5, INTERVALO_MAX)
                    log.debug(f"Backoff adaptativo: intervalo={self._intervalo:.1f}s")

            # sleep no bloqueante: el event loop puede atender otras cosas mientras esperamos
            await asyncio.sleep(self._intervalo)

    def detener(self) -> None:
        # solo cambiamos la bandera, el while termina solo al final del ciclo actual
        self._ejecutando = False
        log.info("Monitor detenido")


class ModuloCompras(Observador):
    # imprime los productos bajo mínimo cuando llega una actualización

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
            log.info("[COMPRAS] Todo el inventario en niveles normales")


class ModuloAlertas(Observador):
    # manda un POST al servidor por cada producto que esté bajo el mínimo

    async def actualizar(self, inventario: dict) -> None:
        productos_bajos = [
            p for p in inventario.get("productos", [])
            if p.get("status") == "BAJO_MINIMO"
        ]
        for producto in productos_bajos:
            await self._enviar_alerta(producto)

    async def _enviar_alerta(self, producto: dict) -> None:
        # armamos el payload con los 4 campos que pide el endpoint POST /alertas
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
                        log.info(f"[ALERTAS] Alerta enviada para {producto['id']} ({producto['nombre']})")
                    elif resp.status == 422:
                        # campos mal mandados, no tiene caso reintentar igual
                        log.error(f"[ALERTAS] 422 - payload inválido para {producto['id']}, no se reintenta")
                    else:
                        log.warning(f"[ALERTAS] Respuesta inesperada {resp.status} para {producto['id']}")

        except (asyncio.TimeoutError, aiohttp.ClientConnectionError) as e:
            log.warning(f"[ALERTAS] Error de red al enviar alerta: {e}")

        except Exception as e:
            log.error(f"[ALERTAS] Error inesperado: {e}")


async def main():
    monitor = MonitorInventario()
    monitor.suscribir(ModuloCompras())
    monitor.suscribir(ModuloAlertas())
    await monitor.iniciar()


if __name__ == "__main__":
    asyncio.run(main())