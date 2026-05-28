## 1. Diagrama de Estados del Ciclo de Vida del Cliente

El cliente HTTP y la interfaz de usuario transicionan de forma síncrona a través de 4 estados para gestionar la vigencia del token JWT enviado por el backend.

       +-------------------------------------------------------+
       |                                                       |
       |                   [ 1. NO_AUTENTICADO ] <---------+   |
       |                             |                     |   |
       |                 (E1: LOGIN_EXITOSO)               |   |
       |                             |                     |   |
       |                             v                     |   |
       |                    [ 2. AUTENTICADO ]             |   |
       |                        /          \               |   |
       |     (E2: COMPROBAR_EXP)            (E4: LOGOUT)   |   |
       |                      /              \             |   |
       |                     v                v            |   |
       |         [ 3. ALERTA_EXPIRACION ]    (E5: LIMPIAR) |   |
       |                    |        \             |       |   |
       |         (E4: LOGOUT)         \            |       |   |
       |              |         (E3: TIEMPO_0)     |       |   |
       |              v                 \          v       |   |
       |              +-------------> [ 4. EXPIRADO ]      |   |
       |                                      |            |   |
       |                                 (E6: EXP_FORCE)   |   |
       +--------------------------------------+------------+   |
                                              |                |
                                              +----------------+

## 2.Instrucciones de Ejecución
El código fuente se encuentra completamente unificado y auto-contenido dentro de un único script para facilitar su validación y portabilidad.

## 3. Reporte de Decisiones de Diseño y Auditoría
A continuación se detallan las justificaciones de ingeniería de software implementadas para blindar el sistema ante escenarios de ataque o fallas concurrentes:

Decisión de Aislamiento en decode_payload: Base64URL remueve los caracteres = de relleno. Python requiere estrictamente que la longitud de los bytes decodificables sea múltiplo de 4. Mediante el cálculo aritmético manual del módulo, el sistema reconstruye el padding ausente. Encapsular el proceso bajo un bloque try-except genérico evita ataques de Denegación de Servicio Local (DoS), impidiendo que un token inyectado maliciosamente tire la aplicación al levantar excepciones de parsing no controladas.

Decisión de Concurrencia mediante Gatekeeper Singleton: Si múltiples componentes de la interfaz de usuario ejecutan peticiones HTTP en paralelo al expirar el token, el sistema podría disparar ráfagas de solicitudes de refresco concurrentes. El backend procesaría la primera e invalidaría el token viejo; las llamadas subsiguientes portando ese mismo token revocado provocarían falsos positivos de ataque y cierres de sesión abruptos. Al implementar un threading.Condition con locks atómicos rápidos, el primer hilo toma el liderazgo de la red mientras los demás se encolan con un método .wait(), consumiendo el mismo resultado de forma sincronizada.

Decisión de Limpieza Atómica Total en logout: Un error común en desarrollo es limpiar únicamente la variable de texto del token. Si banderas de control como _is_refreshing se quedan retenidas en estado True debido a una interrupción abrupta de red, la aplicación experimentará un bloqueo permanente (deadlock) cuando un nuevo usuario intente operar en la misma terminal. El método ejecuta una purga integral y explícita de cada variable de control estatal para regresar de manera segura al estado inicial limpio.

