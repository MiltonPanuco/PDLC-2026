# Reporte de Auditoría Técnica: Protocolo SSE EcoMarket

## 1. Resumen de Invariantes Violados
En la versión inicial del cliente, se detectaron fallos críticos que rompen la robustez del sistema en producción. Un cliente SSE robusto **nunca** debe cerrar la conexión por falta de datos, ni procesar mensajes incompletos.

---

## 2. Hallazgos de la Auditoría

### Error 1: Timeout de Lectura Agresivo
*   **Ubicación:** Configuración del `AsyncClient(timeout=30.0)`.
*   **Fallo en producción:** El cliente asume que si no hay datos en 30s, la red murió. En EcoMarket, si no hay ventas en 1 hora, el cliente se desconectará y reconectará 120 veces innecesariamente.
*   **Corrección:** Establecer `timeout=None`.

### Error 2: Procesamiento de Data Fragmentada
*   **Ubicación:** Método `_procesar_linea` disparando el dispatch inmediatamente.
*   **Fallo en producción:** Si un JSON es muy largo y viaja en dos líneas de `data:`, el parser de JSON truena al recibir la primera mitad. Se pierden alertas críticas de stock.
*   **Corrección:** Implementar un acumulador (buffer) que solo dispare el evento al detectar la línea vacía (`\n\n`).

### Error 3: Contaminación de Tipos de Evento
*   **Ubicación:** Variable de estado `self.current_event` global a la clase.
*   **Fallo en producción:** Si recibimos un evento `stock-critico` y el siguiente mensaje es un mensaje simple (sin tipo), el cliente le asigna el tipo anterior por error.
*   **Corrección:** Resetear la variable de tipo de evento después de cada bloque procesado.

### Error 4: Tormenta de Reconexión (DDoS Involuntario)
*   **Ubicación:** Bloque `except` con `asyncio.sleep(3)` fijo.
*   **Fallo en producción:** Si el servidor cae, miles de clientes intentando entrar cada 3 segundos exactos saturan el ancho de banda e impiden el reinicio del servidor.
*   **Corrección:** Implementar **Backoff Exponencial** (2, 4, 8, 16... segundos).

---

## 3. Evidencia de Ejecución (Logs de Terminal)

```text
[FALLO DETECTADO - ERROR 2]:
DEBUG: data: {"id": "A01", "nombre": "Quinoa",
DEBUG: data: "precio": 45.50}
ERROR: ValueError: El mensaje no es un JSON válido (Mitad recibida).

[FALLO DETECTADO - ERROR 4]:
🔌 Error de conexión. Reintentando en 3s...
🔌 Error de conexión. Reintentando en 3s... (Repetido 50 veces)