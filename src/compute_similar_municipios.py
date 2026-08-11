# -*- coding: utf-8 -*-
"""
Agente D — Matching de municipios similares
Usa k-nearest neighbors (scikit-learn) en espacio normalizado para encontrar
municipios similares por población, PIB per cápita, presupuesto y densidad urbana.
Guarda resultados en data/processed/similar_municipios.csv
"""
import json
import csv
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Features para emparejar municipios
MATCHING_FEATURES = [
    "poblacion",
    "pib_per_capita",
    "presupuesto",
    "densidad_urbana",
    "tasa_pobreza",
    "idh",
]


def load_metrics(year: int = None) -> list[dict]:
    """Carga métricas municipales procesadas."""
    if year is None:
        year = datetime.now().year - 1
    metrics_path = PROCESSED_DIR / f"municipal_metrics_{year}.json"
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def normalize_features(metrics_list: list[dict], features: list[str] = None) -> "tuple[list[list[float]], list[str]]":
    """Normaliza features a escala 0-1 para KNN."""
    if features is None:
        features = MATCHING_FEATURES

    # Extraer y normalizar
    raw_values = []
    for m in metrics_list:
        row = []
        for f in features:
            val = m.get(f, 0)
            if val is None:
                val = 0
            row.append(float(val))
        raw_values.append(row)

    if not raw_values:
        return [], features

    # Normalización min-max
    n_features = len(features)
    min_vals = [min(row[i] for row in raw_values) for i in range(n_features)]
    max_vals = [max(row[i] for row in raw_values) for i in range(n_features)]

    normalized = []
    for row in raw_values:
        norm_row = []
        for i in range(n_features):
            if max_vals[i] == min_vals[i]:
                norm_row.append(0.5)
            else:
                norm_row.append((row[i] - min_vals[i]) / (max_vals[i] - min_vals[i]))
        normalized.append(norm_row)

    return normalized, features


def compute_similar_municipios(metrics_list: list[dict], k: int = 5, features: list[str] = None) -> list[dict]:
    """
    Encuentra municipios similares usando KNN en espacio normalizado.

    Args:
        metrics_list: Lista de métricas municipales
        k: Número de municipios similares a encontrar (por municipio)
        features: Features para el matching

    Returns:
        Lista de diccionarios con pares de municipios similares
    """
    try:
        import numpy as np
        from sklearn.neighbors import NearestNeighbors
    except ImportError:
        print("⚠️ scikit-learn no disponible. Usando matching por distancia euclidiana manual.")
        return _manual_knn(metrics_list, k, features)

    normalized, feat_names = normalize_features(metrics_list, features)
    if not normalized:
        return []

    X = np.array(normalized)
    n = X.shape[0]
    k_actual = min(k + 1, n)  # +1 porque el municipio mismo será el más cercano

    knn = NearestNeighbors(n_neighbors=k_actual, metric="euclidean", algorithm="auto")
    knn.fit(X)

    distances, indices = knn.kneighbors(X)

    results = []
    for i, muni in enumerate(metrics_list):
        similar = []
        for j in range(1, k_actual):  # Saltar el primero (es él mismo)
            neighbor_idx = indices[i][j]
            neighbor_dist = distances[i][j]
            neighbor = metrics_list[neighbor_idx]

            similar.append({
                "municipio_id_origen": muni["municipio_id"],
                "municipio_nombre_origen": muni.get("nombre", ""),
                "municipio_id_similar": neighbor["municipio_id"],
                "municipio_nombre_similar": neighbor.get("nombre", ""),
                "distancia": round(float(neighbor_dist), 4),
                "ranking_similaridad": j,
            })

        results.extend(similar)

    return results


def _manual_knn(metrics_list: list[dict], k: int, features: list[str] = None) -> list[dict]:
    """KNN manual sin scikit-learn (fallback)."""
    import math

    if features is None:
        features = MATCHING_FEATURES

    normalized, feat_names = normalize_features(metrics_list, features)
    if not normalized:
        return []

    n = len(normalized)
    k_actual = min(k + 1, n)
    results = []

    for i, muni in enumerate(metrics_list):
        # Calcular distancias a todos los demás
        distances = []
        for j in range(n):
            if i == j:
                continue
            dist = math.sqrt(sum(
                (normalized[i][f] - normalized[j][f]) ** 2
                for f in range(len(features))
            ))
            distances.append((j, dist))

        # Ordenar por distancia
        distances.sort(key=lambda x: x[1])

        for rank, (j, dist) in enumerate(distances[:k], 1):
            neighbor = metrics_list[j]
            results.append({
                "municipio_id_origen": muni["municipio_id"],
                "municipio_nombre_origen": muni.get("nombre", ""),
                "municipio_id_similar": neighbor["municipio_id"],
                "municipio_nombre_similar": neighbor.get("nombre", ""),
                "distancia": round(dist, 4),
                "ranking_similaridad": rank,
            })

    return results


def save_similar_municipios(results: list[dict]):
    """Guarda resultados de matching en CSV y JSON."""
    if not results:
        return

    csv_path = PROCESSED_DIR / "similar_municipios.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"  ✅ CSV: {csv_path}")

    json_path = PROCESSED_DIR / "similar_municipios.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  ✅ JSON: {json_path}")


def main(k: int = 5, year: int = None):
    """Función principal."""
    if year is None:
        year = datetime.now().year - 1

    metrics_list = load_metrics(year)
    if not metrics_list:
        print("❌ No hay métricas. Ejecuta compute_metrics.py primero.")
        return

    print(f"🔄 Calculando municipios similares (k={k}) para {len(metrics_list)} municipios...")
    print(f"  Features: {MATCHING_FEATURES}")

    results = compute_similar_municipios(metrics_list, k=k)

    print(f"\n📊 Resultados: {len(results)} pares de municipios similares")
    print(f"\nEjemplos:")
    for r in results[:10]:
        print(f"  {r['municipio_nombre_origen']:20s} → {r['municipio_nombre_similar']:20s} "
              f"(dist: {r['distancia']:.3f})")

    save_similar_municipios(results)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Encuentra municipios similares")
    parser.add_argument("--k", type=int, default=5, help="Número de municipios similares")
    parser.add_argument("--year", type=int, default=None)
    args = parser.parse_args()
    main(k=args.k, year=args.year)
