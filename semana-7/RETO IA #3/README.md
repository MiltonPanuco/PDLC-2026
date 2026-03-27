## Decisiones de diseño — Entendidas antes de codificar

A continuación, se sintetizan las respuestas a los dilemas de arquitectura planteados durante el desarrollo:

1.  **Límites de Conexión:** Se entiende que el navegador limita a 6 conexiones por origen. Al multiplexar, evitamos el riesgo de "congelar" la aplicación, dejando slots libres para peticiones de autenticación y carga de recursos.
2.  **Gestión de Silencio vs Muerte:** Se configuró un `timeout=None` para la lectura. En SSE, el silencio es normal; cerrar la conexión prematuramente solo genera carga innecesaria de reconexión tanto en el cliente como en el servidor.
3.  **Filosofía de Errores:** Se adoptó una política de "Aislamiento de Fallos". Si un handler de visualización falla, el motor de red y el resto de los suscriptores deben permanecer operativos.
4.  **Multiplexación Estática:** La imposibilidad de añadir módulos sin reconectar se acepta como un trade-off de simplicidad. Se confía en el header `Last-Event-ID` para cubrir la brecha de datos durante los reinicios de conexión.