# ==============================================================================
# CLIENTE HTTP E INTERCEPTOR DE AUTENTICACIÓN
# ==============================================================================

class MockResponse:
    """Clase auxiliar para simular las respuestas HTTP del servidor de EcoMarket."""
    def __init__(self, status_code: int, json_data: dict):
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> dict:
        return self._json_data


def mock_api_server(url: str, headers: dict) -> MockResponse:
    """
    Simulador de Backend (EcoMarket API).
    Decisión de Diseño: Validar el token simulando el comportamiento real del servidor.
    - Si el token contiene 'nuevo_exp', el backend responde con éxito (200).
    - Si el token es el antiguo/expirado, el backend devuelve un error de autorización (401).
    """
    auth_header = headers.get("Authorization", "")
    
    # Simulación de endpoint de precios
    if url == "/api/ecomarket/precios":
        # Si el token es el nuevo (el que generó nuestro refresh con éxito)
        if "nuevo_exp" in auth_header:
            return MockResponse(200, {"status": "success", "data": {"manzanas": 25.0, "aguacate": 60.0}})
        else:
            # Si es el token viejo de Ana o no hay token, el servidor lo rebota
            return MockResponse(401, {"error": "Unauthorized", "message": "El token ha expirado o es inválido."})
            
    return MockResponse(404, {"error": "Not Found"})


def auth_request(url: str, method: str = "GET", data: dict = None) -> MockResponse:
    """
    Interceptor HTTP Global del Cliente.
    
    Decisión de Diseño (Mecanismo de Reintento Único y Recuperación):
    Por qué: Un cliente robusto no debe rendirse al primer 401. Intenta inyectar el token actual.
    Si el servidor responde 401, el interceptor detiene el flujo de la petición, solicita un nuevo token
    al TokenManager (aprovechando que si hay 10 peticiones en paralelo, el singleton las encolará),
    actualiza los headers y reintenta la petición EXACTAMENTE una vez. 
    Si el segundo intento o el mismo método refresh vuelven a fallar con 401, se destruye la sesión 
    por completo llamando a logout() para proteger el sistema de bucles infinitos de peticiones.
    """
    manager = TokenManager()
    
    # 1. Preparar headers base e inyectar automáticamente el token actual si existe
    headers = {"Content-Type": "application/json"}
    headers.update(manager.get_auth_header())
    
    print(f"\n[HTTP Client] Enviando {method} a {url}...")
    # Primer intento de llamada al servidor externo
    response = mock_api_server(url, headers)
    
    # 2. Detectar si el servidor rechaza el token (HTTP 401 Unauthorized)
    if response.status_code == 401:
        print(f"[HTTP Client] ¡Primer intento fallido (401 Unauthorized)! Detectado token vencido en la petición.")
        
        try:
            print(f"[HTTP Client] Solicitando renovación automática al TokenManager...")
            # Llamamos al método concurrente seguro del Singleton
            nuevo_token = manager.refresh_access_token()
            
            # 3. Si el refresh fue exitoso, reconstruimos los headers con el nuevo token
            print(f"[HTTP Client] Reintentando petición original con el nuevo token...")
            headers.update(manager.get_auth_header())
            
            # Segundo intento (Reintento único)
            response = mock_api_server(url, headers)
            
            # Si el reintento vuelve a fallar con 401, significa que el nuevo token también es inválido
            if response.status_code == 401:
                print("[HTTP Client] ¡Error crítico! El token refrescado también fue rechazado (401).")
                manager.logout()
                raise Exception("Sesión inválida de forma permanente. Forzando cierre de sesión.")
                
        except Exception as e:
            # Manejo del caso crítico: "La petición de refresh también falla o devuelve 401"
            print(f"[HTTP Client] Excepción en flujo de autenticación: {e}")
            print("[HTTP Client] Traslado al estado: NO_AUTENTICADO. Abortando petición.")
            manager.logout()
            return MockResponse(401, {"error": "Authentication Failed", "message": "No se pudo recuperar la sesión."})

    return response