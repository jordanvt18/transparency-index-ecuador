# -*- coding: utf-8 -*-
"""
Script para ejecutar el pipeline ETL completo de una sola vez.
"""
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_step(description, cmd):
    print(f"\n{'='*60}")
    print(f"▶ {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=str(BASE_DIR), shell=True)
    if result.returncode != 0:
        print(f"❌ Error en: {description}")
        sys.exit(1)
    print(f"✅ Completado: {description}")

def main():
    year = 2025

    run_step("Paso 1/5: Recolección de contratos (SERCOP)", f"python scripts/ingest_procurement.py --year {year}")
    run_step("Paso 2/5: Recolección de declaraciones patrimoniales", f"python scripts/ingest_declarations.py --year {year}")
    run_step("Paso 3/5: Recolección de datos socioeconómicos (INEC + Contraloría)", f"python scripts/ingest_socioeconomic.py --year {year}")
    run_step("Paso 4/5: Cálculo de métricas municipales", f"python -m src.etl.compute_metrics --year {year}")
    run_step("Paso 5/5: Cálculo del índice de transparencia", f"python -m src.compute_transparency_index --year {year}")

    # Matching de municipios similares
    run_step("Bonus: Matching de municipios similares (KNN)", f"python -m src.compute_similar_municipios --k 5 --year {year}")

    # Tests
    run_step("Tests", f"python tests/test_index.py")

    print(f"\n{'='*60}")
    print(f"🎉 Pipeline completo! Datos en data/processed/")
    print(f"{'='*60}")

    # Copiar datos al frontend para GitHub Pages
    import shutil
    web_data = BASE_DIR / "web" / "data"
    web_data.mkdir(exist_ok=True)

    # Copiar transparency_index
    src_index = BASE_DIR / "data" / "processed" / f"transparency_index_{year}.json"
    dst_index = web_data / "transparency_index.json"
    if src_index.exists():
        shutil.copy2(src_index, dst_index)
        print(f"📄 Copiado: {dst_index}")

    # Copiar similar_municipios
    src_similar = BASE_DIR / "data" / "processed" / "similar_municipios.json"
    dst_similar = web_data / "similar_municipios.json"
    if src_similar.exists():
        shutil.copy2(src_similar, dst_similar)
        print(f"📄 Copiado: {dst_similar}")

    # Copiar contratos por municipio (para frontend estático)
    raw_sercop = BASE_DIR / "data" / "raw" / "sercop"
    for f in raw_sercop.glob(f"*_{year}_contracts.json"):
        shutil.copy2(f, web_data / f"contracts_{f.stem.replace(f'_{year}_contracts', '')}_{year}.json")
    print(f"📄 Contratos copiados al frontend")

    print(f"\n🌐 Abre web/index.html en tu navegador para ver la plataforma.")


if __name__ == "__main__":
    main()
