# Reporte de Contribución de Equipo — Hito 2
**Materia:** Programación Distribuida del Lado Cliente  
**Integrantes:** * Milton Cruz Pánuco Castillo (Desarrollo Principal)
*                * Mauricio Damián Ramírez Moreno (Soporte de Pruebas)
**Carrera:** Licenciatura en Sistemas Computacionales / Área Economía

---

## ¿Quién hizo qué? (División del Trabajo)

Para este proyecto final, dividimos las tareas de manera que Milton se encargara de toda la programación del código fuerte y la integración, mientras que Mauricio ayudó con las pruebas y el acomodo de archivos:

* **Milton Cruz Pánuco Castillo:**
    * Programó toda la lógica del `CircuitBreaker` (los estados Cerrado, Abierto y Semiabierto).
    * Hizo el código del `TokenManager` para que guarde y actualice los tokens al iniciar sesión.
    * Creó el script principal (`ClienteRobusto`) que junta el control de tokens con el cortocircuito de red.
    * Armó la suite de pruebas automatizadas con `pytest` para comprobar que todo funcione en orden.

* **Mauricio Damián Ramírez Moreno:**
    * Ayudó a rellenar las rutas y respuestas del servidor simulado (`mock_ecomarket.py`).
    * Configuro las líneas para que el archivo `demo_resiliencia.log` se guarde de forma correcta en la carpeta raíz.
    * Revisó y acomodó los archivos README viejos en sus respectivas carpetas por semanas.

---

## Defensa de Decisiones (Pregunta del Profe)

El problema más importante que resolvimos fue decidir qué hacer cuando el servidor nos regresa un error **HTTP 401 (No autorizado)**. 

Al principio, el código sumaba cualquier error al contador del disyuntor, lo que hacía que el circuito se abriera de forma incorrecta por culpa de un token vencido.

Milton analizó las reglas del taller (Invariante **INV-A4**) y determinó que un error 401 no significa que el servidor esté caído, sino que la sesión caducó. Si dejábamos que el Circuit Breaker contara esto como una falla de red, le apagaríamos el sistema a toda la aplicación de manera injustificada.

Por lo tanto, decidimos que el `ClienteRobusto` atrape el error 401, mande a pedir un token nuevo para actualizar la sesión en segundo plano, y que el `CircuitBreaker` ignore por completo este fallo. Así la aplicación se recupera sola sin trabar la pantalla del usuario.