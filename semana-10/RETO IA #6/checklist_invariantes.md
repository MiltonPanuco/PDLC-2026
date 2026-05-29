INV-A1
Descripción: El CircuitBreaker nunca accede a campos del payload JWT (sub, exp, rol, etc.).

Prueba: Pasamos al método ejecutar() una función con un token corrupto como "no.es.jwt".

Estado: Pasa

Evidencia Observable: El circuito operó con normalidad controlando los estados de red. El breaker no lanzó ningún error de decodificación Base64 ni JSON. Pasó el Paso 1 del Script HG.

INV-A2
Descripción: En estado SEMIABIERTO, exactamente una petición pasa al servidor; las demás reciben CircuitOpenError inmediato.

Prueba: Mandamos 3 peticiones simuladas al mismo tiempo usando asyncio.gather() cuando el circuito cambió a SEMIABIERTO.

Estado: Pasa

Evidencia Observable: En la consola del servidor mock solo se registró la llegada de la Petición #9. En el cliente, las otras dos peticiones paralelas saltaron de inmediato con la excepción CircuitOpenError sin tocar la red.

INV-A3
Descripción: Al transicionar SEMIABIERTO → CERRADO, el contador _fallos_consecutivos se pone en 0.

Prueba: Forzamos la caída del servidor hasta abrir el circuito (5 fallas), esperamos los 3 segundos de aislamiento, mandamos una petición exitosa (200) y revisamos el valor interno de cb._fallos.

Estado: Pasa

Evidencia Observable: Tras la respuesta exitosa, la consola imprimió cb._fallos = 0. Al tirar el servidor inmediatamente después, el breaker necesitó de nuevo otras 3 fallas consecutivas para abrirse, demostrando que la memoria se limpió por completo.

INV-A4
Descripción: Un error HTTP 401 o 403 no incrementa _fallos_consecutivos.

Prueba: Mandamos 5 peticiones seguidas que regresaron un estado 401 Unauthorized.

Estado: Pasa

Evidencia Observable: El log imprimió la advertencia del error de permisos, pero el estado del circuito se mantuvo en CERRADO y el contador de fallas se quedó estático en 0.

INV-B1
Descripción: El TokenManager no tiene ningún atributo relacionado con el estado del Circuit Breaker.

Prueba: Corrimos el comando hasattr(tm, '_estado') e inspeccionamos las variables del manager buscando palabras como 'circuit' o 'breaker'.

Estado: Pasa

Evidencia Observable: La prueba arrojó False. No existe acoplamiento de variables. Pasó el Paso 2 del Script HG.

INV-B2
Descripción: El token de acceso nunca aparece en los logs, ni parcialmente, ni truncado con [:N].

Prueba: Tiramos el servidor para forzar errores y usamos un comando grep en la terminal para buscar la palabra 'Bearer' o caracteres del token dentro del archivo de logs generado.

Estado: Pasa

Evidencia Observable: El archivo demo_resiliencia.log solo registró mensajes planos indicando excepciones físicas de red o códigos HTTP de error, sin exponer ninguna cadena criptográfica de las credenciales.

INV-B3
Descripción: Con múltiples peticiones concurrentes expiradas, solo un refresh se ejecuta (patrón singleton).

Prueba: Ejecutamos 5 peticiones asíncronas paralelas cuando el token de Ana ya estaba vencido.

Estado: Pasa

Evidencia Observable: La consola mostró una sola línea de [TokenManager] Ejecutando renovación segura de sesión (Refresh).... Las otras 4 peticiones se quedaron esperando en cola y usaron ese mismo token renovado para salir a la red.