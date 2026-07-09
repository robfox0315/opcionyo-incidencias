"""
data_loader.py
------------------------------------------------------------------
Lógica de carga y transformación de datos para el Dashboard de
Incidencias Técnicas de Opción Yo.

IMPORTANTE: este módulo NO depende de Streamlit. Es pandas puro, para
poder validarlo de forma independiente contra los datos reales.

Autor: NOVA / Roberto Ortega
"""
from __future__ import annotations

import io
import re
import unicodedata
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# 1. NORMALIZACIÓN Y DETECCIÓN DE COLUMNAS
# ----------------------------------------------------------------------
# Mapa de nombres canónicos internos -> posibles encabezados del export
# de HubSpot. Se hace match insensible a tildes/mayúsculas/espacios, por
# si HubSpot cambia ligeramente el nombre en un export futuro.
COLUMNAS_CANONICAS = {
    "ticket_id":      ["ticket id", "id del ticket"],
    "nombre":         ["nombre del ticket"],
    "contacto":       ["associated contact", "contacto asociado"],
    "descripcion":    ["descripcion del ticket", "descripción del ticket"],
    "prioridad":      ["prioridad"],
    "estado":         ["estado del ticket"],
    "fecha_cierre":   ["fecha de cierre"],
    "ans_cierre":     ["estado de ans de tiempo hasta cierre"],
    "tiempo_cierre":  ["tiempo entre la creacion y el cierre (hh:mm:ss)",
                       "tiempo entre la creación y el cierre (hh:mm:ss)"],
    "respondido":     ["respondido a tiempo o a destiempo"],
    "resolucion":     ["resolucion", "resolución"],
    "categoria":      ["categoria", "categoría"],
    "ans_primera":    ["estado de ans de tiempo hasta primera respuesta"],
    "rango_cierre":   ["rangos de tiempo a cierre de ticket"],
    "contacto_ids":   ["associated contact ids"],
    "fecha_creacion": ["fecha de creacion", "fecha de creación"],
    "propietario":    ["propietario del ticket", "ticket owner"],
    "pipeline":       ["pipeline"],
    "fuente":         ["fuente", "source"],
}


def _slug(texto: str) -> str:
    """minúsculas, sin tildes, espacios colapsados -> para comparar headers."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()


def _mapear_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra las columnas del export al esquema canónico interno."""
    inverso = {}
    cols_slug = {_slug(c): c for c in df.columns}
    for canon, posibles in COLUMNAS_CANONICAS.items():
        for p in posibles:
            if p in cols_slug:
                inverso[cols_slug[p]] = canon
                break
    return df.rename(columns=inverso)


# ----------------------------------------------------------------------
# 2. UTILIDADES DE PARSEO
# ----------------------------------------------------------------------
def _extraer_email(texto) -> str | None:
    m = re.search(r"\(([^)]+@[^)]+)\)", str(texto))
    return m.group(1).strip().lower() if m else None


def _nombre_limpio(texto) -> str:
    """'(E) Diana Sánchez (mail@x.com)' -> 'Diana Sánchez'."""
    s = str(texto)
    s = re.sub(r"\([^)]*@[^)]*\)", "", s)   # quita el email entre paréntesis
    s = re.sub(r"^\s*\(E\)\s*", "", s)       # quita el prefijo (E)
    return s.strip()


def _horas_desde_hms(x) -> float:
    """'101:12:32' -> 101.21 horas (admite HH>24)."""
    if pd.isna(x):
        return np.nan
    p = str(x).strip().split(":")
    if len(p) != 3:
        return np.nan
    try:
        return int(p[0]) + int(p[1]) / 60 + int(p[2]) / 3600
    except ValueError:
        return np.nan


# ----------------------------------------------------------------------
# 3. CARGA PRINCIPAL: TICKETS DE HUBSPOT
# ----------------------------------------------------------------------
def cargar_tickets(origen) -> pd.DataFrame:
    """
    Carga el export de HubSpot (xlsx o csv) desde archivo y lo enriquece.
    `origen` puede ser ruta o file-like (st.file_uploader).
    """
    df = _leer_tabla(origen)
    return enriquecer_tickets(df)


