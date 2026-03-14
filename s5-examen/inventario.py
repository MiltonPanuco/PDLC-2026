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
        # TODO: agregar a la lista evitando duplicados
        pass

    def desuscribir(self, obs: Observador) -> None:
        # TODO: quitar de la lista
        pass

    async def _notificar(self, inventario: dict) -> None:
        # TODO: llamar actualizar() en cada observador
        pass

    async def _consultar_inventario(self) -> dict | None:
        # TODO: GET /inventario con headers y manejo de respuestas
        pass

    async def iniciar(self) -> None:
        # TODO: ciclo de polling con backoff
        pass

    def detener(self) -> None:
        # TODO: solo cambiar la bandera
        pass


class ModuloCompras(Observador):
    async def actualizar(self, inventario: dict) -> None:
        # TODO: imprimir productos con status BAJO_MINIMO
        pass


class ModuloAlertas(Observador):
    async def actualizar(self, inventario: dict) -> None:
        # TODO: POST /alertas por cada producto bajo mínimo
        pass

    async def _enviar_alerta(self, producto: dict) -> None:
        # TODO: construir payload y hacer el POST
        pass


async def main():
    monitor = MonitorInventario()
    monitor.suscribir(ModuloCompras())
    monitor.suscribir(ModuloAlertas())
    await monitor.iniciar()


if __name__ == "__main__":
    asyncio.run(main())