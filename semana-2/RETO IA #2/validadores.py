import json
from datetime import datetime

# Configuración de negocio
CATEGORIAS_VALIDAS = ["frutas", "verduras", "lacteos", "miel", "conservas"]
CAMPOS_PRODUCTO = {"id", "nombre", "precio", "categoria", "productor", "disponible", "creado_en"}
CAMPOS_PRODUCTOR = {"id", "nombre"}

def validar_producto(data):
    """
    Valida un diccionario JSON contra las reglas de negocio de EcoMarket.
    Retorna (True, []) si es válido, (False, [errores]) si no.
    """
    errores = []

    # 1. Validación de Campos Extra (Strict Mode)
    campos_recibidos = set(data.keys())
    if not campos_recibidos.issubset(CAMPOS_PRODUCTO):
        extra = campos_recibidos - CAMPOS_PRODUCTO
        errores.append(f"Campos no permitidos detectados: {extra}")

    # 2. Verificación de Campos Requeridos
    for campo in CAMPOS_PRODUCTO:
        if campo not in data:
            errores.append(f"Falta el campo requerido: {campo}")

    if errores: return False, errores

    # 3. Validaciones de Tipo y Rango
    if not isinstance(data['id'], int): errores.append("id debe ser int")
    if not isinstance(data['nombre'], str) or len(data['nombre']) < 2:
        errores.append("nombre debe ser string (min 2 caracteres)")
    
    if not isinstance(data['precio'], (int, float)) or data['precio'] <= 0:
        errores.append("precio debe ser un número positivo")
    
    if data['categoria'] not in CATEGORIAS_VALIDAS:
        errores.append(f"categoria '{data['categoria']}' no es válida")

    if not isinstance(data['disponible'], bool):
        errores.append("disponible debe ser un booleano")

    # 4. Validación del Objeto Anidado (Productor)
    prod = data['productor']
    if not isinstance(prod, dict):
        errores.append("productor debe ser un objeto")
    else:
        if not isinstance(prod.get('id'), int) or not isinstance(prod.get('nombre'), str):
            errores.append("productor debe contener id (int) y nombre (str)")

    # 5. Validación de Fecha ISO 8601
    try:
        # Reemplazamos Z con +00:00 para compatibilidad con fromisoformat en Python < 3.11
        fecha_str = data['creado_en'].replace('Z', '+00:00')
        datetime.fromisoformat(fecha_str)
    except (ValueError, AttributeError, TypeError):
        errores.append("creado_en debe ser una fecha ISO 8601 válida")

    return len(errores) == 0, errores