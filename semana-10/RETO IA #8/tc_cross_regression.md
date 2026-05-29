## Análisis de Escenarios Complejos Operando Simultáneamente

Este documento detalla los resultados de las pruebas cruzadas donde interactúan los tres componentes principales del sistema al mismo tiempo: la comunicación en tiempo real (SSE), la seguridad (JWT) y la resiliencia (Circuit Breaker).

---

### TC-X1 — Stream SSE Activo + Circuit Breaker en Estado ABIERTO

* **Setup (Configuración):** Levantamos el ClienteSSEMultiplex y abrimos una conexión de datos continua contra el servidor mock en la ruta de alertas. Comprobamos en la consola que los eventos en segundo plano están llegando bien y se están despachando por el EventRouter de forma normal.

* **Acción (Ejecución):** Mientras el flujo de alertas de SSE sigue recibiendo datos, usamos el ClienteRobusto para hacer 5 peticiones HTTP seguidas a la ruta de inventario, configurando el servidor mock en modo de falla (HTTP 503) para forzar al CircuitBreaker a cambiar al estado ABIERTO.

* **Verificación (Medición):** Revisamos la pantalla para medir dos cosas de forma paralela: (a) que las llamadas HTTP comunes del ClienteRobusto reboten de inmediato con el error de circuito abierto, y (b) que los mensajes de texto del stream de SSE sigan entrando y mostrándose en la consola sin interrupciones.

* **Resultado Documentado:** **PASA.** La apertura del Circuit Breaker en las rutas HTTP de datos no interrumpió para nada el canal de alertas en tiempo real. Esto pasa porque SSE corre en una conexión persistente totalmente separada de las peticiones tradicionales, demostrando que un apagón en la API común no tira los flujos que ya están conectados por debajo.

---

### TC-X2 — Token Expirado mientras el Circuit Breaker está en SEMIABIERTO

* **Setup (Configuración):** Dejamos el CircuitBreaker en estado ABIERTO y simulamos que ya pasó el tiempo de espera de recuperación para que la siguiente llamada cambie el estado a SEMIABIERTO. Al mismo tiempo, alteramos el TokenManager de forma local para que indique que el token actual ya caducó (is_expiring_soon regresa True).

* **Acción (Ejecución):** Mandamos una sola petición asíncrona para consultar el inventario usando el ClienteRobusto.

* **Verificación (Medición):** Revisamos el orden en que se imprimen los mensajes en la consola. El script debe congelar la llamada de red, mandar a pedir un token nuevo mediante el método refresh_access_token del TokenManager y, una vez que tiene las credenciales listas, cambiar el breaker a SEMIABIERTO para soltar la petición de prueba hacia el servidor mock.

* **Resultado Documentado:** **PASA.** El ClienteRobusto resolvió primero la actualización de los accesos locales y después consumió la única petición de prueba que permite el breaker en estado SEMIABIERTO. Si se hubiera hecho al revés, la petición de prueba habría salido a la red con el token viejo de Ana, fallando con un error 401 y haciendo que el circuito se abriera otra vez por error de permisos en lugar de un error de red.

---

### TC-X3 — Reconexión de SSE con Last-Event-ID tras Cierre del Circuito

* **Setup (Configuración):** Conectamos el stream de SSE de forma normal y guardamos en la memoria local del ReceptorAlertas que el último mensaje procesado de forma exitosa tenía el identificador único 742. Después, simulamos un apagón total tirando el servidor: esto hace que el canal de SSE se desconecte y que las llamadas HTTP fallen hasta abrir el Circuit Breaker.

* **Acción (Ejecución):** Regresamos el servidor mock a su estado normal. Esperamos a que pase el tiempo de aislamiento del breaker y mandamos una petición HTTP exitosa para que el circuito regrese al estado CERRADO, lo que activa en automático el intento de reconexión del flujo de alertas.

* **Verificación (Medición):** Atrapamos los datos de la petición de reconexión que el ReceptorAlertas manda hacia el backend para revisar sus encabezados.

* **Resultado Documentado:** **PASA.** La solicitud de reconexión incluyó de forma correcta el encabezado Last-Event-ID con el valor 742 para pedirle al servidor los mensajes que nos perdimos mientras todo estaba caído. Además, se comprobó que la cabecera Authorization llevó el token actualizado que se generó tras la renovación de la sesión, evitando usar credenciales viejas.