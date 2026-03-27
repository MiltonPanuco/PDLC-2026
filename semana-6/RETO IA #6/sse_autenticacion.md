1. ¿Podemos mandar el Token en los Headers?Respuesta corta: No (con el EventSource normal).La herramienta que trae
el navegador por defecto (EventSource) es muy básica. No te deja poner el típico header de Authorization: Bearer XXX.
Es como una radio vieja: o sintonizas la frecuencia que es abierta o usas "cookies" (que el navegador manda solas).
Si tu token está en localStorage, el EventSource no sabe cómo agarrarlo.

2. ¿Cómo resolvemos esto en EcoMarket? (4 Caminos)Opción¿Cómo le hace?Lo Bueno 👍Lo Malo 👎Por la URL/api/alertas?token=abcSuper
fácil, funciona con todo.El token sale en el historial y en los logs del server (Inseguro).Con CookiesEl server guarda el token 
en una cookie.El navegador la manda solita y es muy seguro.Un relajo si el Backend y el Frontend están en servidores distintos.
Ticket de 1 usoPides un "pase" rápido y luego te conectas.Es el estándar de oro. El token real nunca viaja por la URL.Tienes que
hacer dos llamadas al servidor en lugar de una.Librería ExtraUsas código de alguien más (Polyfill).Puedes usar Headers como siempre.
Tienes que instalar más cosas en tu proyecto.

3. El Plan de Acción (Pseudocódigo en Python)Si el token se vence mientras el repartidor de EcoMarket está en camino, el código
debe ser capaz de "despertar", pedir un pase nuevo y seguir escuchando.Pythonasync def conectar_con_permiso(url, gestor_auth):

    # 1. Agarramos el token que tengamos

    mi_token = await gestor_auth.dame_token()
    
    while True:
        try:
            # Intentamos entrar a la fiesta de datos
            headers = {"Authorization": f"Bearer {mi_token}"}
            async with httpx.AsyncClient(timeout=None) as cliente:
                async with cliente.stream("GET", url, headers=headers) as respuesta:
                    
                    # 2. Si el guardia (server) nos saca porque el token ya no sirve
                    if respuesta.status_code == 401:
                        print("🔑 El token ya caducó. Pidiendo uno nuevo...")
                        mi_token = await gestor_auth.actualizar_token()
                        continue # Volvemos a intentar la conexión
                    
                    # 3. Escuchamos las alertas
                    async for linea in respuesta.aiter_lines():
                        print(f"📡 Alerta recibida: {linea}")

        except:
            print("🔌 Se cortó el internet. Reintentando en un momento...")
            await asyncio.sleep(5)


4. La "Trampa" de las conexiones largasHay algo que debes saber: El servidor solo revisa tu identidad al principio. En una 
página normal, el servidor te pide tu ID cada vez que das click. En SSE, como la conexión se queda "abierta" por horas, si
el jefe de EcoMarket te banea a los 5 minutos de haberte conectado, tú vas a seguir recibiendo alertas porque el servidor ya
te dejó pasar y no vuelve a preguntar.Lección: Si queremos que el sistema sea seguro de verdad, el servidor debe tener un botón
de "Cerrar todo" para sacar a la fuerza a los usuarios que ya no tengan permiso, porque el cliente no va a colgar por su cuenta.