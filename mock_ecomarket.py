# mock_ecomarket.py
import logging
from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
_contador = 0

async def handle_login(request):
    print("[MOCK BACKEND] -> Petición de inicio de sesión en /auth/login")
    token = ("eyJhbGciOiJIUzI1NiJ9"
             ".eyJzdWIiOiJvcDEiLCJyb2wiOiJ2aWV3ZXIiLCJleHAiOjk5OTk5OTk5OTl9"
             ".mock_sig")
    return web.json_response({"access_token": token, "refresh_token": "mock.refresh"})

async def handle_inventario(request):
    global _contador
    _contador += 1
    
    # Sincronización con la Secuencia 1 (Peticiones con refresco controlado)
    if _contador in (1, 3, 5):
        print(f"\n[MOCK BACKEND] -> Recibida Petición #{_contador} | Retornando 401")
        return web.Response(status=401, text="Unauthorized - Token Expired")
    
    if _contador in (2, 4, 6):
        print(f"[MOCK BACKEND] -> Recibida Petición #{_contador} con token renovado | Estado: 200 OK")
        return web.json_response({"productos": _contador * 10, "status": "success"})
    
    # Sincronización con la Secuencia 2 (Inyección de caídas 503)
    if _contador in (7, 8, 9):
        print(f"\n[MOCK BACKEND] -> Recibida Petición #{_contador} | Simulando CAÍDA CRÍTICA (503)")
        return web.Response(status=503, text="Service Unavailable")
    
    # Sincronización con la Secuencia 4 (Canary exitoso)
    print(f"\n[MOCK BACKEND] -> Recibida Petición #{_contador} | ¡SERVIDOR ALIVIADO! (200 OK)")
    return web.json_response({"productos": 150, "recuperado": True, "status": "success"})

app = web.Application()
app.router.add_post('/auth/login',     handle_login)
app.router.add_get ('/api/inventario', handle_inventario)

if __name__ == '__main__':
    print("==================================================================")
    print("[MOCK] Servidor EcoMarket corriendo en http://localhost:8080")
    print("[MOCK] Flujo optimizado para el paso simultáneo de la suite")
    print("==================================================================")
    web.run_app(app, port=8080, print=None)