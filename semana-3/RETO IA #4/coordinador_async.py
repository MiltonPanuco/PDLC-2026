import pytest
from validadores import validar_producto, ValidationError

def test_fallo_campo_requerido():
    """Caso 1: Falta un campo esencial (categoria)"""
    producto_incompleto = {"id": 1, "nombre": "Manzana", "precio": 1.5}
    with pytest.raises(ValidationError) as excinfo:
        validar_producto(producto_incompleto)
    assert "Falta campo requerido: 'categoria'" in str(excinfo.value)

def test_fallo_precio_negativo():
    """Caso 2: El servidor devuelve un precio inválido (Regla de negocio)"""
    producto_negativo = {
        "id": 2, "nombre": "Miel", "precio": -10.0, 
        "categoria": "miel", "disponible": True
    }
    with pytest.raises(ValidationError) as excinfo:
        validar_producto(producto_negativo)
    assert "precio debe ser número positivo" in str(excinfo.value)

def test_fallo_tipo_dato_incorrecto():
    """Caso 3: El ID llega como string en lugar de int"""
    producto_mal_tipado = {
        "id": "101", "nombre": "Leche", "precio": 2.0, 
        "categoria": "lacteos"
    }
    with pytest.raises(ValidationError) as excinfo:
        validar_producto(producto_mal_tipado)
    assert "id debe ser int" in str(excinfo.value)

def test_fallo_categoria_no_permitida():
    """Caso 4: La categoría no está en la lista blanca"""
    producto_extraño = {
        "id": 4, "nombre": "Refresco", "precio": 1.0, 
        "categoria": "bebidas_azucaradas"
    }
    with pytest.raises(ValidationError) as excinfo:
        validar_producto(producto_extraño)
    assert "categoría 'bebidas_azucaradas' no es válida" in str(excinfo.value)

def test_fallo_fecha_invalida():
    """Caso 5: El formato de fecha es incorrecto"""
    producto_fecha_mal = {
        "id": 5, "nombre": "Uvas", "precio": 3.0, 
        "categoria": "frutas", "creado_en": "2023/10/27"
    }
    with pytest.raises(ValidationError) as excinfo:
        validar_producto(producto_fecha_mal)
    assert "creado_en no es una fecha ISO 8601 válida" in str(excinfo.value)