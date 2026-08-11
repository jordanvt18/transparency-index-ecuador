# -*- coding: utf-8 -*-
"""
Agente C — Cálculo del Índice de Transparencia Municipal
Implementa compute_transparency_index.py que calcula subíndices y el índice final.
Guarda resultados en data/processed/transparency_index.parquet (y CSV/JSON).

Metodología:
  - Apertura de datos (30%): disponibilidad de portales, formatos abiertos, APIs.
  - Compras públicas (30%): % licitación pública vs adjudicación directa, HHI proveedores.
  - Rendición y auditoría (20%): existencia de informes, cumplimiento de recomendaciones.
  - Declaraciones patrimoniales (20%): % de autoridades con declaración pública.

Normalización: cada subíndice 0–100; índice final = ponderación lineal.
Los pesos son ajustables por el usuario en la UI.
"""
import json
import csv
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Pesos por defecto (suman 100)
DEFAULT_WEIGHTS = {
    "apertura": 0.30,
    "compras": 0.30,
    "rendicion": 0.20,
    "declaraciones": 0.20,
}


def normalize_0_100(value: float, min_val: float, max_val: float, invert: bool = False) -> float:
    """
    Normaliza un valor a escala 0-100.
    Si invert=True, valores más bajos dan puntajes más altos (ej: HHI, contratación directa).
    """
    if max_val == min_val:
        return 50.0
    normalized = (value - min_val) / (max_val - min_val) * 100
    if invert:
        normalized = 100 - normalized
    return max(0, min(100, normalized))


def compute_openness_subindex(metrics: dict) -> dict:
    """
    Subíndice de Apertura de Datos (0-100).
    Componentes:
      - Portal de transparencia disponible (30 pts)
      - Formatos abiertos (25 pts)
      - API disponible (25 pts)
      - Datos actualizados (20 pts)
    """
    portal = metrics.get("tiene_portal_transparencia", False)
    formatos = metrics.get("formatos_abiertos", 0)
    api = metrics.get("api_disponible", False)
    actualizado = metrics.get("datos_actualizados", False)

    score = 0
    score += 30 if portal else 0
    score += min(25, formatos * 0.25)
    score += 25 if api else 0
    score += 20 if actualizado else 0

    return {
        "sub_apertura_score": round(score, 1),
        "sub_apertura_portal": 30 if portal else 0,
        "sub_apertura_formatos": round(min(25, formatos * 0.25), 1),
        "sub_apertura_api": 25 if api else 0,
        "sub_apertura_actualizado": 20 if actualizado else 0,
    }


def compute_procurement_subindex(metrics: dict, all_metrics: list[dict] = None) -> dict:
    """
    Subíndice de Compras Públicas (0-100).
    Componentes:
      - % licitación pública (40 pts): mayor % = mejor
      - % contratación directa (30 pts): menor % = mejor (invertido)
      - HHI proveedores (30 pts): menor concentración = mejor (invertido)
    """
    pct_licitacion = metrics.get("pct_licitacion_publica", 0)
    pct_directa = metrics.get("pct_contratacion_directa", 0)
    hhi = metrics.get("hhi_proveedores", 0)

    # Normalizar contra el rango observado
    score_licitacion = min(40, pct_licitacion / 100 * 40)
    score_directa = max(0, 30 - pct_directa / 100 * 30)
    score_hhi = max(0, 30 - hhi / 10000 * 30)

    score = score_licitacion + score_directa + score_hhi

    return {
        "sub_compras_score": round(score, 1),
        "sub_compras_licitacion": round(score_licitacion, 1),
        "sub_compras_directa": round(score_directa, 1),
        "sub_compras_hhi": round(score_hhi, 1),
    }


def compute_audit_subindex(metrics: dict) -> dict:
    """
    Subíndice de Rendición y Auditoría (0-100).
    Componentes:
      - % informes publicados (40 pts)
      - % recomendaciones cumplplidas (40 pts)
      - Sin sanciones (20 pts)
    """
    pct_informes = metrics.get("pct_informes", 0)
    pct_recomendaciones = metrics.get("pct_recomendaciones_cumplidas", 0)
    num_sanciones = metrics.get("num_sanciones", 0)

    score_informes = pct_informes / 100 * 40
    score_recomendaciones = pct_recomendaciones / 100 * 40
    score_sanciones = max(0, 20 - num_sanciones * 5)

    score = score_informes + score_recomendaciones + score_sanciones

    return {
        "sub_rendicion_score": round(score, 1),
        "sub_rendicion_informes": round(score_informes, 1),
        "sub_rendicion_recomendaciones": round(score_recomendaciones, 1),
        "sub_rendicion_sanciones": round(score_sanciones, 1),
    }


def compute_declaration_subindex(metrics: dict) -> dict:
    """
    Subíndice de Declaraciones Patrimoniales (0-100).
    Componentes:
      - % autoridades con declaración (60 pts)
      - Tiempo de publicación (40 pts): más rápido = mejor
    """
    pct_declaraciones = metrics.get("pct_declaraciones", 0)
    avg_dias = metrics.get("avg_dias_publicacion", None)

    score_pct = pct_declaraciones / 100 * 60

    # Tiempo de publicación: 0 días = 40 pts, 180+ días = 0 pts
    if avg_dias is not None:
        score_tiempo = max(0, 40 - (avg_dias / 180) * 40)
    else:
        score_tiempo = 0

    score = score_pct + score_tiempo

    return {
        "sub_declaraciones_score": round(score, 1),
        "sub_declaraciones_pct": round(score_pct, 1),
        "sub_declaraciones_tiempo": round(score_tiempo, 1),
    }


