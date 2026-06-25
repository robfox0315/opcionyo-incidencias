# 🛠️ Dashboard de Incidencias Técnicas · Opción Yo

Dashboard interactivo (Streamlit) para el **área de Incidencias Técnicas**,
solicitado por **Felipe Higuera**. Ingiere el export de HubSpot de
"problemas técnicos" y permite aislar el tema **Sin Respuesta**, rankear la
**reincidencia por contacto**, ver **KPIs/SLA** del área y cruzar con la
**telemetría de plataforma** por especialista.

> Identidad de marca: TEAL `#16B6C2` · AZUL `#2F80ED` (igual que el Dashboard ATC).

---

## ✅ Cifras validadas (corte mayo 2026)

Todas las métricas del dashboard fueron verificadas contra los datos reales
y el reporte de Felipe. Reproducen exactamente:

| Métrica | Valor |
|---|---|
| Tickets totales | **280** |
| Sin respuesta (Resolución) | **158 (56,4 %)** |
| Categoría "IT- Sin respuesta" | **112** |
| Tickets abiertos (sin cierre) | **9** |
| Tiempo medio / mediana / P90 a cierre | **98 h / 111 h / 144 h** |
| Contactos recurrentes (>1 ticket) | **34** |
| Mayor reincidente en "sin respuesta" | **(E) Diana Sánchez · 11** |
| Telemetría: especialistas / citas / % incidencia | **145 / 13.187 / 37,2 %** |

---

## 🧭 Pestañas (9)

1. **📊 Resumen** — KPIs de cabecera (tiempos **en días**), resolución, categorías,
   + resolución efectiva, % sin prioridad, concentración Pareto.
2. **🎯 Sin Respuesta** — el foco de Felipe: **tasa de fuga por categoría**, ranking
   de reincidencia por contacto (Especialista / Interno / Cliente), con descargas.
3. **🔁 Reincidencia** — recurrentes + detalle ticket a ticket por contacto.
4. **📁 Distribuciones** — Categoría, Resolución, Prioridad, Estado, Rangos de cierre.
5. **⏱️ SLA & Tiempos** — cumplimiento ANS 1ª respuesta y cierre + histograma en días.
6. **🎓 Atención a Especialistas** — cumplimiento ANS + tiempo a resolución (días),
   comparado con clientes.
7. **🔎 Explorador** — tabla filtrable + descarga CSV/Excel.
8. **📡 Telemetría** — **incidencias por tipo** (resumen), **efectividad de pruebas
   técnicas** (antes/después) y ranking de especialistas por % incidencia y métrica.
9. **💡 Insights & Recomendaciones** — lectura automática de los datos + acción
   sugerida para cada hallazgo, lista para gerencia.

**Filtros globales (barra lateral):** definición de "Sin respuesta"
(Resolución y/o Categoría), toggle *Todos vs Solo Sin Respuesta*, segmento,
prioridad y estado. Todos los tiempos se muestran **en días** (1 día = 24 h).

---

## ⚠️ Notas honestas sobre los datos (importante)

- **No se inventa el especialista** desde el texto de la descripción: en el
  0 % de los tickets aparece nombrado. Se le menciona genéricamente
  ("su especialista") o por ID numérico. Por eso la reincidencia se calcula por
  **Associated Contact**, etiquetando si es Especialista (prefijo "(E)" / correo
  @opcionyo) o Cliente externo.
- **No existe la duración real de la 1ª respuesta** en este export (la columna
  "Respondido A tiempo/Destiempo" viene vacía). La pestaña de especialistas mide
  *cumplimiento del ANS* y *tiempo total a resolución*. Para el "tarda X h en
  atender" exacto, re-exporta de HubSpot incluyendo la propiedad
  **"Tiempo hasta primera respuesta"**.
- Las celdas de **Categoría con doble valor** (separadas por `;`) se dividen al
  contar, igual que en el reporte de Felipe.

---

## 🗂️ Estructura del proyecto

```
opcionyo-incidencias/
├── app.py                         # Aplicación Streamlit (8 pestañas)
├── data_loader.py                 # Lógica de datos (pandas puro, validado)
├── requirements.txt               # Dependencias
├── README.md                      # Este archivo
├── GUIA_DESPLIEGUE_STREAMLIT.md   # Paso a paso a prueba de errores
├── .gitignore
├── .streamlit/
│   └── config.toml                # Tema de marca
└── data/
    ├── problemas_tecnicos_mayo.csv         # Muestra HubSpot (para arrancar)
    ├── incidencias_especialistas_mayo.csv  # Muestra telemetría
    └── seguimiento_pruebas_mayo.csv        # Muestra pruebas técnicas
```

El dashboard **arranca con las muestras incluidas**. Para actualizar, sube tu
export desde la barra lateral (acepta `.xlsx` y `.csv`).

---

## ▶️ Ejecutar en local (opcional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Desplegar en Streamlit Cloud

Sigue **`GUIA_DESPLIEGUE_STREAMLIT.md`** (paso a paso, sin línea de comandos).

---

## 🔒 Privacidad

Los datos incluyen nombres y correos de clientes. **Mantén el repositorio
PRIVADO.** Si no quieres versionar datos, borra la carpeta `data/` y usa solo
el cargador de archivos del dashboard.