def enriquecer_tickets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Toma un DataFrame de tickets (venga de archivo o de la API de HubSpot),
    normaliza nombres de columna y agrega TODAS las columnas derivadas.
    Es el punto único de verdad: archivo y API pasan por aquí, garantizando
    que los KPIs se calculen igual sin importar la fuente.
    """
    df = _mapear_columnas(df)

    # --- VALIDACIÓN: ¿trae las columnas base? ---
    if "contacto" not in df.columns and "resolucion" not in df.columns:
        cols_orig = ", ".join(str(c) for c in df.columns[:8])
        raise ValueError(
            "Los datos NO tienen las columnas de 'problemas técnicos' "
            "(faltan 'Associated Contact', 'Resolución', 'Descripción'…). "
            "Si es un archivo, exporta la vista de 'problemas técnicos'. "
            f"Columnas detectadas: {cols_orig}…"
        )

    # --- SEGURIDAD: crear columnas ausentes como vacías ---
    for col in ["contacto", "descripcion", "prioridad", "estado", "fecha_cierre",
                "ans_cierre", "tiempo_cierre", "respondido", "resolucion",
                "categoria", "ans_primera", "rango_cierre", "contacto_ids"]:
        if col not in df.columns:
            df[col] = np.nan

    # --- columnas derivadas de contacto ---
    df["email"] = df["contacto"].apply(_extraer_email)
    df["nombre_contacto"] = df["contacto"].apply(_nombre_limpio)
    df["es_interno"] = df["email"].str.contains("opcionyo", na=False)
    df["es_especialista"] = (
        df["contacto"].astype(str).str.strip().str.startswith("(E)")
    )

    def _segmento(row):
        if row["es_especialista"]:
            return "Especialista"
        if row["es_interno"]:
            return "Interno / Staff"
        return "Cliente externo"

    df["segmento"] = df.apply(_segmento, axis=1)

    # --- tiempos ---
    # Preferimos el tiempo numérico real (viene de la API en ms). Si no está,
    # parseamos el string HH:mm:ss del export.
    if "ms_cierre" in df.columns and pd.to_numeric(df["ms_cierre"], errors="coerce").notna().any():
        df["horas_cierre"] = pd.to_numeric(df["ms_cierre"], errors="coerce") / 3_600_000
    else:
        df["horas_cierre"] = df["tiempo_cierre"].apply(_horas_desde_hms)

    # Tiempo REAL de primera respuesta (solo disponible vía API: ms_primera_resp)
    if "ms_primera_resp" in df.columns:
        df["horas_primera_respuesta"] = pd.to_numeric(df["ms_primera_resp"], errors="coerce") / 3_600_000
    else:
        df["horas_primera_respuesta"] = np.nan

    if "fecha_cierre" in df.columns:
        # utc=True unifica tz-aware (HubSpot '…Z') y naive (CSV); tz_localize(None)
        # las deja SIN zona horaria (Excel/openpyxl no soporta fechas con tz).
        df["fecha_cierre"] = pd.to_datetime(
            df["fecha_cierre"], errors="coerce", utc=True).dt.tz_localize(None)
    if "fecha_creacion" in df.columns:
        df["fecha_creacion"] = pd.to_datetime(
            df["fecha_creacion"], errors="coerce", utc=True).dt.tz_localize(None)

    # --- bandera SIN RESPUESTA (doble criterio) ---
    resol = df["resolucion"].astype(str).str.strip().str.lower()
    cat = df["categoria"].astype(str).str.lower()
    df["sr_resolucion"] = resol.eq("sin respuesta")
    df["sr_categoria"] = cat.str.contains("sin respuesta", na=False)
    df["sin_respuesta"] = df["sr_resolucion"] | df["sr_categoria"]

    # --- escalado a IT ---
    est = df["estado"].astype(str).str.lower()
    df["escalado_it"] = est.str.contains("escalar a it")
    df["it_involucrado"] = est.str.contains("escalar a it") | est.str.contains("cerrado por it")

    # --- abierto / cerrado ---
    df["cerrado"] = df["fecha_cierre"].notna()

    return df


def _leer_tabla(origen) -> pd.DataFrame:
    """Lee xlsx o csv desde ruta o file-like, detectando el formato."""
    nombre = getattr(origen, "name", str(origen)).lower()
    if nombre.endswith((".xlsx", ".xls")):
        return pd.read_excel(origen, sheet_name=0)
    # CSV: probamos utf-8-sig y luego latin-1
    if hasattr(origen, "read"):
        data = origen.read()
        if isinstance(data, bytes):
            buffer = io.BytesIO(data)
            try:
                return pd.read_csv(buffer, encoding="utf-8-sig")
            except UnicodeDecodeError:
                buffer.seek(0)
                return pd.read_csv(buffer, encoding="latin-1")
        return pd.read_csv(io.StringIO(data))
    try:
        return pd.read_csv(origen, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(origen, encoding="latin-1")


# ----------------------------------------------------------------------
# 4. CARGA SECUNDARIA: TELEMETRÍA DE ESPECIALISTAS
# ----------------------------------------------------------------------
METRICAS_TELEMETRIA = [
    "Conn. loss", "Err. Chime", "Audio/Video",
    "Reloads", "Métricas red", "Errores JS",
]


def cargar_especialistas(origen, es_excel_origen: bool = False) -> pd.DataFrame:
    """
    Carga la telemetría por especialista de forma ROBUSTA.

    - Si es Excel, busca la hoja '📋 Mayo - Todos' (o cualquiera que contenga
      'todos'); si no la encuentra, intenta la primera hoja.
    - Si el archivo no corresponde (p. ej. se subió el export de HubSpot por
      error), lanza un ValueError CLARO en español que la app muestra como
      aviso, en lugar de romperse.
    """
    nombre = getattr(origen, "name", str(origen)).lower()
    if nombre.endswith((".xlsx", ".xls")):
        try:
            xls = pd.ExcelFile(origen)
        except Exception as e:
            raise ValueError("No pude abrir el archivo Excel del reporte de "
                             "especialistas.") from e
        hoja = next((s for s in xls.sheet_names if "todos" in str(s).lower()), None)
        df = pd.read_excel(xls, sheet_name=hoja if hoja else 0, header=1)
    else:
        df = _leer_tabla(origen)

    df = df.dropna(how="all")

    if "Especialista" not in df.columns:
        raise ValueError(
            "El archivo subido no parece el 'Reporte de especialistas' "
            "(no encontré la hoja '📋 Mayo - Todos' ni la columna 'Especialista'). "
            "¿Subiste por error el export de HubSpot en este cargador? "
            "Aquí va el reporte de especialistas, no el de tickets."
        )

    df = df[df["Especialista"].notna()].copy()

    for c in METRICAS_TELEMETRIA:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].replace("-", 0).replace("–", 0), errors="coerce"
            ).fillna(0)

    for c in ["Total Citas", "Citas c/ Inc.", "Citas Sin Inc."]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "% Inc." in df.columns:
        df["% Inc."] = pd.to_numeric(df["% Inc."], errors="coerce")

    return df.reset_index(drop=True)


# ----------------------------------------------------------------------
# 5. KPIs Y AGREGACIONES
# ----------------------------------------------------------------------
def kpis_generales(df: pd.DataFrame) -> dict:
    """KPIs de cabecera sobre el DataFrame (ya filtrado o completo)."""
    total = len(df)
    sr = int(df["sin_respuesta"].sum())
    horas = df["horas_cierre"]
    horas_validas = horas[horas > 0]  # excluye 00:00:00, igual que Felipe

    return {
        "total": total,
        "sin_respuesta": sr,
        "pct_sin_respuesta": (sr / total * 100) if total else 0,
        "cerrados": int(df["cerrado"].sum()),
        "abiertos": int((~df["cerrado"]).sum()),
        "horas_media": horas_validas.mean() if len(horas_validas) else np.nan,
        "horas_mediana": horas_validas.median() if len(horas_validas) else np.nan,
        "horas_p90": horas_validas.quantile(0.9) if len(horas_validas) else np.nan,
        "escalados_it": int(df["escalado_it"].sum()),
        "recurrentes": int((df["contacto"].value_counts() > 1).sum()),
    }


def distribucion(df: pd.DataFrame, columna: str, split_categoria: bool = False) -> pd.DataFrame:
    """
    Conteo + % por valor de una columna. Si split_categoria=True, separa las
    celdas multivalor de Categoría por ';' (replica el criterio de Felipe).
    """
    if split_categoria:
        serie = (
            df[columna].dropna().astype(str)
            .str.split(";").explode().str.strip()
        )
    else:
        serie = df[columna].fillna("Sin dato").astype(str).str.strip()

    out = serie.value_counts().rename_axis(columna).reset_index(name="Tickets")
    out["% de tickets"] = (out["Tickets"] / out["Tickets"].sum() * 100).round(1)
    return out


def ranking_reincidencia(df: pd.DataFrame, solo_sin_respuesta: bool = True) -> pd.DataFrame:
    """
    Ranking de contactos con mayor reincidencia. Etiqueta cada contacto como
    Especialista / Interno / Cliente externo. NO inventa nombres de especialista.
    """
    base = df[df["sin_respuesta"]] if solo_sin_respuesta else df
    g = (
        base.groupby(["nombre_contacto", "email", "segmento"], dropna=False)
        .size().reset_index(name="Tickets")
        .sort_values("Tickets", ascending=False)
        .reset_index(drop=True)
    )
    g.insert(0, "#", g.index + 1)
    g = g.rename(columns={
        "nombre_contacto": "Contacto", "email": "Email", "segmento": "Tipo",
    })
    return g


def horas_a_dias(h: float) -> float:
    """Convierte horas a días (1 día = 24 h)."""
    return np.nan if pd.isna(h) else h / 24.0


def tasa_sin_respuesta_por_categoria(df: pd.DataFrame, min_tickets: int = 5) -> pd.DataFrame:
    """% de 'sin respuesta' dentro de cada categoría (separa multivalor ';')."""
    cat = df.assign(cat=df["categoria"].astype(str).str.split(";")).explode("cat")
    cat["cat"] = cat["cat"].str.strip()
    g = (cat.groupby("cat")
         .agg(Tickets=("ticket_id", "size"), Sin_resp=("sin_respuesta", "sum"))
         .reset_index())
    g = g[g["Tickets"] >= min_tickets].copy()
    g["% sin respuesta"] = (g["Sin_resp"] / g["Tickets"] * 100).round(0)
    g = g.sort_values("% sin respuesta", ascending=False).reset_index(drop=True)
    return g.rename(columns={"cat": "Categoría", "Sin_resp": "Sin respuesta"})


def generar_insights(df: pd.DataFrame) -> list[dict]:
    """
    Genera insights + recomendaciones de forma dinámica desde los datos.
    Cada insight: {nivel, icono, titulo, detalle, recomendacion}.
    nivel ∈ {'critico','alerta','ok','info'}.
    """
    out = []
    total = len(df)
    if total == 0:
        return [{"nivel": "info", "icono": "ℹ️", "titulo": "Sin datos en la vista",
                 "detalle": "Los filtros actuales no devuelven tickets.",
                 "recomendacion": "Amplía los filtros en la barra lateral."}]

    k = kpis_generales(df)
    sr_pct = k["pct_sin_respuesta"]

    # 1. Sin respuesta global
    nivel = "critico" if sr_pct > 40 else "alerta" if sr_pct > 25 else "ok"
    out.append({
        "nivel": nivel, "icono": "🚫",
        "titulo": f"{sr_pct:.0f}% de los tickets cierran SIN respuesta registrada",
        "detalle": f"{k['sin_respuesta']} de {total} tickets quedan como 'sin respuesta' "
                   f"(por Resolución o Categoría).",
        "recomendacion": "Definir un protocolo de cierre: ningún ticket debería "
                         "cerrarse sin al menos una nota de respuesta. Auditar primero "
                         "las categorías con mayor tasa (ver abajo).",
    })

    # 2. Peor categoría por tasa de sin respuesta
    t = tasa_sin_respuesta_por_categoria(df, min_tickets=5)
    t = t[~t["Categoría"].str.contains("Sin respuesta", case=False, na=False)]
    if len(t):
        peor = t.iloc[0]
        out.append({
            "nivel": "critico" if peor["% sin respuesta"] > 70 else "alerta",
            "icono": "📉",
            "titulo": f"'{peor['Categoría']}': {peor['% sin respuesta']:.0f}% sin respuesta",
            "detalle": f"{int(peor['Sin respuesta'])} de {int(peor['Tickets'])} tickets de "
                       f"esa categoría cierran sin respuesta.",
            "recomendacion": "Revisar el flujo de esta categoría: ¿falta asignación, "
                             "plantilla de respuesta o seguimiento? Es la de mayor fuga.",
        })

    # 3. Mayor reincidente
    rank = ranking_reincidencia(df[df["sin_respuesta"]], solo_sin_respuesta=False)
    if len(rank):
        r0 = rank.iloc[0]
        out.append({
            "nivel": "alerta" if r0["Tickets"] >= 3 else "info", "icono": "🔁",
            "titulo": f"Mayor reincidencia en 'sin respuesta': {r0['Contacto']}",
            "detalle": f"{int(r0['Tickets'])} tickets sin respuesta · tipo: {r0['Tipo']}.",
            "recomendacion": "Contacto proactivo 1-a-1 con este caso para cortar la "
                             "reincidencia antes de que escale a churn/insatisfacción.",
        })

    # 4. Concentración de especialistas en sin respuesta
    sr = df[df["sin_respuesta"]]
    if len(sr):
        esp_pct = (sr["segmento"] == "Especialista").mean() * 100
        out.append({
            "nivel": "info", "icono": "🎓",
            "titulo": f"Los especialistas son {esp_pct:.0f}% de los tickets sin respuesta",
            "detalle": f"{int((sr['segmento']=='Especialista').sum())} de {len(sr)} "
                       f"sin respuesta provienen de especialistas internos.",
            "recomendacion": "Si la incidencia interna es alta, priorizar un canal "
                             "dedicado de soporte a especialistas (afecta sus sesiones).",
        })

    # 5. Priorización sin usar (calidad de dato)
    sin_prio = df["prioridad"].isna().mean() * 100
    media_pct = (df["prioridad"].astype(str).str.lower() == "media").mean() * 100
    if sin_prio > 10 or media_pct > 70:
        out.append({
            "nivel": "alerta", "icono": "🏷️",
            "titulo": "La priorización casi no se usa",
            "detalle": f"{media_pct:.0f}% marcados 'Media' y {sin_prio:.0f}% sin prioridad. "
                       "No hay señal de triage real.",
            "recomendacion": "Definir criterios de Urgente/Alta (p. ej. especialista en "
                             "sesión activa) para priorizar lo crítico y medir SLA por nivel.",
        })

    # 6. Resolución efectiva
    res_ok = (df["resolucion"].astype(str).str.lower() == "resuelto exitoso").mean() * 100
    out.append({
        "nivel": "alerta" if res_ok < 40 else "ok", "icono": "✅",
        "titulo": f"Tasa de resolución efectiva: {res_ok:.0f}%",
        "detalle": f"Solo {res_ok:.0f}% de los tickets se marcan 'Resuelto exitoso'.",
        "recomendacion": "Subir la resolución efectiva reduciendo el 'sin respuesta'. "
                         "Meta sugerida: >50% en el próximo corte.",
    })

    # 7. Tiempo a cierre en días
    p90_d = horas_a_dias(k["horas_p90"])
    if not pd.isna(p90_d):
        out.append({
            "nivel": "alerta" if p90_d > 5 else "ok", "icono": "⏱️",
            "titulo": f"P90 de cierre: {p90_d:.1f} días",
            "detalle": f"El 90% de los tickets cierra en ≤ {p90_d:.1f} días "
                       f"(mediana {horas_a_dias(k['horas_mediana']):.1f} d).",
            "recomendacion": "Fijar un SLA objetivo en días (p. ej. cierre ≤ 3 días) y "
                             "monitorear el P90, no solo el promedio.",
        })

    # 8. Backlog abierto
    if k["abiertos"] > 0:
        out.append({
            "nivel": "alerta" if k["abiertos"] >= 5 else "info", "icono": "📂",
            "titulo": f"{k['abiertos']} tickets abiertos sin fecha de cierre",
            "detalle": "Quedan sin cierre registrado en HubSpot.",
            "recomendacion": "Revisar y cerrar/dar seguimiento al backlog para no "
                             "distorsionar los tiempos del próximo corte.",
        })

    # 9. Concentración (Pareto)
    vc = df["contacto"].value_counts()
    top10 = vc.head(10).sum()
    out.append({
        "nivel": "info", "icono": "📊",
        "titulo": f"Top 10 contactos concentran {top10/total*100:.0f}% de los tickets",
        "detalle": f"{int(top10)} de {total} tickets provienen de 10 contactos.",
        "recomendacion": "Atacar la cola larga con acciones individuales a ese top "
                         "tiene alto retorno (regla de Pareto).",
    })

    return out


def incidencias_por_tipo(esp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Totales por tipo de incidencia técnica (suma de las 6 métricas de
    telemetría) + % del total + nº de especialistas afectados + nivel.
    Devuelve un resumen ordenado, listo para gerencia.
    """
    filas = []
    total = 0
    for m in METRICAS_TELEMETRIA:
        if m in esp_df.columns:
            ev = int(esp_df[m].sum())
            afect = int((esp_df[m] > 0).sum())
            filas.append({"Tipo": m, "Eventos": ev, "Especialistas afectados": afect})
            total += ev
    out = pd.DataFrame(filas).sort_values("Eventos", ascending=False).reset_index(drop=True)
    out["% del total"] = (out["Eventos"] / total * 100).round(1) if total else 0

    def _nivel(p):
        return "🔴 Crítico" if p >= 30 else "🟠 Alto" if p >= 10 else "🟡 Medio" if p >= 1 else "🟢 Bajo"
    out["Nivel"] = out["% del total"].apply(_nivel)
    return out