def compute_transparency_index(metrics_list: list[dict], weights: dict = None) -> list[dict]:
    """
    Calcula el índice de transparencia para todos los municipios.

    Args:
        metrics_list: Lista de métricas municipales (de compute_metrics.py)
        weights: Diccionario con pesos {'apertura': 0.30, 'compras': 0.30, ...}

    Returns:
        Lista de diccionarios con índices y subíndices por municipio
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()

    results = []
    for m in metrics_list:
        openness = compute_openness_subindex(m)
        procurement = compute_procurement_subindex(m)
        audit = compute_audit_subindex(m)
        declaration = compute_declaration_subindex(m)

        # Índice final = suma ponderada
        index_final = (
            openness["sub_apertura_score"] * weights["apertura"] +
            procurement["sub_compras_score"] * weights["compras"] +
            audit["sub_rendicion_score"] * weights["rendicion"] +
            declaration["sub_declaraciones_score"] * weights["declaraciones"]
        )

        result = {
            # Identificación
            "municipio_id": m["municipio_id"],
            "nombre": m.get("nombre", ""),
            "provincia": m.get("provincia", ""),
            "poblacion": m.get("poblacion", 0),
            "presupuesto": m.get("presupuesto", 0),
            "year": m.get("year", ""),
            # Índice final
            "indice_transparencia": round(index_final, 1),
            # Subíndices
            **openness,
            **procurement,
            **audit,
            **declaration,
            # Métricas crudas para detalle
            "num_contratos": m.get("num_contratos", 0),
            "monto_total_contratos": m.get("monto_total", 0),
            "pct_licitacion_publica": m.get("pct_licitacion_publica", 0),
            "pct_contratacion_directa": m.get("pct_contratacion_directa", 0),
            "hhi_proveedores": m.get("hhi_proveedores", 0),
            "num_proveedores_unicos": m.get("num_proveedores_unicos", 0),
            "pct_declaraciones": m.get("pct_declaraciones", 0),
            "pct_informes_auditoria": m.get("pct_informes", 0),
            "num_sanciones": m.get("num_sanciones", 0),
            # Pesos utilizados
            "peso_apertura": weights["apertura"],
            "peso_compras": weights["compras"],
            "peso_rendicion": weights["rendicion"],
            "peso_declaraciones": weights["declaraciones"],
        }
        results.append(result)

    # Ordenar por índice descendente
    results.sort(key=lambda x: x["indice_transparencia"], reverse=True)

    # Agregar ranking
    for i, r in enumerate(results, 1):
        r["ranking"] = i

    return results


def save_results(results: list[dict], year: int, output_format: str = "all"):
    """Guarda resultados en múltiples formatos."""
    if not results:
        return

    # JSON
    if output_format in ("all", "json"):
        json_path = PROCESSED_DIR / f"transparency_index_{year}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  ✅ JSON: {json_path}")

    # CSV
    if output_format in ("all", "csv"):
        csv_path = PROCESSED_DIR / f"transparency_index_{year}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"  ✅ CSV: {csv_path}")

    # Parquet (opcional, requiere pyarrow)
    if output_format in ("all", "parquet"):
        try:
            import pandas as pd
            df = pd.DataFrame(results)
            parquet_path = PROCESSED_DIR / "transparency_index.parquet"
            df.to_parquet(parquet_path, index=False)
            print(f"  ✅ Parquet: {parquet_path}")
        except ImportError:
            print("  ⚠️ pyarrow no instalado, omitiendo formato Parquet")


def main(year: int = None, weights: dict = None):
    """Función principal: carga métricas y calcula índice."""
    if year is None:
        year = datetime.now().year - 1

    # Cargar métricas
    metrics_path = PROCESSED_DIR / f"municipal_metrics_{year}.json"
    if not metrics_path.exists():
        print(f"❌ No se encontraron métricas en {metrics_path}")
        print("  Ejecuta src/etl/compute_metrics.py primero.")
        return

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics_list = json.load(f)

    print(f"🔄 Calculando índice de transparencia para {len(metrics_list)} municipios...")
    if weights:
        print(f"  Pesos: {weights}")
    else:
        print(f"  Pesos por defecto: {DEFAULT_WEIGHTS}")

    results = compute_transparency_index(metrics_list, weights)

    print(f"\n📊 Resultados (Top 10):")
    for r in results[:10]:
        print(f"  {r['ranking']:2d}. {r['nombre']:20s} | Índice: {r['indice_transparencia']:5.1f} "
              f"| Apertura: {r['sub_apertura_score']:5.1f} | Compras: {r['sub_compras_score']:5.1f} "
              f"| Rendición: {r['sub_rendicion_score']:5.1f} | Decl.: {r['sub_declaraciones_score']:5.1f}")

    save_results(results, year)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calcula Índice de Transparencia Municipal")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--peso-apertura", type=float, default=0.30)
    parser.add_argument("--peso-compras", type=float, default=0.30)
    parser.add_argument("--peso-rendicion", type=float, default=0.20)
    parser.add_argument("--peso-declaraciones", type=float, default=0.20)
    args = parser.parse_args()

    weights = {
        "apertura": args.peso_apertura,
        "compras": args.peso_compras,
        "rendicion": args.peso_rendicion,
        "declaraciones": args.peso_declaraciones,
    }
    main(year=args.year, weights=weights)
