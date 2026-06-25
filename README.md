# **Hub de Gestión de Plantillas y Análisis de Datos mediante Estadística Avanzada (Temporada 2025-26)**

**Trabajo Final de Máster** centrado en el *scouting* y la gestión de plantillas de un club de fútbol. El proyecto recorre todo el ciclo del dato: recopila la información de una temporada entera, la refina a través de una **arquitectura medallón** (*bronze* → *silver* → *gold*) y la expone en una **aplicación web interactiva** que ayuda a un club a fichar, planificar y decidir con base estadística.

---

**Autor:** Xavier Rosinach Capell - *Sports Data Scientist & AI Engineer*
**Formación:** Máster en Big Data Deportivo — Universidad Europea, Escuela Universitaria Real Madrid

---

## **Arquitectura de datos (estilo Medallón)**

El flujo de datos sigue el patrón **Medallón**, en el que la información avanza por capas y gana calidad y estructura en cada paso.

### **1. Scraping**

Extracción de los datos en bruto desde dos fuentes:

- **Sofascore** — estadísticas detalladas de partido y de jugador (eventos, mapas de pases y tiros, métricas avanzadas, alineaciones, etc.).
- **Scoresway** — información de contexto y estadísticas detalladas de partido y de jugador (partidos, competiciones, plantillas, datos de clubes y jugadores).

El resultado son ficheros crudos (en formato ``json``), sin limpiar y con formatos heterogéneos según el origen.

### **2. Capa Bronze — unificación de datos**

Primera capa de consolidación. Aquí los datos de ambas fuentes se **unifican** en un esquema común: se cruzan jugadores, equipos y partidos entre Sofascore y Scoresway, se homogeneizan identificadores, nombres y formatos, y se resuelven duplicados e inconsistencias. La capa bronze es la "fuente única de verdad" sobre la que se construye todo lo demás, todavía cercana al dato original.

### **3. Capa Silver — extracción de métricas a partir de los estudios**

Capa de **transformación analítica**. Sobre los datos unificados se aplican los estudios estadísticos que convierten los datos brutos en métricas con significado deportivo. Cada estudio está documentado en la carpeta [`studies/`](studies/):

1. **Ranking Elo de clubes** ([`studies/1_club_elo`](studies/1_club_elo)) — valoración dinámica de la fuerza de cada equipo, actualizada partido a partido según resultado, rival y margen de goles.
2. **Roles de jugador** ([`studies/2_player_roles`](studies/2_player_roles)) — perfil de juego de cada futbolista mediante PCA + *clustering* (K-means) dentro de su posición.
3. **Índice de similitud** ([`studies/3_similarity_score`](studies/3_similarity_score)) — parecido entre jugadores (y entre equipos) por *cosine similarity* sobre sus perfiles estadísticos.
4. **Rating y potencial** ([`studies/4_player_ratings`](studies/4_player_ratings)) — nota por partido (0–10) ajustada por contexto, agregada en el tiempo y mapeada a un Rating (65–95) y un Potential (65–99).
5. **Adaptabilidad a un club** ([`studies/5_player_adaptability`](studies/5_player_adaptability)) — cómo de bien encajaría un jugador en un club concreto (estilo, plantilla, contexto), expresado en porcentaje y estrellas (0–5).

### **4. Capa Gold — preparación y publicación en la nube**

Capa final orientada al **consumo**. Las métricas de la capa silver se preparan en el formato exacto que necesita la aplicación: objetos por entidad (`entities/{tipo}/{id}.json`), listas (`info/`), ficheros de comparación y de imágenes (escudos, fotos, banderas). Estos ficheros se suben a un *bucket* en la nube (**Cloudflare R2**), de modo que el HTML pueda leerlos directamente vía HTTP, de forma rápida y sin servidor propio. Así la web funciona como una página estática que consume datos ya cocinados.

```
Scraping (Sofascore + Scoresway)
        │
        ▼
   Bronze  ──  unificación de fuentes en un esquema común
        │
        ▼
   Silver  ──  estudios estadísticos → métricas avanzadas
        │
        ▼
    Gold   ──  datos listos para consumo + subida a Cloudflare R2
        │
        ▼
   Aplicación web (lee los JSON desde la nube)
```

---

## **La aplicación web**

La aplicación ([`app/app.html`](app/app.html)) es una página estática (HTML + JavaScript, con Apache ECharts para los gráficos) que lee los datos publicados en la nube. Está construida en torno a un club y permite navegar por su entorno deportivo.

