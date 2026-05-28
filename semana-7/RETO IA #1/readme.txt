Decisiones de diseño — entendidas antes de codificar
1. El Límite de las "Puertas de Embarque" (Navegador)
Pregunta: Si abro 3 objetos EventSource hacia el mismo origen (límite de 6), ¿cuántas quedan libres para fetch()?

Respuesta: Quedan 3 conexiones libres.

Riesgo Técnico: Si el usuario abre 6 pestañas de la app, agotará todas las conexiones permitidas por el navegador hacia nuestro servidor. Cualquier intento posterior de hacer un fetch() (como el de renovación de token cada hora) se quedará en estado "Pending" indefinidamente, bloqueando la funcionalidad de la app. El navegador no "cola" estas peticiones de forma eficiente si el socket SSE nunca se cierra.

2. Python vs. Navegador: El Auto vs. El Autobús
Pregunta: ¿Tiene Python (requests/httpx) el mismo límite de 6 conexiones?

Respuesta: No. El límite de 6 es una regla impuesta por los navegadores (estándar HTTP/1.1) para evitar abusos.

Limitación en Python: En Python, el límite es el hardware y el sistema operativo (File Descriptors) y, sobre todo, la capacidad del servidor de EcoMarket para mantener sockets abiertos. Mientras que el navegador te protege de saturar al server, un script de Python mal programado puede tumbar el backend por exceso de conexiones.

3. Eventos sin Handler: El Paquete sin Dueño
Pregunta: ¿Qué debe hacer el cliente si recibe un evento precio-actualizado pero no tiene un manejador registrado?

Respuesta: Debe ignorarlo silenciosamente (quizás con un log de advertencia).

Justificación: SSE es un protocolo de "empuje". El servidor evoluciona más rápido que el cliente. Si lanzamos una excepción por cada evento desconocido, la app de EcoMarket se rompería cada vez que el equipo de Backend añada una nueva funcionalidad. El cliente solo debe reaccionar a lo que sabe procesar.

4. Multiplexación y Parámetros de URL
Pregunta: ¿Puedo añadir un módulo (ej. "devoluciones") a una conexión activa mediante parámetros de URL sin reconectar?

Respuesta: No.

Justificación: Los parámetros de URL (GET /api/alertas?modulo=devoluciones) se envían durante el handshake HTTP. Una vez que el túnel está abierto y los datos fluyen, la petición inicial ya terminó su fase de cabeceras. Para cambiar los módulos activos, es necesario cerrar la conexión actual e iniciar una nueva con la URL actualizada.