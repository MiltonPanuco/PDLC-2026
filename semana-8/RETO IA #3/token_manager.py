import base64
import json
import time
import threading

class TokenManager:
    _instance = None
    _lock = threading.Lock()  # Garantiza la seguridad de hilos al inicializar el Singleton

    def __new__(cls):
        """
        Decisión de Diseño (Pattern): Implementación de Singleton con Double-Checked Locking.
        Por qué: En entornos concurrentes, si dos hilos intentan instanciar el mánager al mismo tiempo,
        podríamos duplicar el estado en memoria. Este patrón garantiza una única instancia global segura.
        """
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(TokenManager, cls).__new__(cls)
                    cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        """Inicializa las variables de estado internas de la instancia única."""
        self._current_token = None
        self._is_refreshing = False
        self._refresh_lock = threading.Lock()  # Lock específico para la operación de refresco
        self._refresh_condition = threading.Condition(self._refresh_lock) # Mecanismo de cola/espera

    def decode_payload(self, token: str) -> dict:
        """
        Decisión de Diseño (Robustez): Manejo manual del padding y aislamiento de excepciones.
        Por qué: Base64URL elimina los caracteres '=' de relleno para ser seguro en URLs. Python requiere 
        estrictamente que la longitud sea múltiplo de 4. Capturar de forma genérica errores de parsing 
        (IndexError, ValueError) evita que un token corrupto inyectado maliciosamente tire la aplicación completa.
        """
        try:
            if not token or not isinstance(token, str):
                return None
                
            parts = token.split('.')
            if len(parts) != 3:
                return None  # Token malformado
                
            payload_b64url = parts[1]
            
            # Reconstrucción del padding requerido por la especificación Base64
            rem = len(payload_b64url) % 4
            if rem > 0:
                payload_b64url += '=' * (4 - rem)
                
            # urlsafe_b64decode maneja internamente el reemplazo de '-' por '+' y '_' por '/'
            payload_bytes = base64.urlsafe_b64decode(payload_b64url)
            return json.loads(payload_bytes.decode('utf-8'))
        except (ValueError, IndexError, KeyError, TypeError):
            return None

    def store_tokens(self, token: str):
        """
        Decisión de Diseño (Encapsulación): Centralización de la asignación del token de sesión.
        Por qué: Al mutar el token centralizadamente, aseguramos un único punto de verdad. En una app real,
        aquí se dispararía en paralelo la persistencia hacia un almacenamiento secundario seguro (como un llavero).
        """
        self._current_token = token

    def is_expiring_soon(self, payload: dict, buffer_minutes: int = 5) -> bool:
        """
        Decisión de Diseño (Defensa proactiva): Uso de un margen de seguridad (buffer).
        Por qué: Si hacemos la validación exactamente cuando expira, las peticiones HTTP que vayan en camino 
        hacia el backend morirán en el tránsito debido a la latencia de red. Al usar un buffer de 5 minutos,
        anticipamos la expiración y renovamos el token de forma totalmente invisible para el usuario.
        """
        if not payload or 'exp' not in payload:
            return True  # Si no hay datos confiables de expiración, forzamos el estado inválido por seguridad
            
        exp_seconds = payload['exp']
        now_seconds = int(time.time())
        buffer_seconds = buffer_minutes * 60
        
        return (exp_seconds - now_seconds) < buffer_seconds

    def get_auth_header(self) -> dict:
        """
        Decisión de Diseño (Abstracción): Formateo estricto del estándar RFC 6750.
        Por qué: Abstrae al cliente HTTP de saber cómo se estructuran las cabeceras de autenticación. Si el día 
        de mañana EcoMarket migra de 'Bearer' a otro esquema de autenticación personalizada, solo se modifica esta línea.
        """
        if not self._current_token:
            return {}
        return {"Authorization": f"Bearer {self._current_token}"}

    def refresh_access_token(self) -> str:
        """
        Decisión de Diseño (Concurrencia): Patrón Gatekeeper con Variables de Condición.
        Por qué: Si 5 peticiones concurrentes detectan que el token va a expirar, no debemos saturar al backend 
        con 5 solicitudes de refresco (lo que causaría que el servidor invalide los tokens anteriores y rompa la sesión).
        El primer hilo toma el control (`_is_refreshing = True`), mientras que los hilos subsiguientes se duermen
        en una cola (`_refresh_condition.wait()`). Al despertar, consumen el resultado del primer hilo sin repetir el viaje de red.
        """
        with self._refresh_lock:
            # Si ya hay un proceso de refresco ejecutándose, este hilo se encola a esperar
            if self._is_refreshing:
                print(f"[{threading.current_thread().name}] Detectó refresco en curso. Encolándose a esperar...")
                self._refresh_condition.wait()
                print(f"[{threading.current_thread().name}] Despertó. Utilizando el nuevo token del estado.")
                return self._current_token

            # El primer hilo en llegar se convierte en el "Gatekeeper"
            self._is_refreshing = True

        # --- Zona fuera del lock de control para no bloquear la ejecución de otras lógicas ---
        try:
            print(f"\n[{threading.current_thread().name}] ---> Iniciando petición de red al Backend de EcoMarket...")
            time.sleep(1.5)  # Simulamos la latencia del viaje de red (I/O Bound)
            
            # Simulamos el nuevo token devuelto por el servidor con expiración extendida
            nuevo_exp = int(time.time()) + 600  # Vence en 10 minutos
            nuevo_token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzQ1NiIsImVtYWlsIjoiYW5hQGVjb21hcmtldC5teCIsInJvbGUiOiJvcGVyYXRvciIsImV4cCI6e251ZXZvX2V4cH0sImlhdCI6MTcxMzk5OTEwMH0.signature"
            nuevo_token = nuevo_token.replace("{nuevo_exp}", str(nuevo_exp))
            
            self.store_tokens(nuevo_token)
            exito = True
        except Exception:
            exito = False
            nuevo_token = None
        # ------------------------------------------------------------------------------------

        # Liberamos la cola de espera y notificamos los resultados
        with self._refresh_lock:
            self._is_refreshing = False
            # Despertamos a todos los hilos que estaban esperando en la condición (.wait())
            self._refresh_condition.notify_all()
            
            if not exito:
                self.logout()
                raise Exception("El refresco de token falló en el servidor.")
                
            print(f"[{threading.current_thread().name}] <--- Refresco Exitoso. Notificando a la cola.")
            return nuevo_token

    def logout(self):
        """
        Decisión de Diseño (Limpieza Atómica): Destrucción total de variables de control estatales.
        Por qué: Olvidar reiniciar banderas como `_is_refreshing` o dejar referencias residuales del token anterior 
        provocará comportamientos indeterminados (bloqueos permanentes) cuando un nuevo usuario intente hacer login 
        en la misma ejecución de la aplicación. Rompemos el estado de forma limpia.
        """
        with self._refresh_lock:
            self._current_token = None
            self._is_refreshing = False
            print("[TokenManager] Estado completamente limpio. Sesión cerrada con éxito.")


