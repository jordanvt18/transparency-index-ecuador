# -*- coding: utf-8 -*-
"""
API REST para el Índice de Transparencia Municipal
Endpoints:
  GET /municipio/{id}/transparency → índice y subíndices
  GET /municipio/{id}/similar → lista de municipios similares con distancias
  GET /municipio/{id}/contracts?year= → contratos filtrados
  GET /ranking?province=&min_pop=&max_pop= → ranking dinámico
  GET /weights → obtener pesos actuales
  POST /weights → actualizar pesos y recalcular
"""
import json
import csv
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_SERCOP = BASE_DIR / "data" / "raw" / "sercop"
WEB_DIR = BASE_DIR / "web"

app = FastAPI(
    title="Índice de Transparencia Municipal - Ecuador",
    description="API para consultar el índice de transparencia y comparar municipios similares",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pesos por defecto
DEFAULT_WEIGHTS = {"apertura": 0.30, "compras": 0.30, "rendicion": 0.20, "declaraciones": 0.20}
current_weights = DEFAULT_WEIGHTS.copy()


def load_index_data(year: int = None) -> list[dict]:
    """Carga los datos del índice de transparencia."""
    if year is None:
        year = datetime.now().year - 1
    json_path = PROCESSED_DIR / f"transparency_index_{year}.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Intentar sin año
    generic = PROCESSED_DIR / "transparency_index.json"
    if generic.exists():
        with open(generic, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_similar_data() -> list[dict]:
    """Carga datos de municipios similares."""
    json_path = PROCESSED_DIR / "similar_municipios.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_contracts(municipio_id: str = None, year: int = None) -> list[dict]:
    """Carga contratos de un municipio para un año."""
    contracts = []
    pattern = f"{municipio_id}_{year}_contracts.json" if municipio_id and year else "*_contracts.json"
    for f in RAW_SERCOP.glob(pattern):
        with open(f, "r", encoding="utf-8") as fh:
            contracts.extend(json.load(fh))
    return contracts


def recalculate_index(weights: dict) -> list[dict]:
    """Recalcula el índice con pesos personalizados."""
    import sys
    sys.path.insert(0, str(BASE_DIR / "src"))
    from compute_transparency_index import compute_transparency_index

    # Cargar métricas base
    year = datetime.now().year - 1
    metrics_path = PROCESSED_DIR / f"municipal_metrics_{year}.json"
    if not metrics_path.exists():
        return []

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics_list = json.load(f)

    results = compute_transparency_index(metrics_list, weights)
    return results


# ==================== ENDPOINTS ====================

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/municipio/{municipio_id}/transparency")
async def get_transparency(municipio_id: str, year: int = None):
    """Índice y subíndices de transparencia para un municipio."""
    data = load_index_data(year)
    for m in data:
        if m.get("municipio_id") == municipio_id:
            return m
    raise HTTPException(status_code=404, detail="Municipio no encontrado")


@app.get("/api/municipio/{municipio_id}/similar")
async def get_similar(municipio_id: str):
    """Lista de municipios similares con distancias."""
    similar_data = load_similar_data()
    results = [s for s in similar_data if s.get("municipio_id_origen") == municipio_id]

    if not results:
        raise HTTPException(status_code=404, detail="No hay datos de similaridad para este municipio")

    # Enriquecer con índice de transparencia del municipio similar
    index_data = load_index_data()
    index_map = {m["municipio_id"]: m for m in index_data}

    for r in results:
        similar_id = r["municipio_id_similar"]
        if similar_id in index_map:
            r["indice_transparencia"] = index_map[similar_id]["indice_transparencia"]
            r["sub_apertura_score"] = index_map[similar_id].get("sub_apertura_score", 0)
            r["sub_compras_score"] = index_map[similar_id].get("sub_compras_score", 0)
            r["sub_rendicion_score"] = index_map[similar_id].get("sub_rendicion_score", 0)
            r["sub_declaraciones_score"] = index_map[similar_id].get("sub_declaraciones_score", 0)

    return {"municipio_id": municipio_id, "similares": results}


@app.get("/api/municipio/{municipio_id}/contracts")
async def get_contracts(
    municipio_id: str,
    year: int = Query(default=None, description="Año de los contratos"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Contratos filtrados por municipio y año."""
    if year is None:
        year = datetime.now().year - 1

    contracts = load_contracts(municipio_id, year)
    total = len(contracts)
    paginated = contracts[offset:offset + limit]

    return {
        "municipio_id": municipio_id,
        "year": year,
        "total": total,
        "limit": limit,
        "offset": offset,
        "contracts": paginated,
    }


@app.get("/api/ranking")
async def get_ranking(
    province: str = Query(default=None, description="Filtrar por provincia"),
    min_pop: int = Query(default=None, ge=0, description="Población mínima"),
    max_pop: int = Query(default=None, ge=0, description="Población máxima"),
    limit: int = Query(default=50, le=200),
    sort_by: str = Query(default="indice_transparencia", description="Campo para ordenar"),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
):
    """Ranking dinámico de municipios por transparencia."""
    data = load_index_data()

    # Filtrar
    filtered = data
    if province:
        filtered = [m for m in filtered if m.get("provincia", "").lower() == province.lower()]
    if min_pop is not None:
        filtered = [m for m in filtered if m.get("poblacion", 0) >= min_pop]
    if max_pop is not None:
        filtered = [m for m in filtered if m.get("poblacion", 0) <= max_pop]

    # Ordenar
    reverse = order == "desc"
    filtered.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)

    # Limitar
    total = len(filtered)
    filtered = filtered[:limit]

    return {
        "total": total,
        "returned": len(filtered),
        "sort_by": sort_by,
        "order": order,
        "filters": {"province": province, "min_pop": min_pop, "max_pop": max_pop},
        "ranking": filtered,
    }


class WeightsModel(BaseModel):
    apertura: float = 0.30
    compras: float = 0.30
    rendicion: float = 0.20
    declaraciones: float = 0.20


@app.get("/api/weights")
async def get_weights():
    """Obtiene los pesos actuales del índice."""
    return {"weights": current_weights}


@app.post("/api/weights")
async def update_weights(weights: WeightsModel):
    """Actualiza los pesos y recalcula el ranking."""
    global current_weights

    # Validar que sumen 1.0
    total = weights.apertura + weights.compras + weights.rendicion + weights.declaraciones
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Los pesos deben sumar 1.0. Suma actual: {total:.2f}"
        )

    new_weights = {
        "apertura": weights.apertura,
        "compras": weights.compras,
        "rendicion": weights.rendicion,
        "declaraciones": weights.declaraciones,
    }
    current_weights = new_weights

    # Recalcular índice
    results = recalculate_index(new_weights)

    return {
        "weights": new_weights,
        "ranking": results[:20],  # Top 20
        "total": len(results),
    }


@app.get("/api/provinces")
async def get_provinces():
    """Lista de provincias disponibles."""
    data = load_index_data()
    provinces = sorted(set(m.get("provincia", "") for m in data if m.get("provincia")))
    return {"provinces": provinces}


@app.get("/api/stats")
async def get_stats():
    """Estadísticas generales del índice."""
    data = load_index_data()
    if not data:
        return {"error": "No hay datos disponibles"}

    indices = [m["indice_transparencia"] for m in data]
    return {
        "total_municipios": len(data),
        "indice_promedio": round(sum(indices) / len(indices), 1),
        "indice_maximo": max(indices),
        "indice_minimo": min(indices),
        "indice_mediana": sorted(indices)[len(indices) // 2],
        "year": data[0].get("year", ""),
    }


# Servir frontend estático
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
