# -*- coding: utf-8 -*-
"""
Agente B — Normalización y métricas
Extrae campos, calcula métricas por municipio, limpia proveedores (fuzzy matching).
"""
import json
import csv
import math
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_SERCOP = BASE_DIR / "data" / "raw" / "sercop"
RAW_DECLARATIONS = BASE_DIR / "data" / "raw" / "declarations"
RAW_CONTRALORIA = BASE_DIR / "data" / "raw" / "contraloria"
RAW_INEC = BASE_DIR / "data" / "raw" / "inec"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_all_contracts(year: int) -> list[dict]:
    """Carga todos los contratos de todos los municipios para un año."""
    contracts = []
    for f in RAW_SERCOP.glob(f"*_{year}_contracts.json"):
        with open(f, "r", encoding="utf-8") as fh:
            contracts.extend(json.load(fh))
    return contracts


def load_all_declarations(year: int) -> list[dict]:
    """Carga todas las declaraciones patrimoniales para un año."""
    declarations = []
    for f in RAW_DECLARATIONS.glob(f"*_{year}_declarations.json"):
        with open(f, "r", encoding="utf-8") as fh:
            declarations.extend(json.load(fh))
    return declarations


def load_all_audits(year: int) -> list[dict]:
    """Carga todas las auditorías para un año."""
    audit_file = RAW_CONTRALORIA / f"auditorias_{year}.json"
    if audit_file.exists():
        with open(audit_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_municipios() -> list[dict]:
    muni_file = RAW_INEC / "municipios.json"
    if muni_file.exists():
        with open(muni_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def fuzzy_normalize_proveedor(name: str) -> str:
    """Normaliza nombres de proveedores con limpieza básica (fuzzy matching simplificado)."""
    if not name:
        return ""
    # Normalizar mayúsculas, espacios, sufijos legales
    name = name.strip().upper()
    suffixes = [" S.A.", " S.A", " CIA. LTDA.", " CÍA. LTDA.", " CÍA.LTDA.",
                " CIA.LTDA.", " LTDA.", " LTDA", " S.A.S", " S.A.S.", " S.A.S",
                " CIA. S.A.", " CÍA. S.A.", " SUCURSAL ECUADOR"]
    for s in suffixes:
        name = name.replace(s, "")
    name = name.strip()
    # Remover caracteres especiales pero conservar letras y espacios
    name = "".join(c for c in name if c.isalnum() or c.isspace())
    name = " ".join(name.split())  # Normalizar espacios
    # Remover palabras sueltas comunes de sufijos legales
    stop_words = {"S", "A", "SA", "SAS", "LTDA", "CIA", "CIA."}
    name = " ".join(w for w in name.split() if w.upper() not in stop_words)
    return name.strip().upper() or name.upper()


def calculate_hhi(proveedores: list[str]) -> float:
    """
    Calcula el Índice de Herfindahl-Hirschman (HHI) para concentración de proveedores.
    HHI = sum(p_i^2) donde p_i es la participación de cada proveedor.
    0 = competencia perfecta, 10000 = monopolio.
    """
    if not proveedores:
        return 0.0
    counter = Counter(proveedores)
    total = len(proveedores)
    hhi = sum((count / total * 100) ** 2 for count in counter.values())
    return round(hhi, 2)


def compute_procurement_metrics(contracts: list[dict], municipio_id: str) -> dict:
    """Calcula métricas de compras públicas para un municipio."""
    muni_contracts = [c for c in contracts if c.get("municipio_id") == municipio_id]

    if not muni_contracts:
        return {
            "municipio_id": municipio_id,
            "num_contratos": 0,
            "monto_total": 0,
            "avg_monto_contrato": 0,
            "pct_licitacion_publica": 0,
            "pct_contratacion_directa": 0,
            "hhi_proveedores": 0,
            "num_proveedores_unicos": 0,
            "num_contratos_por_habitante": 0,
        }

    num_contracts = len(muni_contracts)
    monto_total = sum(c.get("monto", 0) for c in muni_contracts)

    # Modalidades
    modalidades = [c.get("modalidad", "") for c in muni_contracts]
    total_modalidades = len(modalidades)
    pct_licitacion = sum(1 for m in modalidades if "Licitación" in m) / total_modalidades * 100
    pct_directa = sum(1 for m in modalidades if "Directa" in m) / total_modalidades * 100

    # Proveedores
    proveedores_raw = [c.get("proveedor", "") for c in muni_contracts]
    proveedores_norm = [fuzzy_normalize_proveedor(p) for p in proveedores_raw]
    hhi = calculate_hhi(proveedores_norm)
    num_proveedores_unicos = len(set(proveedores_norm))

    return {
        "municipio_id": municipio_id,
        "num_contratos": num_contracts,
        "monto_total": round(monto_total, 2),
        "avg_monto_contrato": round(monto_total / num_contracts, 2) if num_contracts > 0 else 0,
        "pct_licitacion_publica": round(pct_licitacion, 1),
        "pct_contratacion_directa": round(pct_directa, 1),
        "hhi_proveedores": hhi,
        "num_proveedores_unicos": num_proveedores_unicos,
    }


def compute_declaration_metrics(declarations: list[dict], municipio_id: str) -> dict:
    """Calcula métricas de declaraciones patrimoniales para un municipio."""
    muni_decls = [d for d in declarations if d.get("municipio_id") == municipio_id]

    if not muni_decls:
        return {
            "municipio_id": municipio_id,
            "total_autoridades": 0,
            "autoridades_con_declaracion": 0,
            "pct_declaraciones": 0,
            "avg_dias_publicacion": None,
        }

    total = len(muni_decls)
    con_declaracion = sum(1 for d in muni_decls if d.get("tiene_declaracion", False))
    pct = (con_declaracion / total * 100) if total > 0 else 0

    # Promedio de días de publicación (tiempo entre inicio de año y publicación)
    dias_publicacion = []
    for d in muni_decls:
        if d.get("fecha_publicacion"):
            try:
                fecha = datetime.fromisoformat(d["fecha_publicacion"])
                inicio_anio = datetime(fecha.year, 1, 1)
                dias = (fecha - inicio_anio).days
                dias_publicacion.append(dias)
            except (ValueError, TypeError):
                pass

    avg_dias = round(sum(dias_publicacion) / len(dias_publicacion), 1) if dias_publicacion else None

    return {
        "municipio_id": municipio_id,
        "total_autoridades": total,
        "autoridades_con_declaracion": con_declaracion,
        "pct_declaraciones": round(pct, 1),
        "avg_dias_publicacion": avg_dias,
    }


def compute_audit_metrics(audits: list[dict], municipio_id: str) -> dict:
    """Calcula métricas de auditoría y rendición para un municipio."""
    muni_audits = [a for a in audits if a.get("municipio_id") == municipio_id]

    if not muni_audits:
        return {
            "municipio_id": municipio_id,
            "num_auditorias": 0,
            "num_informes": 0,
            "pct_informes": 0,
            "total_recomendaciones": 0,
            "recomendaciones_cumplidas": 0,
            "pct_recomendaciones_cumplidas": 0,
            "num_sanciones": 0,
        }

    num_audits = len(muni_audits)
    num_informes = sum(1 for a in muni_audits if a.get("tiene_informe", False))
    total_recomendaciones = sum(a.get("num_recomendaciones", 0) for a in muni_audits)
    recomendaciones_cumplidas = sum(a.get("recomendaciones_cumplidas", 0) for a in muni_audits)
    num_sanciones = sum(1 for a in muni_audits if a.get("tiene_sancion", False))

    pct_informes = (num_informes / num_audits * 100) if num_audits > 0 else 0
    pct_recomendaciones = (recomendaciones_cumplidas / total_recomendaciones * 100) if total_recomendaciones > 0 else 0

    return {
        "municipio_id": municipio_id,
        "num_auditorias": num_audits,
        "num_informes": num_informes,
        "pct_informes": round(pct_informes, 1),
        "total_recomendaciones": total_recomendaciones,
        "recomendaciones_cumplidas": recomendaciones_cumplidas,
        "pct_recomendaciones_cumplidas": round(pct_recomendaciones, 1),
        "num_sanciones": num_sanciones,
    }


def compute_openness_metrics(municipio: dict) -> dict:
    """
    Calcula métricas de apertura de datos basadas en disponibilidad
    de portales de transparencia y formatos abiertos.
    """
    # En producción, esto verificaría:
    # - Existencia de portal de transparencia
    # - Disponibilidad de datos en formatos abiertos (CSV, JSON, XLS)
    # - Existencia de API
    # - Actualización de datos

    # Simulación basada en presupuesto (municipios más grandes tienden a tener mejores portales)
    presupuesto = municipio.get("presupuesto", 50000000)
    poblacion = municipio.get("poblacion", 50000)

    # Score base por tamaño
    base_score = min(80, (presupuesto / 1000000000) * 30 + (poblacion / 100000) * 5 + 30)

    import random
    random.seed(hash(f"open_{municipio['id']}") % 2**32)
    portal_score = base_score + random.uniform(-15, 15)
    portal_score = max(10, min(95, portal_score))

    return {
        "municipio_id": municipio["id"],
        "tiene_portal_transparencia": portal_score > 30,
        "portal_score": round(portal_score, 1),
        "formatos_abiertos": round(portal_score * 0.8, 1),
        "api_disponible": portal_score > 60,
        "datos_actualizados": portal_score > 40,
    }


def main(year: int = None):
    """Función principal: calcula todas las métricas y las guarda en processed/."""
    if year is None:
        year = datetime.now().year - 1

    municipios = load_municipios()
    if not municipios:
        print("❌ No hay municipios. Ejecuta los scripts de ingestión primero.")
        return

    print(f"🔄 Cargando datos crudos para año {year}...")
    contracts = load_all_contracts(year)
    declarations = load_all_declarations(year)
    audits = load_all_audits(year)

    print(f"  📄 Contratos: {len(contracts)}")
    print(f"  📝 Declaraciones: {len(declarations)}")
    print(f"  🔍 Auditorías: {len(audits)}")

    print(f"🔄 Calculando métricas para {len(municipios)} municipios...")

    all_metrics = []
    for i, muni in enumerate(municipios):
        mid = muni["id"]

        proc_metrics = compute_procurement_metrics(contracts, mid)
        decl_metrics = compute_declaration_metrics(declarations, mid)
        audit_metrics = compute_audit_metrics(audits, mid)
        open_metrics = compute_openness_metrics(muni)

        # Población para normalización
        poblacion = muni.get("poblacion", 50000)
        proc_metrics["num_contratos_por_habitante"] = round(
            proc_metrics["num_contratos"] / poblacion * 1000, 4
        ) if poblacion > 0 else 0

        # Merge con datos del municipio
        merged = {
            **muni,
            **proc_metrics,
            **decl_metrics,
            **audit_metrics,
            **open_metrics,
            "year": year,
        }
        all_metrics.append(merged)

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(municipios)}] procesados...")

    # Guardar como JSON
    metrics_path = PROCESSED_DIR / f"municipal_metrics_{year}.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, ensure_ascii=False, indent=2)

    # Guardar como CSV
    if all_metrics:
        csv_path = PROCESSED_DIR / f"municipal_metrics_{year}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_metrics[0].keys())
            writer.writeheader()
            writer.writerows(all_metrics)

    print(f"\n✅ Métricas calculadas para {len(all_metrics)} municipios")
    print(f"📁 Guardado en: {PROCESSED_DIR}")

    return all_metrics


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calcula métricas municipales")
    parser.add_argument("--year", type=int, default=None)
    args = parser.parse_args()
    main(year=args.year)
