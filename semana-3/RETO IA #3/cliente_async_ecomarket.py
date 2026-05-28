import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Tuple
# Importamos tus recursos de la Semana 2
from validadores import validar_producto, ValidationError 
from cliente_ecomarket import (
    API_URL, ResourceNotFoundError, ConflictError, EcoMarketError
)

# --- CLIENTE ASÍNCRONO ---

async def listar_productos(session: aiohttp.ClientSession, categoria: str = None) -> List[Dict]:
    params = {"categoria": categoria} if categoria else {}
    async with session.get(f"{API_URL}/productos", params=params) as response:
        response.raise_for_status()
        return await response.json()

async def obtener_producto(session: aiohttp.ClientSession, producto_id: int) -> Dict:
    async with session.get(f"{API_URL}/productos/{producto_id}") as response:
        if response.status == 404:
            raise ResourceNotFoundError(f"Producto {producto_id} no encontrado")
        response.raise_for_status()
        data = await response.json()
        return validar_producto(data) # Validación original

async def crear_producto(session: aiohttp.ClientSession, datos: Dict[str, Any]) -> Dict:
    async with session.post(f"{API_URL}/productos", json=datos) as response:
        if response.status == 409:
            raise ConflictError("El producto ya existe")
        response.raise_for_status()
        return await response.json()

async def actualizar_producto_total(session: aiohttp.ClientSession, producto_id: int, datos: Dict[str, Any]) -> Dict:
    async with session.put(f"{API_URL}/productos/{producto_id}", json=datos) as response:
        if response.status == 404: raise ResourceNotFoundError(f"ID {producto_id} no existe")
        response.raise_for_status()
        return await response.json()

async def actualizar_producto_parcial(session: aiohttp.ClientSession, producto_id: int, campos: Dict[str, Any]) -> Dict:
    async with session.patch(f"{API_URL}/productos/{producto_id}", json=campos) as response:
        if response.status == 404: raise ResourceNotFoundError(f"ID {producto_id} no existe")
        response.raise_for_status()
        return await response.json()

async def eliminar_producto(session: aiohttp.ClientSession, producto_id: int) -> bool:
    async with session.delete(f"{API_URL}/productos/{producto_id}") as response:
        if response.status == 404: raise ResourceNotFoundError(f"ID {producto_id} no existe")
        return response.status == 204

# --- FUNCIONES DE CARGA MASIVA Y DASHBOARD ---

async def cargar_dashboard() -> Dict:
    """Carga productos, categorías y perfil en paralelo."""
    async with aiohttp.ClientSession() as session:
        tareas = [
            listar_productos(session),
            session.get(f"{API_URL}/categorias"), # Simulado
            session.get(f"{API_URL}/perfil")      # Simulado
        ]
        # return_exceptions=True evita que un fallo detenga todo el dashboard
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        
        dashboard = {"datos": {}, "errores": []}
        mapeo = ["productos", "categorias", "perfil"]
        
        for nombre, res in zip(mapeo, resultados):
            if isinstance(res, Exception):
                dashboard["errores"].append({nombre: str(res)})
            else:
                dashboard["datos"][nombre] = res
        return dashboard

async def crear_multiples_productos(lista_productos: List[Dict]) -> Tuple[List, List]:
    """Crea productos con un límite de 5 peticiones simultáneas."""
    sem = asyncio.Semaphore(5)
    creados, fallidos = [], []

    async def tarea_con_semaforo(session, datos):
        async with sem:
            try:
                res = await crear_producto(session, datos)
                creados.append(res)
            except Exception as e:
                fallidos.append({"item": datos.get('nombre'), "error": str(e)})

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(tarea_con_semaforo(session, p) for p in lista_productos))
    
    return creados, fallidos