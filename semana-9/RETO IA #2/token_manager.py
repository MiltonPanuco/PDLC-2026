class CircuitBreakerException(Exception):
    """Excepción lanzada instantáneamente cuando el circuito está ABIERTO."""
    pass


class CircuitBreaker:
    """
    Implementación del patrón Circuit Breaker para el cliente de EcoMarket.
    
    TABLA DE CLASIFICACIÓN DE ERRORES (Auditoría de Diseño):
    -------------------------------------------------------------------------
    Tipo de Error      | HTTP Status | Acción del Circuito | Justificación
    -------------------------------------------------------------------------
    Infras. / Servidor | 500, 503    | Incrementa contador | El backend está caído/degradado.
    Network Timeout    | Tarjeta/TCP | Incrementa contador | Error de enlace o caída de red.
    Lógica de Cliente  | 401, 404    | IGNORAR (No cuenta) | Es un error del flujo de la app,
                       |             |                     | el servidor sí está vivo y activo.
    -------------------------------------------------------------------------
    
    CORRECCIÓN DE LA IA (Causa Raíz del Flujo Semiabierto):
    El estado ABIERTO nunca debe transicionar directamente a CERRADO tras el 
    vencimiento del tiempo de espera. Eso provocaría una inundación de red 
    si el servidor sigue caído. En su lugar, transiciona a SEMIABIERTO, donde 
    se permite exactamente UNA (1) petición de prueba (Canary). Si falla, 
    regresa a ABIERTO penalizando el tiempo; si tiene éxito (200 OK), se cierra.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold  # N fallos consecutivos (5)
        self.recovery_timeout = recovery_timeout    # Tiempo de espera en ABIERTO (30s)
        
        # Estados posibles: "CERRADO", "ABIERTO", "SEMIABIERTO"
        self._estado = "CERRADO"
        self._failure_count = 0
        self._last_state_change = time.time()
        self._lock = threading.Lock()

    def _es_fallo_servidor(self, status_code: int) -> bool:
        """
        Fase APLICA: Filtro de control de errores.
        Determina si el código HTTP devuelto representa una falla de la 
        infraestructura del servidor o si es una respuesta lógica del cliente.
        """
        # Si no hay código (error de conexión/timeout de red de bajo nivel), es fallo de infraestructura
        if status_code is None:
            return True
            
        # Errores 5xx (500 Internal Server Error, 503 Service Unavailable, etc.) son fallos de servidor
        if 500 <= status_code < 600:
            return True
            
        # Errores 4xx (401 Unauthorized, 404 Not Found) significan que el servidor respondió con éxito 
        # a nivel HTTP, por ende, el circuito NO debe acumular estos fallos como caídas del sistema.
        return False

    def verificar_estado(self):
        """Bloquea las peticiones si el circuito está abierto o maneja el timeout."""
        with self._lock:
            if self._estado == "ABIERTO":
                # Verificar si ya pasó el tiempo de penalización y aislamiento
                if time.time() - self._last_state_change > self.recovery_timeout:
                    self._estado = "SEMIABIERTO"
                    self._last_state_change = time.time()
                    print(f"\n[CircuitBreaker] Timeout expiró. Transición: ABIERTO ──> SEMIABIERTO. Intentando petición Canary...")
                else:
                    # El circuito sigue abierto: rechazo inmediato (Fail-Fast) sin tocar la red
                    raise CircuitBreakerException("Circuit Breaker está ABIERTO. Petición bloqueada localmente.")

    def registrar_exito(self):
        """Registra una respuesta exitosa del servidor y restablece el circuito."""
        with self._lock:
            self._failure_count = 0
            if self._estado == "SEMIABIERTO":
                self._estado = "CERRADO"
                self._last_state_change = time.time()
                print("[CircuitBreaker] ¡Petición de prueba exitosa! Transición: SEMIABIERTO ──> CERRADO. Flujo normal restaurado.")

    def registrar_fallo(self, status_code: int):
        """Evalúa el código devuelto e incrementa el contador si es un fallo de servidor."""
        with self._lock:
            # Invoca la función de filtrado auditada
            if not self._es_fallo_servidor(status_code):
                return # Ignorar errores lógicos de cliente (401, 404, etc.)

            self._failure_count += 1
            print(f"[CircuitBreaker] Fallo de infraestructura registrado (Código: {status_code}). Conteo actual: {self._failure_count}/{self.failure_threshold}")

            # Evaluar transiciones de estado según la máquina de estados del disyuntor
            if self._estado == "CERRADO" and self._failure_count >= self.failure_threshold:
                self._estado = "ABIERTO"
                self._last_state_change = time.time()
                print(f"\n[CircuitBreaker] ¡Alerta! Umbral de fallos alcanzado. Transición: CERRADO ──> ABIERTO. Red aislada por {self.recovery_timeout}s.")
                
            elif self._estado == "SEMIABIERTO":
                self._estado = "ABIERTO"
                self._last_state_change = time.time()
                print(f"\n[CircuitBreaker] ¡Error! La petición Canary falló. Transición: SEMIABIERTO ──> ABIERTO. Red re-aislada.")