def cargar_pruebas(origen) -> pd.DataFrame:
    """Carga el seguimiento de pruebas técnicas de forma robusta."""
    nombre = getattr(origen, "name", str(origen)).lower()
    if nombre.endswith((".xlsx", ".xls")):
        xls = pd.ExcelFile(origen)
        hoja = next((s for s in xls.sheet_names if "prueba" in str(s).lower()), None)
        if hoja is None:
            raise ValueError("El Excel no tiene la hoja de 'Seguimiento de Pruebas'.")
        df = pd.read_excel(xls, sheet_name=hoja, header=3)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.rename(columns={"Resultado": "Resultado inicial",
                                "Resultado.1": "Resultado seguimiento"})
    else:
        df = _leer_tabla(origen)
    df = df.dropna(how="all")
    if "Especialista" not in df.columns:
        raise ValueError("El archivo no corresponde al seguimiento de pruebas.")
    df = df[df["Especialista"].notna()].copy()
    return df.reset_index(drop=True)


def resumen_pruebas(pr: pd.DataFrame) -> dict:
    """Métricas de efectividad del seguimiento de pruebas técnicas."""
    realizadas = int((pr.get("Estado Prueba", pd.Series(dtype=str))
                      .astype(str).str.contains("Realizada", na=False)).sum())
    ini = pr.get("Resultado inicial", pd.Series(dtype=str)).astype(str).str.strip().str.lower()
    seg = pr.get("Resultado seguimiento", pd.Series(dtype=str)).astype(str).str.strip().str.lower()
    malos = int((ini == "malo").sum())
    mejoraron = int(((ini == "malo") & (seg.str.startswith("bueno"))).sum())
    return {
        "total_registros": len(pr),
        "realizadas": realizadas,
        "result_malo": malos,
        "mejoraron": mejoraron,
        "pct_mejora": (mejoraron / malos * 100) if malos else 0,
    }


def df_a_excel_bytes(df: pd.DataFrame, hoja: str = "Datos") -> bytes:
    """Serializa un DataFrame a bytes de Excel, saneando lo que openpyxl rechaza:
    fechas con zona horaria, valores infinitos y strings demasiado largos."""
    safe = df.copy()
    for c in safe.columns:
        s = safe[c]
        # 1) fechas con zona horaria -> sin zona
        if isinstance(s.dtype, pd.DatetimeTZDtype):
            safe[c] = s.dt.tz_localize(None)
        # 2) textos (object o dtype 'str'/'string' de pandas nuevo): recortar a
        #    32.000 (límite de celda 32.767) y quitar caracteres de control
        elif s.dtype == object or pd.api.types.is_string_dtype(s):
            safe[c] = s.apply(
                lambda v: re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(v)[:32000])
                if isinstance(v, str) else v)
    # 3) infinitos -> vacío
    safe = safe.replace([np.inf, -np.inf], np.nan)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        safe.to_excel(writer, index=False, sheet_name=str(hoja)[:31])
    return buffer.getvalue()
