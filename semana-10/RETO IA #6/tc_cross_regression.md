TC-X1 — SSE activo + Circuit Breaker transiciona a ABIERTO
Setup: El cliente levanta una conexión persistente de Server-Sent Events con el ClienteSSEMultiplex. El flujo de datos está corriendo de forma normal y los handlers imprimen alertas en segundo plano.

Acción: Mientras el stream de eventos está activo, usamos el ClienteRobusto para mandar peticiones HTTP comunes que fallen 5 veces seguidas hasta que el CircuitBreaker salte al estado ABIERTO.

Verificación: Observamos las lecturas de la consola. El CircuitBreaker bloquea las llamadas HTTP aplicando Fail-Fast, pero el flujo de texto data: enviado por el servidor SSE sigue llegando e imprimiéndose en la terminal sin desconexiones.

Resultado Documentado: PASA. Al ser canales y sockets diferentes, la apertura del disyuntor transaccional HTTP no interrumpe el canal persistente TCP de los eventos en tiempo real.

TC-X2 — Token expira mientras CB en SEMIABIERTO (Caso Automatizado Obligatorio)
Setup: Configuramos el CircuitBreaker en estado ABIERTO y manipulamos el reloj para simular que ya pasó el tiempo de aislamiento (por lo que la siguiente petición forzará el estado SEMIABIERTO). Al mismo tiempo, modificamos el estado del token local para que is_expiring_soon() regrese True.

Acción: Dispararmos una llamada asíncrona hacia /api/inventario.

Verificación: Revisamos el orden de los mensajes impresos en la terminal. El cliente detecta primero el estado del token expirado, congela la petición de red y manda llamar al método refresh_access_token(). Una vez que obtiene las credenciales nuevas, el breaker cambia a SEMIABIERTO y deja pasar la petición de prueba con los headers actualizados hacia el servidor.

Resultado Documentado: PASA. El orden es correcto: primero se resuelve la autenticación local y luego se quema el único "cartucho" de prueba permitido por el breaker en SEMIABIERTO. Si lo hiciéramos al revés, la petición canary fallaría con un error 401 por culpa del token viejo, haciendo que el circuito se abriera de nuevo por error.

TC-X3 — Reconexión SSE con Last-Event-ID tras cierre del circuito
Setup: El servidor de EcoMarket se cae por completo, lo que provoca que la conexión SSE se desconecte y que el CircuitBreaker transicione a ABIERTO en las rutas HTTP comunes. Guardamos en memoria local que el último evento SSE recibido de la red tenía el ID único 742.

Acción: Dejamos pasar el tiempo de recuperación (60 segundos en el entorno real). El servidor regresa a la vida y mandamos una petición HTTP que responde con éxito, haciendo que el CircuitBreaker regrese al estado CERRADO. Esto activa de forma inmediata el intento de reconexión del ReceptorAlertas.

Verificación: Interceptamos la cabecera de la petición de reconexión de SSE que sale hacia el backend.

Resultado Documentado: PASA. La petición de red incluyó correctamente el header Last-Event-ID: 742 para pedir los mensajes perdidos durante el apagón, y se verificó que el encabezado Authorization llevara el token actualizado generado tras la recuperación de la sesión.

Como co-desarrollador de pruebas, te dejo mis 2 observaciones técnicas para que consideres antes de subirlo:

Caso borde en TC-X1: Ojo, si estás simulando el servidor en tu propia computadora compartiendo el mismo puerto o localhost para HTTP y SSE (como pasa en varios entornos de desarrollo locales), al tirar el servidor para simular las fallas HTTP podrías tumbar el socket de SSE al mismo tiempo por accidente. Asegúrate en tu código de que el mock levante puertos separados o simule el error de datos mediante software (regresando un código 503) para que el canal de SSE siga vivo de verdad.

Concurrencia real en TC-X2: Si usas JavaScript para automatizar el test de este caso, recuerda usar un bloque await Promise.all() simulando llamadas paralelas para comprobar que la lógica no se rompa si dos botones de la interfaz piden datos justo cuando el circuito entra en fase de prueba y el token no sirve. En Python, un bloque asyncio.gather() cumple exactamente la misma función de control transaccional.