# ==============================================================================
# SCRIPT DE PRUEBA MANUAL Y SIMULACIÓN CONCURRENTE
# ==============================================================================
if __name__ == "__main__":
    print("=== Simulador de Autenticación EcoMarket ===\n")
    
    # Instanciamos el manager (Patrón Singleton)
    manager = TokenManager()

    # 1. Simulación de Login Exitoso (Token antiguo/cercano a expirar)
    print("[Paso 1] Simulando Login de un usuario...")
    token_inicial = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiJ1c2VyXzQ1NiIsImVtYWlsIjoiYW5hQGVjb21hcmtldC5teCIsInJvbGUiOiJvcGVyYXRvciIsImV4cCI6MTcxNDAwMDAwMCwiaWF0IjoxNzEzOTk5MTAwfQ."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    manager.store_tokens(token_inicial)
    
    # 2. Decodificar e inspeccionar tiempo restante
    print("\n[Paso 2] Inspeccionando credencial cargada:")
    payload = manager.decode_payload(token_inicial)
    print(f" -> Claims extraídos del Payload: {payload}")
    
    if payload:
        now = int(time.time())
        minutos_restantes = (payload['exp'] - now) / 60
        print(f" -> Tiempo restante calculado: {minutos_restantes:.2f} minutos.")
        
        # Evaluar si requiere refresco inminente usando nuestro buffer
        if manager.is_expiring_soon(payload):
            print(" -> [Alerta Máquina de Estados] Estado: ALERTA_EXPIRACION detectado (Faltan < 5 minutos).")
    
    # 3. Prueba de Concurrencia Extrema (Simular ráfaga de peticiones HTTP simultáneas)
    print("\n[Paso 3] Simulando ráfaga concurrente de peticiones HTTP requiriendo refresco...")
    
    def simular_peticion_http_hilo():
        manager_hilo = TokenManager()  # Obtiene la misma instancia única del Singleton
        header = manager_hilo.get_auth_header()
        
        # Simulamos que el interceptor HTTP detecta que el token actual guardado está por expirar
        payload_hilo = manager_hilo.decode_payload(manager_hilo._current_token)
        if manager_hilo.is_expiring_soon(payload_hilo):
            # El hilo intenta refrescar antes de proceder con su petición real
            token_fresco = manager_hilo.refresh_access_token()
            
    # Creamos 3 hilos (3 peticiones HTTP paralelas en segundo plano)
    hilos = []
    for i in range(3):
        t = threading.Thread(target=simular_peticion_http_hilo, name=f"Petición-HTTP-{i+1}")
        hilos.append(t)

    # Disparamos los hilos al mismo tiempo
    for t in hilos:
        t.start()

    # Esperamos a que terminen todas las operaciones para ver el resultado final
    for t in hilos:
        t.join()

    # 4. Verificar estado final
    print("\n[Paso 4] Verificación de estado final de la sesión:")
    payload_final = manager.decode_payload(manager._current_token)
    minutos_finales = (payload_final['exp'] - int(time.time())) / 60
    print(f" -> Nuevo tiempo de expiración del token unificado: {minutos_finales:.2f} minutos.")
    
    # 5. Cierre de sesión seguro
    print("\n[Paso 5] Ejecutando Logout...")
    manager.logout()