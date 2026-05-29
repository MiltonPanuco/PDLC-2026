Prompt usado: "Actúa como comité de revisión arquitectónica. Analiza mi decisión de excluir las rutas de autenticación del Circuit Breaker. Evaluaremos el escenario en Black Friday con alta concurrencia de reintentos."

Respuesta relevante resumida: La IA me dijo que aunque es buena idea para no trabar la app, si el servidor de usuarios se llena en un día de muchas ventas (como Black Friday), nuestros propios usuarios podrían tumbar el sistema sin querer al intentar conectar todos al mismo tiempo. Me recomendó que en vez de bloquearlos, les ponga un temporizador para que los reintentos vayan tardando más tiempo cada vez.

Decisión aceptada o rechazada: Acepté el riesgo de que los usuarios saturen el sistema, pero rechacé la idea de juntar todo en el mismo apagador.

Justificación técnica: Juntar todo rompe las reglas del taller (el breaker no debe saber nada de tokens). Lo que haré para solucionar lo que me dijo la IA es dejar esto así por ahora, y para la siguiente semana programar en el TokenManager que los reintentos no sean tan seguidos, dándole un respiro al servidor.


= MI ADR =

Título
Dejar el botón de reingreso (Login y Refresh) fuera del apagador automático (Circuit Breaker)

1. Contexto (máx. 2 oraciones)
Si el servidor de la escuela o de la app empieza a fallar y a ponerse lento, el Circuit Breaker "apaga" las peticiones automáticas para no tumbar por completo el sistema. Si metemos el proceso de iniciar sesión o renovar el token dentro de este mismo apagador, cuando el circuito se abra nos va a bloquear también el inicio de sesión, y la app se va a quedar congelada sin poder intentar conectar de nuevo aunque el servidor ya haya revivido.

2. Decisión (1 oración)
Decidimos dejar la renovación del token (/auth/refresh) por fuera del Circuit Breaker para que la app siempre pueda intentar iniciar sesión, sin importar si el canal de datos está bloqueado o no.

3. Consecuencias positivas (exactamente 2)
Evitamos que la app se quede en un callejón sin salida (un torbellino donde no puedes pedir datos porque no tienes token, y no puedes pedir un token porque el sistema está bloqueado).

El código del Circuit Breaker queda mucho más limpio y fácil de entender, porque solo se encarga de ver si el internet o el servidor se cayeron, no de si el usuario inició sesión o no.

4. Consecuencias negativas (exactamente 2)
Si el servidor se cae justamente en la parte del inicio de sesión, la app va a seguir mandando peticiones de refresh a lo loco sin que nadie las frene.

No vamos a poder saber si el servidor de inicio de sesión está fallando usando las métricas del breaker, porque este solo vigila las rutas comunes (como la lista de productos).

5. Escenario adverso — ¿cuándo fallaría esta decisión?
Esto saldría mal si el servidor fuera un código viejito donde todo está guardado en la misma computadora. Si esa computadora se traba por falta de memoria, el hecho de que nuestra app le siga mandando solicitudes de inicio de sesión una y otra vez haría que se sature todavía más, impidiendo que el servidor pueda reiniciarse o recuperarse porque lo estamos bombardeando sin piedad.