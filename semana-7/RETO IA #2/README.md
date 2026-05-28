## Decisiones de diseño — Entendidas antes de codificar

### Análisis de Multiplexación
*   **Composición sobre Herencia:** Se decidió que `ClienteSSEMultiplex` contenga un `EventRouter` en lugar de heredar de él. Esto permite cambiar el ruteador (ej. por uno asíncrono) sin afectar la lógica de conexión.
*   **Manejo de Errores en Handlers:** Se implementó un bloque `try/except` dentro del despachador del Router. 
    *   *Justificación:* Un error en la lógica de negocio (ej. un cálculo mal hecho en precios) no debe "matar" el hilo de red. El cliente debe reportar el error y seguir procesando el stream.
*   **Persistencia (Last-Event-ID):** El cliente rastrea el último ID exitoso. En caso de reconexión, este se envía en los headers para que el servidor de EcoMarket realice el "catch-up" de eventos perdidos.

### Invariantes del Parser
1.  **Líneas vacías:** Indican el fin de un bloque. Solo ahí se dispara `_procesar_evento`.
2.  **Comentarios (`:`):** Se descartan inmediatamente; sirven para mantener el socket abierto (keep-alive).
3.  **Valor con `:`:** Se usa `split(":", 1)` para asegurar que las URLs o JSONs dentro del campo `data` no se rompan.