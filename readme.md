# Índice de Transparencia Municipal · Ecuador 🇪🇨

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Plataforma ciudadana para construir un **Índice de Transparencia Municipal** y comparar municipios "parecidos" (por tamaño, presupuesto, indicadores socioeconómicos) para exponer diferencias en compras públicas, cumplimiento de rendición y declaraciones patrimoniales.

## 🎯 Valor Ciudadano

Permite a la ciudadanía y periodistas:
- **Comparar** desempeño en transparencia entre municipios pares
- **Detectar anomalías** en contratación pública y concentración de proveedores
- **Priorizar** vigilancia ciudadana con base en evidencia

## 📊 Componentes del Índice

| Componente | Peso | Qué mide |
|---|---|---|
| Apertura de Datos | 30% | Portal de transparencia, formatos abiertos, API, actualización |
| Compras Públicas | 30% | % licitación pública vs directa, concentración de proveedores (HHI) |
| Rendición y Auditoría | 20% | Informes publicados, recomendaciones cumplidas, sanciones |
| Declaraciones Patrimoniales | 20% | % autoridades con declaración pública, tiempo de publicación |

Cada subíndice se normaliza a 0–100. El índice final es una ponderación lineal. **Los pesos son ajustables desde la UI.**

## 🗂️ Estructura del Repositorio

```
transparency-index-ecuador/
├── scripts/                    # Pipeline ETL (Agente A)
│   ├── ingest_procurement.py   # Descarga contratos de SERCOP
│   ├── ingest_declarations.py  # Recopila declaraciones patrimoniales
│   └── ingest_socioeconomic.py # Datos INEC + auditorías Contraloría
├── src/
│   ├── etl/
│   │   └── compute_metrics.py  # Normalización y métricas (Agente B)
│   ├── compute_transparency_index.py  # Cálculo del índice (Agente C)
│   ├── compute_similar_municipios.py  # KNN matching (Agente D)
│   └── api/
│       └── main.py             # API REST (FastAPI)
├── web/                        # Frontend
│   ├── index.html
│   ├── css/styles.css
│   ├── js/app.js
│   └── data/                   # JSON estáticos para GitHub Pages
├── data/
│   ├── raw/                    # Datos crudos
│   │   ├── sercop/
│   │   ├── declarations/
│   │   ├── inec/
│   │   └── contraloria/
│   └── processed/              # Métricas e índices calculados
├── notebooks/                  # Análisis exploratorio
├── tests/                      # Pruebas
├── docs/                       # Documentación adicional
├── METHODOLOGY.md              # Metodología detallada
├── DATA_LICENSE.md             # Licencia y fuentes de datos
├── requirements.txt
└── README.md
```

## 🚀 Instalación y Uso

### 1. Clonar
```bash
git clone https://github.com/jordanvt18/transparency-index-ecuador.git
cd transparency-index-ecuador
```

### 2. Entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 3. Ejecutar pipeline ETL
```bash
# Paso 1: Recolectar datos (genera datos sintéticos si el API no responde)
python scripts/ingest_procurement.py --year 2025
python scripts/ingest_declarations.py --year 2025
python scripts/ingest_socioeconomic.py --year 2025

# Paso 2: Calcular métricas
python -m src.etl.compute_metrics --year 2025

# Paso 3: Calcular índice de transparencia
python -m src.compute_transparency_index --year 2025

# Paso 4: Encontrar municipios similares
python -m src.compute_similar_municipios --k 5 --year 2025
```

### 4. Iniciar API
```bash
uvicorn src.api.main:app --reload --port 8000
```

### 5. Abrir frontend
Abre `web/index.html` en tu navegador, o visita `http://localhost:8000` (la API sirve el frontend).

## 📡 API Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/ranking` | Ranking dinámico con filtros (provincia, población) |
| GET | `/api/municipio/{id}/transparency` | Índice y subíndices de un municipio |
| GET | `/api/municipio/{id}/similar` | Municipios similares con distancias |
| GET | `/api/municipio/{id}/contracts?year=` | Contratos filtrados |
| GET | `/api/weights` | Pesos actuales del índice |
| POST | `/api/weights` | Actualizar pesos y recalcular |
| GET | `/api/provinces` | Lista de provincias |
| GET | `/api/stats` | Estadísticas generales |

## 🗺️ Visualizaciones

- **Mapa coroplético**: color por índice de transparencia; tooltip con subíndices
- **Ranking interactivo**: ordenar por índice, filtrar por provincia y tamaño
- **Comparador de municipios similares**: small multiples con sparklines de compras, barras de subíndices, tabla de diferencias
- **Detalle de contratos**: tabla filtrable con enlaces a documentos fuente
- **Panel de ajuste de pesos**: sliders para cambiar pesos y ver cómo varía el ranking en tiempo real

## 📋 Fuentes de Datos

| Fuente | Tipo de datos | URL |
|---|---|---|
| SERCOP | Contratos y compras públicas | https://www.compraspublicas.gob.ec |
| Contraloría General del Estado | Auditorías y sanciones | https://www.contraloria.gob.ec |
| INEC | Indicadores socioeconómicos | https://www.ecuadorencifras.gob.ec |
| Portales de transparencia municipal | Declaraciones patrimoniales | Variables por municipio |

## ⚖️ Consideraciones Éticas y Legales

- **Datos incompletos**: se documentan vacíos; no se imputan sin evidencia
- **Privacidad**: datos personales sensibles son anonimizados
- **Difamación**: no se publican acusaciones; se enlaza a documentos oficiales
- **Disclaimer**: incluye guía para periodistas/ciudadanos sobre interpretación del índice

## 📈 Roadmap

- **MVP (3 semanas)**: Índice calculado para 50 municipios con datos de compras y comparador básico
- **v1 (8 semanas)**: Cobertura nacional, UI completa, endpoints, tests y documentación

## 📄 Licencia

MIT License — ver [LICENSE](LICENSE)

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor abre un issue o pull request en https://github.com/jordanvt18/transparency-index-ecuador
