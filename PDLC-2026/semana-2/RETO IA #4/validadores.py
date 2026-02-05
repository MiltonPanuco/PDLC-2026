from datetime import datetime
from typing import List, Dict, Any

CATEGORIAS_VALIDAS = ["frutas", "verduras", "lacteos", "miel", "conservas"]
REQUERIDOS = {"id", "nombre", "precio", "categoria"}

class ValidationError(Exception):
    """Excepción para errores de contrato de datos."""
    pass

def validar_producto(data: Dict[str, Any]) -> Dict:
    if not isinstance(data, dict):
        raise ValidationError("El producto no es un diccionario válido.")

    errores = []
    
    # 1. Campos requeridos
    for campo in REQUERIDOS:
        if campo not in data:
            errores.append(f"Falta campo requerido: '{campo}'")
    
    if errores: # Salida temprana si faltan campos base
        raise ValidationError(f"Estructura incompleta: {', '.join(errores)}")

    # 2. Tipos y Rango
    if not isinstance(data['id'], int):
        errores.append(f"id debe ser int, se recibió {type(data['id']).__name__}")
    
    if not isinstance(data['nombre'], str) or len(data['nombre']) < 2:
        errores.append("nombre debe ser str (mín. 2 caracteres)")

    if not isinstance(data['precio'], (int, float)) or data['precio'] <= 0:
        errores.append(f"precio debe ser número positivo, se recibió {data['precio']}")

    if data['categoria'] not in CATEGORIAS_VALIDAS:
        errores.append(f"categoría '{data['categoria']}' no es válida")

    if 'disponible' in data and not isinstance(data['disponible'], bool):
        errores.append("disponible debe ser booleano")

    # 3. Fecha ISO 8601
    if data.get('creado_en'):
        try:
            datetime.fromisoformat(data['creado_en'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            errores.append("creado_en no es una fecha ISO 8601 válida")

    if errores:
        raise ValidationError(" | ".join(errores))
    
    return data

def validar_lista_productos(data: Any) -> List[Dict]:
    if not isinstance(data, list):
        raise ValidationError(f"Se esperaba lista, se obtuvo {type(data).__name__}")
    return [validar_producto(item) for item in data]