# Reporte de Autopsia: Diagnóstico de Defectos Deliberados
**Proyecto:** Cliente Robusto - Auditoría Interna TechNova
**Curso:** Programación Distribuida del Lado del Cliente

---

## Análisis de Defectos y Plan de Mitigación

### SECCIÓN 1: BUG A — Interferencia de Roles en la Capa de Resiliencia

* **Síntoma:** Los operadores con rol 'viewer' reciben un PermissionError de forma inesperada al intentar consultar el inventario, a pesar de que es una operación legítima de lectura (GET).
* **Causa Raíz:** La clase CircuitBreaker está asumiendo responsabilidades de autorización que no le corresponden. El breaker intercepta la petición, decodifica manualmente el JWT a nivel de bytes, extrae el payload y valida los roles contra una lista blanca fija donde falta el perfil 'viewer'. Esto acopla la tolerancia a fallos con las reglas de negocio de accesos.
* **Línea Exacta:** Bloque de las líneas 19 a 27 en `cliente_robusto_con_bugs.py`:
    ```python
    if token_manager:
        token = token_manager.get_access_token()
        pad = 4 - len(token.split('.')[1]) % 4
        payload = json.loads(
            base64.urlsafe_b64decode(token.split('.')[1] + '=' * pad)
        )
        if payload.get('rol') not in ('admin', 'supervisor'):
            raise PermissionError(f"Rol '{payload['rol']}' no autorizado")
    ```
* **Corrección:** Hay que eliminar por completo el parámetro `token_manager` y todo su bloque condicional dentro del método `ejecutar()` del breaker. La validación de roles debe delegarse exclusivamente al backend o a un middleware de rutas en el cliente.
    ```python
    def ejecutar(self, fn):
        # Se elimina el bloque condicional del token_manager por completo
        if self.estado == EstadoCircuito.ABIERTO:
            if time.time() - self._tiempo_apertura >= self._timeout:
                self.estado = EstadoCircuito.SEMIABIERTO
            else:
                raise Exception("CircuitOpenError")
        try:
            resultado = fn()
            self._on_exito()
            return resultado
        except Exception as e:
            self._on_fallo(e)
            raise
    ```
* **Principio Violado:** * **SRP (Principio de Responsabilidad Única):** El breaker solo debe cambiar si se modifica la lógica de resiliencia ante caídas de red, no por políticas de usuarios.
    * **Invariante INV-A1:** El CircuitBreaker debe mantenerse 100% agnóstico a la estructura interna o campos del payload del token (JWT).

---

### SECCIÓN 2: BUG B — Exposición de Credenciales en Logs

* **Síntoma:** En los logs de diagnóstico de producción se están registrando fragmentos del token de acceso activo de los usuarios (los primeros 40 caracteres).
* **Causa Raíz:** En la captura de excepciones (`except Exception`) del método `get_inventario` en `ClienteRobusto`, se metió una instrucción de logueo errónea que concatena el string criptográfico `headers['Authorization'][:40]` para "facilitar" el rastreo de fallos. Esto rompe la confidencialidad en producción.
* **Línea Exacta:** Líneas 64 a 66 en `cliente_robusto_con_bugs.py`:
    ```python
    logger.error(
        f"Error: {e}. Auth: {headers['Authorization'][:40]}..."
    )
    ```
* **Corrección:** Sanitizar el bloque interceptor eliminando la interpolación de los encabezados de autorización. Solo se debe registrar la descripción de la falla o el código HTTP correspondiente.
    ```python
    except Exception as e:
        logger.error(f"Fallo en la consulta de inventario: {e}")
        raise
    ```
* **Principio Violado:** * **Invariante INV-B2:** Las credenciales o materiales de seguridad de sesión jamás deben ser volcados en cadenas de diagnóstico ni escritos en logs, ni siquiera de forma parcial o truncada.
    * **Seguridad por Diseño (Security by Design):** Los datos sensibles de sesión deben estar estrictamente aislados del ciclo de auditorías operacionales ordinarias.

---

### SECCIÓN 3: BUG C — Estado Corrupto en el Contador de Fallos

* **Síntoma:** Después de que el servidor remoto se recupera de una caída y el circuito cierra de nuevo, el breaker vuelve a saltar a ABIERTO instantáneamente al recibir un solo error posterior, ignorando por completo el umbral de tolerancia configurado.
* **Causa Raíz:** El método transicional `_on_exito()` actualiza correctamente la etiqueta a `EstadoCircuito.CERRADO`, pero olvida resetear el contador interno de errores transitorios. El atributo `self._fallos` conserva el número acumulado durante la crisis anterior, corrompiendo la estabilidad de la máquina de estados.
* **Línea Exacta:** Líneas 42 a 45 en `cliente_robusto_con_bugs.py`:
    ```python
    def _on_exito(self):
        # ─────────────────────────────────────── BUG C (síntoma C)
        self.estado = EstadoCircuito.CERRADO
        # ────────────────────────────────────────────────────────────
    ```
* **Corrección:** Incorporar explícitamente el reinicio de la variable `self._fallos` a cero dentro de la función de éxito para blanquear el historial.
    ```python
    def _on_exito(self):
        self.estado = EstadoCircuito.CERRADO
        self._fallos = 0  # Restablece la ventana limpia de tolerancia del circuito
    ```
* **Principio Violado:** * **Invariante INV-A3:** Al transicionar al estado operativo base (`CERRADO`), es mandatorio limpiar todas las métricas de error acumuladas para garantizar que el comportamiento del circuito vuelva a ser predecible frente a futuras fluctuaciones.