**Vistas de equipo:**

- **Resumen del club** — identidad, Elo, fundación, entrenador y evolución reciente de la diferencia de goles.
- **Estadísticas** — métricas agregadas del equipo en la temporada.
- **Plantilla** — jugadores con su rating, potencial, posiciones, nacionalidades y valor de mercado.
- **Equipos similares** — clubes con un perfil de juego parecido.
- **Búsqueda de jugadores** — buscador con filtros (posición, edad, rating, etc.) para encontrar perfiles concretos.

**Ficha de jugador:**

- Datos personales, **rating** y **potencial**, posiciones y **rol** de juego, y **adaptabilidad** al club.
- Visualizaciones avanzadas: **mapa de calor de pases**, **mapa de tiros** y **vista de portería**, **evolución del rating** por partido, **radares de percentiles** por posición y **scatter** de comparación de métricas.
- **Jugadores similares** para identificar alternativas o recambios.

**Estudios estadísticos** — un apartado *Statistical studies* explica, con fórmulas, cómo se calcula cada métrica avanzada, para que los números sean transparentes y auditables.

---

## **¿Por qué es útil para un club en el periodo de *scouting*?**

Durante una ventana de fichajes, un club necesita decidir **a quién fichar, a quién renovar y a quién dejar salir**, normalmente con poco tiempo y mucha información dispersa. Esta herramienta aporta valor porque:

- **Centraliza la información** de toda la temporada en un único lugar, ya procesada y lista para consultar.
- **Objetiva las decisiones**: el rating, el potencial, los roles y la similitud se derivan de los datos, no de impresiones, y todas las fórmulas están documentadas.
- **Acelera el *scouting***: el buscador con filtros y la similitud entre jugadores permiten pasar de miles de futbolistas a una *shortlist* manejable de candidatos comparables al perfil buscado.
- **Evalúa el encaje, no solo el nivel**: el índice de adaptabilidad estima si un jugador encajaría en el **estilo y la plantilla** concretos del club, reduciendo el riesgo de fichajes que no se adaptan.
- **Apoya la planificación de plantilla**: combinar rating actual + potencial + edad ayuda a equilibrar rendimiento inmediato y proyección futura, clave para construir un proyecto a medio plazo.

En conjunto, convierte un volumen enorme de datos brutos en una herramienta de decisión clara para la dirección deportiva.

---

## **Estructura del repositorio**

```
.
├── proc_data_code/             # Código del procesado de datos (pipeline medallón)
│   ├── scraping/               # 1 · Scraping de Sofascore y Scoresway
│   ├── bronze/                 # 2 · Capa Bronze — unificación de las fuentes
│   ├── silver/                 # 3 · Capa Silver — limpieza, agregación y estudios (Elo, roles, rating…)
│   ├── gold/                   # 4 · Capa Gold — preparación, similitud, adaptabilidad y subida a R2
│   ├── use/                    # Carpeta de apoyo al procesado de datos (configuración y funciones)
│   └── main.py                 # Orquestador del pipeline
├── studies/                    # Estudios estadísticos (notebooks + documentación con fórmulas)
│   ├── 1_club_elo/
│   │   ├── elo_ranking_model.ipynb
│   │   ├── elo_proceso.md
│   │   └── utils/              # Carpeta de apoyo al procesado de datos
│   ├── 2_player_roles/
│   │   ├── position_profiles.ipynb
│   │   ├── roles_proceso.md
│   │   ├── utils/              # Carpeta de apoyo al procesado de datos
│   │   └── results/            # Roles resultantes y visualizaciones
│   ├── 3_similarity_score/
│   │   ├── similarity_score.ipynb
│   │   └── similarity_proceso.md
│   ├── 4_player_ratings/
│   │   ├── player_rating_calculator.ipynb
│   │   └── ratings_proceso.md
│   └── 5_player_adaptability/
│       ├── player_suitability.ipynb
│       ├── adaptability_proceso.md
├── app/
│   ├── app.html                # Aplicación web (página principal)
│   └── visualizations/         # Módulos JS de las visualizaciones (Apache ECharts)
└── README.md
```

---

## **Tecnologías**

- **Python** (pandas, scikit-learn) para el *scraping*, el procesado por capas y los estudios.
- **JavaScript** + **Apache ECharts** para las visualizaciones interactivas.
- **KaTeX** para renderizar las fórmulas en la web.
- **Cloudflare R2** como almacenamiento en la nube de los datos servidos a la aplicación.

---
