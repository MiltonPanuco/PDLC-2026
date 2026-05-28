"""
DECISIONES DE DISEÑO - RETO 1 (MÁQUINA DE ESTADOS DEL DISYUNTOR):
--------------------------------------------------------------------------------
1. Implementación de un Estado Intermedio Obligatorio (SEMIABIERTO):
   El circuito nunca debe transicionar directamente de ABIERTO a CERRADO tras el 
   vencimiento del tiempo de espera. Pasar directamente a CERRADO inundaría un 
   servidor degradado con todo el tráfico acumulado del cliente, provocando una 
   caída inmediata en cascada. El estado SEMIABIERTO actúa como un filtro síncrono 
   que permite el paso controlado de una única petición de prueba (Canary).
2. Mecanismo de Rechazo Inmediato (Fail-Fast) en ABIERTO:
   Mientras el temporizador de penalización esté activo en el estado ABIERTO, las 
   peticiones entrantes deben abortar localmente lanzando una excepción dedicada 
   sin tocar los sockets de red. Esto ahorra ancho de banda, batería y CPU en el 
   dispositivo cliente, y otorga un tiempo de respiro absoluto para la 
   autorrecuperación del backend de EcoMarket.
3. Restablecimiento Atómico con Reinicio de Penalización:
   Si el servidor se encuentra en recuperación parcial pero falla ante la petición 
   Canary en el estado SEMIABIERTO, el circuito debe regresar inmediatamente a 
   ABIERTO. Esto reinicia el temporizador de aislamiento completo, aislando de 
   nuevo el sistema de manera proactiva.

TABLA DE CLASIFICACIÓN DE ERRORES - RETO 2 (FILTRADO DE INTERRUPCIONES):
--------------------------------------------------------------------------------
Tipo de Error      | HTTP Status / Origen | Acción del Circuito | Justificación
--------------------------------------------------------------------------------
Infras. / Servidor | 500 (Internal Error) | Incrementa contador | El backend está 
                   | 503 (Service Unav.)  | de fallos.          | sufriendo una caída o
                   | None (Network Timeout)                     | saturación real.
--------------------------------------------------------------------------------
Lógica de Cliente  | 401 (Unauthorized)   | IGNORAR             | Son respuestas válidas
                   | 404 (Not Found)      | (No altera conteo)  | de la lógica del negocio;
                   |                      |                     | el servidor está vivo.
--------------------------------------------------------------------------------
"""

import time
import threading

class CircuitBreakerException(Exception):
    """Excepción de interrupción instantánea lanzada cuando el circuito está ABIERTO."""
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        """
        Inicializa el Disyuntor del Cliente con un umbral de fallos y tiempo de recuperación.
        """
        self.failure_threshold = failure_threshold  # N fallos consecutivos antes de abrir (5)
        self.recovery_timeout = recovery_timeout    # Tiempo de aislamiento en segundos (30s)
        
        # Estados válidos: "CERRADO", "ABIERTO", "SEMIABIERTO"
        self._estado = "CERRADO"
        self._failure_count = 0
        self._last_state_change = time.time()
        self._lock = threading.Lock()  # Lock para control concurrente del estado interno

    def _es_fallo_servidor(self, status_code: int) -> bool:
        """
        Filtro de control de errores (Reto 2).
        Distingue fallos críticos de infraestructura de las respuestas lógicas del cliente.
        """
        # Excepciones de red de bajo nivel o timeouts (no devuelven código HTTP)
        if status_code is None:
            return True
            
        # Códigos de error de infraestructura del servidor (5xx)
        if 500 <= status_code < 600:
            return True
            
        # Códigos 4xx (401, 404, etc.) indican que el backend opera con normalidad
        return False

    def verificar_estado(self):
        """
        Asegura el comportamiento de la máquina de estados antes de procesar una petición.
        Lanza CircuitBreakerException si el tráfico se encuentra bloqueado de forma local.
        """
        with self._lock:
            if self._estado == "ABIERTO":
                # Comprobar si el tiempo de aislamiento obligatorio ya concluyó
                if time.time() - self._last_state_change > self.recovery_timeout:
                    self._estado = "SEMIABIERTO"
                    self._last_state_change = time.time()
                    print(f"\n[CircuitBreaker] {time.strftime('%H:%M:%S')} - Tiempo de aislamiento vencido.")
                    print("[CircuitBreaker] Transición: ABIERTO ──> SEMIABIERTO. Habilitando petición de prueba (Canary)...")
                else:
                    # Mecanismo Fail-Fast activo: Bloqueo de red inmediato
                    raise CircuitBreakerException("Circuit Breaker está ABIERTO. Petición bloqueada localmente de forma preventiva.")

    def registrar_exito(self):
        """
        Registra un flujo exitoso (200 OK) proveniente de la red.
        Cierra el circuito si la petición de prueba en SEMIABIERTO concluye con éxito.
        """
        with self._lock:
            self._failure_count = 0  # Reseteo atómico del contador consecutivo
            
            if self._estado == "SEMIABIERTO":
                self._estado = "CERRADO"
                self._last_state_change = time.time()
                print(f"[CircuitBreaker] {time.strftime('%H:%M:%S')} - ¡Petición Canary exitosa!")
                print("[CircuitBreaker] Transición: SEMIABIERTO ──> CERRADO. Flujo de red totalmente restaurado.")

    def registrar_fallo(self, status_code: int):
        """
        Analiza las excepciones detectadas por las llamadas de red.
        Ejecuta las transiciones hacia ABIERTO si se cumplen los criterios de la auditoría.
        """
        with self._lock:
            # Invocar el filtro de errores de la tabla de clasificación
            if not self._es_fallo_servidor(status_code):
                print(f"[CircuitBreaker] Código {status_code} ignorado de forma segura (Error de lógica de cliente, no altera conteo).")
                return

            self._failure_count += 1
            print(f"[CircuitBreaker] Fallo de infraestructura detectado. Código: {status_code if status_code else 'NETWORK_TIMEOUT'}. Conteo consecutivo: {self._failure_count}/{self.failure_threshold}")

            # Transición de CERRADO a ABIERTO si se alcanza el umbral de tolerancia
            if self._estado == "CERRADO" and self._failure_count >= self.failure_threshold:
                self._estado = "ABIERTO"
                self._last_state_change = time.time()
                print(f"\n[CircuitBreaker] {time.strftime('%H:%M:%S')} - ALERTA: Umbral de tolerancia superado.")
                print(f"[CircuitBreaker] Transición: CERRADO ──> ABIERTO. Tráfico bloqueado localmente por {self.recovery_timeout}s.")
                
            # Transición de SEMIABIERTO a ABIERTO si la petición Canary vuelve a fallar
            elif self._estado == "SEMIABIERTO":
                self._estado = "ABIERTO"
                self._last_state_change = time.time()
                print(f"\n[CircuitBreaker] {time.strftime('%H:%M:%S')} - ERROR: La petición Canary falló ante el servidor.")
                print(f"[CircuitBreaker] Transición: SEMIABIERTO ──> ABIERTO. El disyuntor vuelve a aislar el sistema.")


