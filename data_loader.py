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
    Carga el export de HubSpot (xlsx o csv) y devuelve un DataFrame
    enriquecido con columnas derivadas.

    `origen` puede ser una ruta (str/Path) o un objeto file-like
    (lo que devuelve st.file_uploader).
    """
    df = _leer_tabla(origen)
    df = _mapear_columnas(df)

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
    df["horas_cierre"] = df["tiempo_cierre"].apply(_horas_desde_hms)
    if "fecha_cierre" in df.columns:
        df["fecha_cierre"] = pd.to_datetime(df["fecha_cierre"], errors="coerce")

    # --- bandera SIN RESPUESTA (doble criterio) ---
    resol = df["resolucion"].astype(str).str.strip().str.lower()
    cat = df["categoria"].astype(str).str.lower()
    df["sr_resolucion"] = resol.eq("sin respuesta")
    df["sr_categoria"] = cat.str.contains("sin respuesta", na=False)
    df["sin_respuesta"] = df["sr_resolucion"] | df["sr_categoria"]

    # --- escalado a IT ---
    # Titular = estado "Escalar a IT" (3). "Cerrado por IT" (1) se ve aparte
    # en la distribución de Estado para no mezclar definiciones.
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
    Carga la telemetría por especialista.

    - Si recibe el CSV de muestra (data/incidencias_especialistas_mayo.csv),
      lo lee directo.
    - Si recibe el Excel completo de Felipe, lee la hoja '📋 Mayo - Todos'
      cuyo encabezado está en la fila índice 1.
    """
    nombre = getattr(origen, "name", str(origen)).lower()
    if nombre.endswith((".xlsx", ".xls")):
        df = pd.read_excel(origen, sheet_name="📋 Mayo - Todos", header=1)
    else:
        df = _leer_tabla(origen)

    df = df.dropna(how="all")
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


def df_a_excel_bytes(df: pd.DataFrame, hoja: str = "Datos") -> bytes:
    """Serializa un DataFrame a bytes de Excel (para descarga)."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=hoja[:31])
    return buffer.getvalue()
