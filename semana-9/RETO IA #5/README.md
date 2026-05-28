##1. Diagrama de Estados del Ciclo de Vida del Cliente

El cliente HTTP y la interfaz de usuario transicionan a través de 4 estados para gestionar de manera segura la vigencia de los tokens JWT del backend.

```text
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