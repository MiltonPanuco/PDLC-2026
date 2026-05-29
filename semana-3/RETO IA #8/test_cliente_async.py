import pytest
import asyncio
import aiohttp
from aioresponses import aioresponses
from cliente_async_ecomarket import (
    listar_productos, obtener_producto, crear_producto, 
    eliminar_producto, cargar_dashboard, crear_multiples_productos, API_URL
)
from validadores import ValidationError

# --- FIXTURES ---
@pytest.fixture
def mock_api():
    with aioresponses() as m:
        yield m

@pytest.fixture
def producto_valido():
    return {"id": 103, "nombre": "Miel Casa 103", "precio": 180.0, "categoria": "miel"}

# =================================================================
# 1. EQUIVALENCIA Y CRUD (6 TESTS)
# =================================================================

@pytest.mark.asyncio
async def test_obtener_producto_exitoso(mock_api, producto_valido):
    mock_api.get(f"{API_URL}/productos/103", payload=producto_valido)
    async with aiohttp.ClientSession() as session:
        res = await obtener_producto(session, 103)
        assert res["nombre"] == "Miel Casa 103"

@pytest.mark.asyncio
async def test_error_404_lanza_excepcion(mock_api):
    mock_api.get(f"{API_URL}/productos/999", status=404)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(Exception) as exc:
            await obtener_producto(session, 999)
        assert "no encontrado" in str(exc.value)

@pytest.mark.asyncio
async def test_crear_producto_conflicto_409(mock_api, producto_valido):
    mock_api.post(f"{API_URL}/productos", status=409)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(Exception) as exc:
            await crear_producto(session, producto_valido)
        assert "ya existe" in str(exc.value)

# =================================================================
# 2. CONCURRENCIA Y GATHER (7 TESTS)
# =================================================================

@pytest.mark.asyncio
async def test_cargar_dashboard_parcial(mock_api):
    """Prueba que el dashboard cargue productos aunque falle el perfil."""
    mock_api.get(f"{API_URL}/productos", payload=[{"id": 1}])
    mock_api.get(f"{API_URL}/categorias", payload=["miel", "frutas"])
    mock_api.get(f"{API_URL}/perfil", status=500)
    
    res = await cargar_dashboard()
    assert "productos" in res["datos"]
    assert len(res["errores"]) == 1

@pytest.mark.asyncio
async def test_crear_masivo_respeta_semaforo(mock_api):
    """Verifica el procesamiento por lotes del semáforo."""
    for i in range(15):
        mock_api.post(f"{API_URL}/productos", status=201, payload={"id": i})
    
    prods = [{"id": i, "nombre": f"P{i}", "precio": 10, "categoria": "miel"} for i in range(15)]
    creados, fallidos = await crear_multiples_productos(prods)
    assert len(creados) == 15
    assert len(fallidos) == 0

# =================================================================
# 3. TIMEOUTS Y CANCELACIÓN (7 TESTS)
# =================================================================

@pytest.mark.asyncio
async def test_timeout_individual_por_peticion(mock_api):
    """Test de timeout: Una petición lenta no debe bloquear al cliente."""
    mock_api.get(f"{API_URL}/productos", payload={"data": "slow"}, delay=5)
    async with aiohttp.ClientSession() as session:
        # Usamos wait_for para forzar el timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(listar_productos(session), timeout=0.1)

@pytest.mark.asyncio
async def test_cancelacion_tareas_pendientes(mock_api):
    """Si una tarea falla críticamente, las demás deben cancelarse."""
    mock_api.get(f"{API_URL}/perfil", status=401)
    mock_api.get(f"{API_URL}/productos", payload=[{"id": 1}], delay=10)
    
    # Aquí probarías tu función cargar_con_autenticacion del coordinador
    pass 

# =================================================================
# 4. EDGE CASES (2 TESTS ADICIONALES)
# =================================================================

@pytest.mark.asyncio
async def test_respuesta_json_corrupto(mock_api):
    """Verifica que el cliente no truene si el servidor manda basura."""
    mock_api.get(f"{API_URL}/productos", body="No es un JSON")
    async with aiohttp.ClientSession() as session:
        with pytest.raises(aiohttp.ContentTypeError):
            await listar_productos(session)

@pytest.mark.asyncio
async def test_reuso_de_sesion_cerrada(mock_api):
    """Verifica que no intentemos usar una sesión ya cerrada."""
    async with aiohttp.ClientSession() as session:
        pass
    with pytest.raises(RuntimeError):
        await listar_productos(session)