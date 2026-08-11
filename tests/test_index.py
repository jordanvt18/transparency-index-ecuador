# -*- coding: utf-8 -*-
"""
Tests básicos para el Índice de Transparencia Municipal.
"""
import json
import sys
from pathlib import Path

# Asegurar import path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from etl.compute_metrics import (
    calculate_hhi,
    fuzzy_normalize_proveedor,
    compute_procurement_metrics,
    compute_declaration_metrics,
)
from compute_transparency_index import (
    normalize_0_100,
    compute_openness_subindex,
    compute_procurement_subindex,
    compute_audit_subindex,
    compute_declaration_subindex,
    compute_transparency_index,
)
from compute_similar_municipios import (
    normalize_features,
    compute_similar_municipios,
    MATCHING_FEATURES,
)


def test_hhi():
    """HHI debe calcularse correctamente."""
    # Un solo proveedor = monopolio = 10000
    assert calculate_hhi(["Proveedor A"]) == 10000.0

    # Dos proveedores iguales = 5000
    assert calculate_hhi(["A", "B"]) == 5000.0

    # Lista vacía = 0
    assert calculate_hhi([]) == 0.0


def test_fuzzy_normalize():
    """Normalización de proveedores debe limpiar sufijos legales."""
    assert fuzzy_normalize_proveedor("Constructora Andina S.A.") == "CONSTRUCTORA ANDINA"
    assert fuzzy_normalize_proveedor("Tecnologías Cía. Ltda.") == "TECNOLOGÍAS"
    assert fuzzy_normalize_proveedor("") == ""
    assert fuzzy_normalize_proveedor("  Empresa  S.A.S  ") == "EMPRESA"


def test_normalize_0_100():
    """Normalización 0-100."""
    assert normalize_0_100(50, 0, 100) == 50.0
    assert normalize_0_100(100, 0, 100) == 100.0
    assert normalize_0_100(0, 0, 100) == 0.0
    assert normalize_0_100(50, 0, 100, invert=True) == 50.0
    assert normalize_0_100(100, 0, 100, invert=True) == 0.0


def test_openness_subindex():
    """Subíndice de apertura debe estar entre 0 y 100."""
    metrics = {
        "tiene_portal_transparencia": True,
        "formatos_abiertos": 80,
        "api_disponible": True,
        "datos_actualizados": True,
    }
    result = compute_openness_subindex(metrics)
    score = result["sub_apertura_score"]
    assert 0 <= score <= 100
    assert score > 80  # Todos los componentes presentes


def test_procurement_subindex():
    """Subíndice de compras debe estar entre 0 y 100."""
    metrics = {
        "pct_licitacion_publica": 50,
        "pct_contratacion_directa": 20,
        "hhi_proveedores": 2000,
    }
    result = compute_procurement_subindex(metrics)
    score = result["sub_compras_score"]
    assert 0 <= score <= 100


def test_audit_subindex():
    """Subíndice de auditoría."""
    metrics = {
        "pct_informes": 80,
        "pct_recomendaciones_cumplidas": 60,
        "num_sanciones": 1,
    }
    result = compute_audit_subindex(metrics)
    assert 0 <= result["sub_rendicion_score"] <= 100


def test_declaration_subindex():
    """Subíndice de declaraciones."""
    metrics = {
        "pct_declaraciones": 75,
        "avg_dias_publicacion": 30,
    }
    result = compute_declaration_subindex(metrics)
    assert 0 <= result["sub_declaraciones_score"] <= 100


def test_transparency_index_full():
    """Índice completo con pesos por defecto."""
    metrics_list = [{
        "municipio_id": "010001",
        "nombre": "Quito",
        "provincia": "Pichincha",
        "poblacion": 2000000,
        "presupuesto": 1200000000,
        "year": 2025,
        "num_contratos": 100,
        "monto_total": 5000000,
        "pct_licitacion_publica": 40,
        "pct_contratacion_directa": 25,
        "hhi_proveedores": 1500,
        "num_proveedores_unicos": 30,
        "pct_declaraciones": 80,
        "avg_dias_publicacion": 45,
        "pct_informes": 75,
        "pct_recomendaciones_cumplidas": 60,
        "num_sanciones": 2,
        "tiene_portal_transparencia": True,
        "formatos_abiertos": 70,
        "api_disponible": True,
        "datos_actualizados": True,
    }]

    results = compute_transparency_index(metrics_list)
    assert len(results) == 1
    assert 0 <= results[0]["indice_transparencia"] <= 100
    assert results[0]["ranking"] == 1


def test_normalize_features():
    """Normalización de features para KNN."""
    metrics_list = [
        {"municipio_id": "001", "poblacion": 100000, "pib_per_capita": 5000,
         "presupuesto": 50000000, "densidad_urbana": 60, "tasa_pobreza": 30, "idh": 0.7},
        {"municipio_id": "002", "poblacion": 200000, "pib_per_capita": 8000,
         "presupuesto": 80000000, "densidad_urbana": 70, "tasa_pobreza": 25, "idh": 0.75},
    ]
    normalized, features = normalize_features(metrics_list)
    assert len(normalized) == 2
    assert len(normalized[0]) == len(features)
    # Todos los valores deben estar entre 0 y 1
    for row in normalized:
        for val in row:
            assert 0 <= val <= 1


def test_similar_municipios():
    """KNN debe encontrar municipios similares."""
    metrics_list = [
        {"municipio_id": f"00{i}", "nombre": f"Muni{i}", "poblacion": 100000 + i * 10000,
         "pib_per_capita": 5000 + i * 500, "presupuesto": 50000000 + i * 5000000,
         "densidad_urbana": 60 + i, "tasa_pobreza": 30 - i, "idh": 0.7 + i * 0.01}
        for i in range(6)
    ]
    results = compute_similar_municipios(metrics_list, k=3)
    assert len(results) > 0
    # Cada municipio debe tener 3 similares
    assert len(results) == 6 * 3


if __name__ == "__main__":
    test_hhi()
    print("✅ test_hhi")
    test_fuzzy_normalize()
    print("✅ test_fuzzy_normalize")
    test_normalize_0_100()
    print("✅ test_normalize_0_100")
    test_openness_subindex()
    print("✅ test_openness_subindex")
    test_procurement_subindex()
    print("✅ test_procurement_subindex")
    test_audit_subindex()
    print("✅ test_audit_subindex")
    test_declaration_subindex()
    print("✅ test_declaration_subindex")
    test_transparency_index_full()
    print("✅ test_transparency_index_full")
    test_normalize_features()
    print("✅ test_normalize_features")
    test_similar_municipios()
    print("✅ test_similar_municipios")
    print("\n🎉 Todos los tests pasaron!")
