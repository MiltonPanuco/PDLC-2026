import pytest
import responses
import requests
from cliente_ecomarket import (
    listar_productos, obtener_producto, crear_producto, 
    actualizar_producto_total, actualizar_producto_parcial, 
    eliminar_producto, API_URL, ResourceNotFoundError, ConflictError
)

# --- FIXTURES ---
@pytest.fixture
def producto_valido():
    return {"id": 1, "nombre": "Miel de Abeja", "precio": 150.0, "categoria": "miel"}

# =================================================================
# 1. HAPPY PATH (6 TESTS)
# =================================================================

@responses.activate
def test_listar_productos_exitoso():
    """Prueba la obtención de la lista completa de productos (200 OK)"""
    responses.add(responses.GET, f"{API_URL}/productos",
                  json=[{"id": 1, "nombre": "Miel"}], status=200)
    resultado = listar_productos()
    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Miel"

@responses.activate
def test_obtener_producto_por_id_exitoso(producto_valido):
    responses.add(responses.GET, f"{API_URL}/productos/1",
                  json=producto_valido, status=200)
    resultado = obtener_producto(1)
    assert resultado["id"] == 1

@responses.activate
def test_crear_producto_exitoso(producto_valido):
    responses.add(responses.POST, f"{API_URL}/productos",
                  json=producto_valido, status=201)
    resultado = crear_producto(producto_valido)
    assert resultado["nombre"] == "Miel de Abeja"

@responses.activate
def test_actualizar_producto_total_exitoso(producto_valido):
    responses.add(responses.PUT, f"{API_URL}/productos/1",
                  json=producto_valido, status=200)
    resultado = actualizar_producto_total(1, producto_valido)
    assert resultado["id"] == 1

@responses.activate
def test_actualizar_producto_parcial_exitoso():
    payload = {"precio": 180.0}
    responses.add(responses.PATCH, f"{API_URL}/productos/1",
                  json={"id": 1, "precio": 180.0}, status=200)
    resultado = actualizar_producto_parcial(1, payload)
    assert resultado["precio"] == 180.0

@responses.activate
def test_eliminar_producto_exitoso():
    responses.add(responses.DELETE, f"{API_URL}/productos/1", status=204)
    resultado = eliminar_producto(1)
    assert resultado is True

# =================================================================
# 2. ERRORES HTTP (8 TESTS)
# =================================================================

@responses.activate
def test_crear_producto_datos_invalidos_retorna_400():
    responses.add(responses.POST, f"{API_URL}/productos", status=400)
    with pytest.raises(requests.exceptions.HTTPError):
        crear_producto({"nombre": ""})

@responses.activate
def test_listar_productos_sin_token_retorna_401():
    responses.add(responses.GET, f"{API_URL}/productos", status=401)
    with pytest.raises(requests.exceptions.HTTPError):
        listar_productos()

@responses.activate
def test_obtener_producto_inexistente_retorna_404():
    responses.add(responses.GET, f"{API_URL}/productos/999", status=404)
    with pytest.raises(ResourceNotFoundError):
        obtener_producto(999)

@responses.activate
def test_actualizar_producto_inexistente_retorna_404():
    responses.add(responses.PUT, f"{API_URL}/productos/999", status=404)
    with pytest.raises(ResourceNotFoundError):
        actualizar_producto_total(999, {})

@responses.activate
def test_eliminar_producto_inexistente_retorna_404():
    responses.add(responses.DELETE, f"{API_URL}/productos/999", status=404)
    with pytest.raises(ResourceNotFoundError):
        eliminar_producto(999)

@responses.activate
def test_crear_producto_duplicado_retorna_409():
    responses.add(responses.POST, f"{API_URL}/productos", 
                  json={"detail": "El producto ya existe"}, status=409)
    with pytest.raises(ConflictError):
        crear_producto({"id": 1})

@responses.activate
def test_error_interno_del_servidor_500():
    responses.add(responses.GET, f"{API_URL}/productos", status=500)
    with pytest.raises(requests.exceptions.HTTPError):
        listar_productos()

@responses.activate
def test_servicio_no_disponible_503():
    responses.add(responses.GET, f"{API_URL}/productos", status=503)
    with pytest.raises(requests.exceptions.HTTPError):
        listar_productos()

# =================================================================
# 3. EDGE CASES (6 TESTS)
# =================================================================

@responses.activate
def test_respuesta_vacia_con_200():
    """Prueba que el cliente maneje bodies vacíos cuando se espera JSON"""
    responses.add(responses.GET, f"{API_URL}/productos/1", body="", status=200)
    with pytest.raises(requests.exceptions.JSONDecodeError):
        obtener_producto(1)

@responses.activate
def test_content_type_incorrecto_html():
    responses.add(responses.GET, f"{API_URL}/productos", 
                  body="<html>Error</html>", content_type="text/html", status=200)
    with pytest.raises(requests.exceptions.JSONDecodeError):
        listar_productos()

@responses.activate
def test_timeout_del_servidor():
    responses.add(responses.GET, f"{API_URL}/productos", 
                  body=requests.exceptions.Timeout("Server timed out"))
    with pytest.raises(requests.exceptions.Timeout):
        listar_productos()

@responses.activate
def test_lista_productos_vacia():
    responses.add(responses.GET, f"{API_URL}/productos", json=[], status=200)
    resultado = listar_productos()
    assert resultado == []

# =================================================================
# 4. MIS TESTS ADICIONALES (BEYOND IA)
# =================================================================

@responses.activate
def test_eliminar_producto_con_dependencias_409():
    """Test Propio 1: Verifica el manejo de 409 al eliminar (Integridad Referencial)"""
    responses.add(responses.DELETE, f"{API_URL}/productos/10", 
                  json={"detail": "Producto con ventas asociadas"}, status=409)
    with pytest.raises(ConflictError) as excinfo:
        eliminar_producto(10)
    assert "registros asociados" in str(excinfo.value)

@responses.activate
def test_buscar_productos_con_caracteres_especiales():
    """Test Propio 2: Verifica que los query params se codifiquen correctamente"""
    responses.add(responses.GET, f"{API_URL}/productos", 
                  json=[], status=200, match=[responses.matchers.query_param_matcher({"nombre": "Miel & Limón"})])
    # Si buscar_productos no usa params de requests o encodeURIComponent, fallará el match
    from cliente_ecomarket import buscar_productos
    resultado = buscar_productos("Miel & Limón")
    assert resultado == []