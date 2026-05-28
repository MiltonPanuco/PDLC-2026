import requests
from typing import List, Dict, Any, Union

# ============================================================
# ECO-MARKET API CLIENT (Versión Pythonic & Resiliente)
# ============================================================

API_URL = 'https://api.ecomarket.com/api'

class EcoMarketError(Exception):
    """Excepción base para el cliente."""
    pass

class ResourceNotFoundError(EcoMarketError):
    """Error 404: Recurso no encontrado."""
    pass

class ConflictError(EcoMarketError):
    """Error 409: Conflicto o duplicado."""
    pass

# --- 1. OPERACIONES DE LECTURA ---

def listar_productos() -> List[Dict]:
    """Obtiene la lista completa de productos."""
    response = requests.get(f"{API_URL}/productos")
    response.raise_for_status()
    return response.json()

def buscar_productos(nombre: str = "") -> List[Dict]:
    """Busca productos por coincidencia de nombre usando Query Params."""
    params = {"nombre": nombre} if nombre else {}
    response = requests.get(f"{API_URL}/productos", params=params)
    response.raise_for_status()
    return response.json()

# --- 2. OPERACIONES DE ESCRITURA (CRUD) ---

def crear_producto(datos: Dict[str, Any]) -> Dict:
    """
    POST /productos
    Crea un producto. Lanza ConflictError si el SKU o nombre ya existe.
    """
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{API_URL}/productos", json=datos, headers=headers)
    
    if response.status_code == 409:
        raise ConflictError(f"El producto ya existe: {response.json().get('detail', 'Error de conflicto')}")
    
    response.raise_for_status() # Verifica 201 Created
    return response.json()

def actualizar_producto_total(producto_id: int, datos: Dict[str, Any]) -> Dict:
    """
    PUT /productos/{id}
    Reemplazo total del recurso. Requiere todos los campos en 'datos'.
    """
    headers = {"Content-Type": "application/json"}
    response = requests.put(f"{API_URL}/productos/{producto_id}", json=datos, headers=headers)
    
    if response.status_code == 404:
        raise ResourceNotFoundError(f"No se puede actualizar: Producto {producto_id} no existe.")
    
    response.raise_for_status()
    return response.json()

def actualizar_producto_parcial(producto_id: int, campos: Dict[str, Any]) -> Dict:
    """
    PATCH /productos/{id}
    Modificación parcial. Solo envía los campos que deseas cambiar.
    """
    headers = {"Content-Type": "application/json"}
    response = requests.patch(f"{API_URL}/productos/{producto_id}", json=campos, headers=headers)
    
    if response.status_code == 404:
        raise ResourceNotFoundError(f"No se encontró producto {producto_id} para modificar.")
    
    response.raise_for_status()
    return response.json()

def eliminar_producto(producto_id: int) -> bool:
    """
    DELETE /productos/{id}
    Retorna True si se eliminó (204). Lanza excepción si hay conflicto o no existe.
    """
    response = requests.delete(f"{API_URL}/productos/{producto_id}")
    
    if response.status_code == 404:
        raise ResourceNotFoundError(f"Producto {producto_id} no encontrado para eliminar.")
    if response.status_code == 409:
        raise ConflictError(f"No se puede eliminar: El producto {producto_id} tiene registros asociados.")
    
    return response.status_code == 204