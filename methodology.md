# Metodología del Índice de Transparencia Municipal · Ecuador

## 1. Objetivo

Construir un índice compuesto (0–100) que mida el nivel de transparencia de los gobiernos municipales del Ecuador, permitiendo comparaciones entre municipios con características socioeconómicas similares.

## 2. Componentes del Índice

### 2.1 Apertura de Datos (30%)

| Indicador | Puntos | Descripción |
|---|---|---|
| Portal de transparencia | 30 | Existencia de un portal web de transparencia activo |
| Formatos abiertos | 25 | Disponibilidad de datos en CSV, JSON, XLS (no solo PDF) |
| API pública | 25 | Existencia de una API para acceso programático a datos |
| Datos actualizados | 20 | Datos actualizados dentro del último año |

**Fuente**: Verificación directa de portales municipales.

### 2.2 Compras Públicas (30%)

| Indicador | Puntos | Descripción |
|---|---|---|
| % Licitación pública | 40 | Porcentaje de contratos por licitación pública (mayor = mejor) |
| % Contratación directa | 30 | Porcentaje de adjudicación directa (menor = mejor) |
| HHI proveedores | 30 | Índice de Herfindahl-Hirschman de concentración de proveedores (menor = mejor) |

**Fuente**: SERCOP — Servicio Nacional de Contratación Pública.

**Cálculo del HHI**:
```
HHI = Σ (s_i × 100)²
```
Donde `s_i` es la participación del proveedor `i` en el total de contratos. HHI = 0 indica competencia perfecta; HHI = 10,000 indica monopolio.

### 2.3 Rendición y Auditoría (20%)

| Indicador | Puntos | Descripción |
|---|---|---|
| % Informes publicados | 40 | Porcentaje de auditorías con informe público |
| % Recomendaciones cumplidas | 40 | Cumplimiento de recomendaciones de auditorías anteriores |
| Ausencia de sanciones | 20 | Sin sanciones de la Contraloría (cada sanción: -5 pts) |

**Fuente**: Contraloría General del Estado.

### 2.4 Declaraciones Patrimoniales (20%)

| Indicador | Puntos | Descripción |
|---|---|---|
| % Autoridades con declaración | 60 | Porcentaje de autoridades con declaración pública |
| Tiempo de publicación | 40 | Días entre inicio del año y publicación (0 días = 40 pts; 180+ días = 0 pts) |

**Fuente**: Portales de transparencia municipal / Contraloría.

## 3. Normalización

Cada subíndice se normaliza a una escala de 0 a 100. El índice final es una ponderación lineal:

```
Índice = (Apertura × w₁) + (Compras × w₂) + (Rendición × w₃) + (Declaraciones × w₄)
```

Donde `w₁ + w₂ + w₃ + w₄ = 1.0`. Los pesos por defecto son 0.30, 0.30, 0.20, 0.20.

**Los pesos son ajustables por el usuario** desde la interfaz, permitiendo explorar cómo cambian los rankings con diferentes prioridades.

## 4. Matching de Municipios Similares

Para comparar municipios "parecidos", se utiliza el algoritmo **k-nearest neighbors (KNN)** con distancia euclidiana sobre un espacio normalizado (min-max scaling, 0–1) de las siguientes features:

| Feature | Fuente |
|---|---|
| Población | INEC |
| PIB per cápita | INEC / Banco Central |
| Presupuesto municipal | Ministerio de Finanzas |
| Densidad urbana | INEC |
| Tasa de pobreza | INEC |
| IDH cantonal | PNUD / INEC |

Se encuentran los **5 municipios más similares** por cada municipio. La distancia se reporta como métrica de similaridad.

## 5. Pipeline ETL

```
scripts/ingest_procurement.py     → data/raw/sercop/
scripts/ingest_declarations.py    → data/raw/declarations/
scripts/ingest_socioeconomic.py   → data/raw/inec/ + data/raw/contraloria/
        ↓
src/etl/compute_metrics.py        → data/processed/municipal_metrics_{year}.json
        ↓
src/compute_transparency_index.py → data/processed/transparency_index_{year}.json
        ↓
src/compute_similar_municipios.py → data/processed/similar_municipios.json
```

## 6. Reproducibilidad

El pipeline completo es reproducible ejecutando los scripts en orden. Cuando las fuentes públicas no están disponibles (APIs caídas, portales sin datos), el sistema genera datos sintéticos realistas para demostración, claramente etiquetados.

## 7. Limitaciones

1. **Cobertura**: No todos los municipios publican datos completos
2. **Calidad**: Los formatos varían entre municipios
3. **Temporalidad**: Los datos pueden tener rezagos de publicación
4. **Comparabilidad**: Definiciones de "modalidad de contratación" pueden variar

## 8. Consideraciones Éticas

- **No es una acusación**: El índice mide transparencia, no corrupción. Un índice bajo indica opacidad, no necesariamente ilegalidad.
- **Datos personales**: Las declaraciones patrimoniales se anonimizan; no se publican datos personales sensibles.
- **Vínculo a fuentes**: Todos los datos enlazan a documentos oficiales verificables.
- **Actualización**: El índice debe actualizarse periódicamente para mantener relevancia.
