# 🚀 Cliente Seguro y Resiliente EcoMarket — (Grand Deploy)

## 📊 Datos del Desarrollador
* **Alumno:** Milton Cruz Pánuco Castillo 
* **Equipo Presentación Final:** Mauricio Damián Ramírez Moreno 
* **Maestro:** Lic. Eligardo Cruz Sánchez
* **Carrera:** Licenciatura en Sistemas Computacionales / Área Economía
* **Materia:** Programación Distribuida del Lado Cliente
* **Institución:** Universidad Autónoma de Nayarit (UAN)

---

## ⚡ El Core del Proyecto
Este repositorio es la consolidación de diez semanas de puro desarrollo. Aquí está el cliente definitivo de EcoMarket, una pieza de software capaz de aguantar servidores caídos, renovar credenciales en tiempo real sin trabar la interfaz y procesar flujos de datos continuos sin despeinarse. 

Todo el sistema está blindado bajo el principio de **Responsabilidad Única (SRP)**: cada módulo hace una sola cosa y la hace excelente.

---

## 🛠️ Reporte de Ingeniería: Decisiones de Diseño y Auditoría

### 📡 1. Tiempo Real (Semanas 6 y 7 — Server-Sent Events)
* **Adiós al Polling Basura:** Cambiamos las peticiones constantes que solo saturan la red por un canal SSE persistente. El cliente se queda escuchando de forma pasiva y el servidor solo manda bytes útiles cuando hay un cambio real en el inventario.
* **Respetando los Límites del Navegador:** Los navegadores solo permiten 6 conexiones HTTP/1.1 abiertas al mismo tiempo. Al meter un `EventRouter`, multiplexamos los datos en un solo canal, dejando slots libres para que la app pueda cargar imágenes o pedir tokens sin quedarse congelada.
* **Composición > Herencia:** El `ClienteSSEMultiplex` contiene al `EventRouter` en lugar de heredar de él. Así, si mañana queremos cambiar a un ruteador asíncrono, no tenemos que romper la lógica que maneja la conexión de red.
* **Aislamiento de Errores Visuales:** Si un botón o gráfica de la UI truena por un mal cálculo de precios, un bloque `try/except` en el despachador lo atrapa. El cliente reporta el fallo pero no mata el hilo de red; la música sigue sonando.
* **Parser Blindado a Nivel de Bytes:** Las líneas vacías disparan la acción. Los comentarios (`:`) se tiran a la basura de inmediato porque solo sirven para keep-alive. Para el campo `data`, usamos estrictamente `split(":", 1)`, asegurando que los JSONs o URLs con dos puntos internos no se rompan al parsear.

### 🔑 2. Capa de Seguridad (Semanas 8 y 9 — Gestión de Tokens JWT)
* **Reconstrucción Automática de Padding:** Base64URL le quita los caracteres `=` al token. Como Python exige que los bytes sean múltiplos de 4, implementamos un parche aritmético manual usando el operador módulo (`4 - len(partes[1]) % 4`). Al atraparlo con control de excepciones, evitamos que un token corrupto inyectado tire la app por un error de parsing.
* **El Candado Antirepeticiones (Singleton de Refresh):** Si 5 componentes de la UI piden datos al mismo tiempo justo cuando el token expira, el sistema no manda 5 peticiones de refresh a lo loco. El primer hilo toma el control de la red y congela a los demás. Cuando el refresh termina, todos comparten el mismo token fresco, evitando que el backend nos bote la sesión por seguridad.
* **Purga Atómica en Logout:** Al salir, no solo borramos el string del token. Limpiamos a fondo todas las variables y banderas de control en memoria para que no se queden retenidas en `True`. Así evitamos bloqueos permanentes (deadlocks) cuando un nuevo usuario intente iniciar sesión en la misma computadora.

### 🔌 3. Resiliencia Extrema (Semanas 9 y 10 — Circuit Breaker)
* **Clasificación de Errores Inteligente:** Un error de credenciales vencidas (HTTP 401 o 403) significa que el servidor está vivo y jalando bien. Por eso, estos errores se filtran y NO inflan el contador de fallas del breaker, evitando que un usuario sin accesos le apague el internet a toda la app (Invariante INV-A4).
* **Reset de Memoria al Recuperar:** En cuanto el circuito está en `SEMIABIERTO` y una petición de prueba pasa con éxito (HTTP 200), el método `_on_exito()` regresa el estado a `CERRADO` y limpia el contador a cero (`_fallos = 0`). El historial se blanquea por completo para aguantar futuros problemas de red (Invariante INV-A3).

---

## 📂 Historial de Desarrollo (Trazabilidad Semanal)

Toda la documentación y los retos individuales que fuimos construyendo semana a semana se mantuvieron intactos en sus subcarpetas para la auditoría del profesor:
* [Avances y Validadores de Cliente — Semana 2]
* [Documentación de Monitoreo SSE — Semana 6]
* [Dilemas de Conexión y Multiplexación — Semana 7 (Retos 1 y 3)]
* [Estrategias de Parser y Flujo SSE — Semana 7 (Reto 2)]
* [Ciclo de Vida y Seguridad del Token — Semana 9]
---

## ⚙️ Requisitos y Setup Rápido
* Python 3.10 o superior
* Paquetes básicos de entorno (Instalar en la raíz del proyecto):
```bash
pip install aiohttp pytest pytest-asyncio