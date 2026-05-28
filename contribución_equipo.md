# Reporte de Trabajo Individual — Hito 2
**Alumno:** Milton Cruz Pánuco Castillo
**Carrera:** Licenciatura en Sistemas Computacionales

## Organización del Trabajo
Al desarrollar este proyecto de manera individual, me encargué de la integración completa de la pila distribuida lógicas de las semanas 8 y 9:
* **Mecanismo de Resiliencia:** Modificación y limpieza de la máquina de estados del CircuitBreaker para asegurar el correcto conteo de errores y el aislamiento temporal.
* **Mecanismo de Seguridad:** Ajuste del TokenManager, decodificación Base64URL y control de refrescos concurrentes en segundo plano.
* **Integración y Certificación:** Creación de la clase ClienteRobusto para conectar ambas piezas y desarrollo de los casos de prueba automatizados con pytest.

## Defensa Breve de Aportaciones y Decisiones
El principal reto que tuve que resolver por mi cuenta fue definir cómo tratar los errores de permisos (HTTP 401 y 403) dentro del disyuntor de red. Inicialmente, el código buggy sumaba cualquier error al contador general de fallas, lo que abría el circuito de forma incorrecta.

Analizando las restricciones técnicas del taller (invariante INV-A4), determiné que un error 401 indica que el servidor de EcoMarket está en línea y respondiendo de forma íntegra, solo que nuestras credenciales no son válidas. Si permitía que el Circuit Breaker sumara estos eventos, un token vencido terminaría bloqueando el canal de red para los demás módulos de la app. Por lo tanto, decidí filtrar estos códigos en la clasificación de errores, permitiendo que el sistema intente recuperar la sesión de manera transparente sin alterar el estado de resiliencia de la red.