# ==============================================================================
# SCRIPT DE COMPROBACIÓN Y SIMULACIÓN COMPLETA DE CASOS
# ==============================================================================
if __name__ == "__main__":
    print(f"=== 🔌 Entorno de Simulación: Patrón Circuit Breaker ===")
    print(f"Desarrollador: VAZQUEZ TALAVERA MARIA BELEN (Matrícula: 24213132)\n")
    
    # Inicializamos el disyuntor con umbral bajo de 3 fallos y 3 segundos de timeout para pruebas rápidas
    disyuntor = CircuitBreaker(failure_threshold=3, recovery_timeout=3.0)

    print("--- CASO 1: Operación Normal y Filtrado de Errores Lógicos (401/404) ---")
    try:
        disyuntor.verificar_estado()
        print("[App] Enviando petición a /api/perfil...")
        # Simulamos que el backend responde 401 porque el usuario no tiene sesión
        disyuntor.registrar_fallo(status_code=401)
        disyuntor.registrar_exito()
    except Exception as e:
        print(f"[App] Error inesperado: {e}")

    print("\n--- CASO 2: Acumulación de Fallos de Servidor (500/503) e Interrupción ---")
    for i in range(3):
        try:
            disyuntor.verificar_estado()
            print(f"[App] Petición HTTP #{i+1} en curso...")
            # Simulamos caída del servidor de EcoMarket
            disyuntor.registrar_fallo(status_code=503)
        except CircuitBreakerException as e:
            print(f"[App] Intercepción capturada: {e}")

    print("\n--- CASO 3: Validación del Mecanismo Fail-Fast (Rechazo inmediato de red) ---")
    try:
        print("[App] El componente gráfico intenta solicitar datos secundarios...")
        disyuntor.verificar_estado()
    except CircuitBreakerException as e:
        print(f"[App] Éxito Fail-Fast: {e} (No se generó tráfico de red innecesario).")

    print("\n--- CASO 4: Transición a SEMIABIERTO y Prueba de Recuperación (Canary) ---")
    print("[Sistema] Esperando a que venza el tiempo de penalización del servidor...")
    time.sleep(3.2)  # Dormimos el hilo el tiempo suficiente para superar el recovery_timeout de 3s
    
    try:
        # Esto debería transicionar el circuito a SEMIABIERTO
        disyuntor.verificar_estado()
        print("[App] Enviando única petición Canary de prueba...")
        
        # Simulamos que el servidor responde con éxito (200 OK) tras su restauración
        disyuntor.registrar_exito()
    except Exception as e:
        print(f"[App] Error en Canary: {e}")

    print("\n--- CASO 5: Verificación de Flujo Normal Restaurado (Circuito Cerrado de nuevo) ---")
    try:
        disyuntor.verificar_estado()
        print("[App] Petición ordinaria enviada con éxito. El circuito opera en CERRADO.")
    except Exception as e:
        print(f"[App] Error: {e}")