import time
import json
import base64

def decode_payload(token: str) -> dict:
    """
    Decodifica el payload de un JWT en el cliente y calcula el tiempo restante.
    
    NOTA DE SEGURIDAD PARA EL CLIENTE:
    El cliente hace esto sin verificar la firma porque solo está LEYENDO los datos 
    para lógica de interfaz o flujos locales (como anticipar la expiración). 
    No hay peligro porque el cliente no está autorizando accesos en el servidor; 
    el backend verificará la firma obligatoriamente con su clave secreta en cada petición.
    """
    try:
        # 1. Separar las tres partes por el punto
        parts = token.split('.')
        if len(parts) != 3:
            print("Error: El token no tiene 3 partes.")
            return None
            
        payload_b64url = parts[1]

        # 2. Corregir el "padding" (relleno de '=' necesario para Base64 en Python)
        rem = len(payload_b64url) % 4
        if rem > 0:
            payload_b64url += '=' * (4 - rem)

        # 3. Decodificar usando la función URL-safe de Python
        payload_bytes = base64.urlsafe_b64decode(payload_b64url)
        payload_obj = json.loads(payload_bytes.decode('utf-8'))

        # 4. Calcular el tiempo restante en minutos
        if 'exp' in payload_obj:
            exp_seconds = payload_obj['exp']
            now_seconds = int(time.time()) # Tiempo actual en segundos Unix
            
            minutos_restantes = (exp_seconds - now_seconds) / 60

            if minutos_restantes > 0:
                print(f"[EcoMarket Auth] Token válido. Quedan {minutos_restantes:.2f} minutos.")
            else:
                print(f"[EcoMarket Auth] ¡Alerta! El token expiró hace {abs(minutos_restantes):.2f} minutos.")
        
        return payload_obj

    except Exception as e:
        print(f"Error al decodificar el payload: {e}")
        return None