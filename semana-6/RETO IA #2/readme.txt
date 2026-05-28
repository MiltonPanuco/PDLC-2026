# EcoMarket - Monitor de Alertas SSE

Sistema de monitoreo de inventario basado en **Server-Sent Events**.

## Traza de Red (Escenario EcoMarket)
1. **t=0**: Cliente abre conexión `GET /api/alertas` (Header `Accept: text/event-stream`).
2. **t=2**: Recibe `id: 1`, evento `precio-actualizado`. Actualiza UI local.
3. **t=8**: Recibe `id: 2`, evento `stock-critico`. Dispara alerta visual.
4. **t=15**: Recibe `: ping`. Mantiene el socket activo sin procesar datos.
5. **t=25**: **Falla de Red**. El cliente detecta el cierre del socket.
6. **t=28**: El cliente reconecta enviando `Last-Event-ID: 2`. El servidor retoma desde el evento 3.

## Ejecución
1. Instalar dependencias: `pip install httpx`
2. Correr el monitor: `python receptor_alertas.py`

## Ventaja sobre Polling
SSE reduce el overhead de red al eliminar las peticiones constantes "vacías". Solo se transmiten datos cuando ocurre un cambio real en el inventario.