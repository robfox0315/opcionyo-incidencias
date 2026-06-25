"""
=====================================================================
  DASHBOARD DE INCIDENCIAS TÉCNICAS · OPCIÓN YO
  Área de Incidencias Técnicas  ·  solicitado por Felipe Higuera
---------------------------------------------------------------------
  Ingiere el export de HubSpot ("problemas técnicos") y permite:
    · Aislar tickets "Sin respuesta" (por Resolución y/o Categoría)
    · Ranking de reincidencia por contacto (Especialista vs Cliente)
    · KPIs del área, SLA, tiempos a cierre
    · Atención a especialistas (cumplimiento ANS + tiempo a resolución)
    · Cruce con telemetría de plataforma por especialista
    · Descarga de tablas filtradas (CSV / Excel)

  Identidad de marca Opción Yo:  TEAL #16B6C2  ·  AZUL #2F80ED
=====================================================================
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl

# ---------------------------------------------------------------------
# CONFIGURACIÓN GENERAL Y MARCA
# ---------------------------------------------------------------------
OY_TEAL = "#16B6C2"
OY_BLUE = "#2F80ED"
OY_DARK = "#0E2A47"
OY_GREY = "#6B7280"
OK_GREEN = "#27AE60"
WARN_RED = "#E74C3C"
WARN_AMBER = "#F39C12"

# paleta para gráficos (orden de marca)
PALETA = [OY_TEAL, OY_BLUE, "#7C4DFF", OK_GREEN, WARN_AMBER, WARN_RED,
          "#00BFA5", "#5C6BC0", "#FF8A65", "#26A69A", "#AB47BC", "#78909C"]

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_TICKETS = DATA_DIR / "problemas_tecnicos_mayo.csv"
SAMPLE_ESP = DATA_DIR / "incidencias_especialistas_mayo.csv"

st.set_page_config(
    page_title="Incidencias Técnicas · Opción Yo",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------
st.markdown(f"""
<style>
    .stApp {{ background-color: #F7FAFC; }}
    .block-container {{ padding-top: 2rem; padding-bottom: 3rem; }}
    h1, h2, h3 {{ color: {OY_DARK}; }}
    .oy-header {{
        background: linear-gradient(100deg, {OY_TEAL} 0%, {OY_BLUE} 100%);
        padding: 22px 28px; border-radius: 16px; color: white; margin-bottom: 8px;
    }}
    .oy-header h1 {{ color: white; margin: 0; font-size: 1.6rem; }}
    .oy-header p {{ color: #EAF8FA; margin: 4px 0 0 0; font-size: 0.95rem; }}
    .kpi {{
        background: white; border-radius: 14px; padding: 18px 20px;
        border: 1px solid #E5EAF0; border-left: 6px solid {OY_TEAL};
        box-shadow: 0 1px 3px rgba(16,42,71,0.06); height: 100%;
    }}
    .kpi .label {{ color: {OY_GREY}; font-size: 0.78rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: .03em; }}
    .kpi .value {{ color: {OY_DARK}; font-size: 1.9rem; font-weight: 800; line-height: 1.1; }}
    .kpi .sub {{ color: {OY_GREY}; font-size: 0.8rem; margin-top: 2px; }}
    .kpi.blue {{ border-left-color: {OY_BLUE}; }}
    .kpi.green {{ border-left-color: {OK_GREEN}; }}
    .kpi.red {{ border-left-color: {WARN_RED}; }}
    .kpi.amber {{ border-left-color: {WARN_AMBER}; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; flex-wrap: wrap; }}
    .stTabs [data-baseweb="tab"] {{ font-size: 0.9rem; }}
    .nota {{ background:#EAF8FA; border-left:4px solid {OY_TEAL};
        padding:12px 16px; border-radius:8px; font-size:0.9rem; color:{OY_DARK}; }}
    .nota.warn {{ background:#FFF4E5; border-left-color:{WARN_AMBER}; }}
</style>
""", unsafe_allow_html=True)


def kpi(label, value, sub="", color=""):
    st.markdown(
        f"""<div class="kpi {color}">
              <div class="label">{label}</div>
              <div class="value">{value}</div>
              <div class="sub">{sub}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def estilo_plot(fig, h=360):
    fig.update_layout(
        height=h, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=OY_DARK, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F6")
    return fig


# ---------------------------------------------------------------------
# CARGA DE DATOS (con cache)
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _tickets_desde_ruta(ruta: str) -> pd.DataFrame:
    return dl.cargar_tickets(ruta)


@st.cache_data(show_spinner=False)
def _esp_desde_ruta(ruta: str) -> pd.DataFrame:
    return dl.cargar_especialistas(ruta)


# ---------------------------------------------------------------------
# SIDEBAR · FUENTE DE DATOS + FILTROS
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### 🛠️ Incidencias Técnicas")
    st.caption("Opción Yo · Área de Incidencias")
    st.divider()

    st.markdown("**1 · Fuente de datos (HubSpot)**")
    subido = st.file_uploader(
        "Sube el export de HubSpot (.xlsx o .csv)",
        type=["xlsx", "xls", "csv"], key="up_tickets",
    )

    if subido is not None:
        df = dl.cargar_tickets(subido)
        st.success(f"✅ Cargado: {subido.name} ({len(df)} tickets)")
    elif SAMPLE_TICKETS.exists():
        df = _tickets_desde_ruta(str(SAMPLE_TICKETS))
        st.info(f"📄 Usando muestra incluida ({len(df)} tickets). "
                "Sube tu export para actualizar.")
    else:
        st.error("No hay datos. Sube el export de HubSpot para continuar.")
        st.stop()

    st.divider()
    st.markdown("**2 · Filtro principal · SIN RESPUESTA**")
    criterio = st.radio(
        "¿Qué cuenta como 'Sin respuesta'?",
        ["Resolución o Categoría", "Solo Resolución", "Solo Categoría"],
        help="Resolución='Sin respuesta' (158) y/o Categoría='IT- Sin respuesta' (112).",
    )
    vista = st.radio("Vista", ["Todos los tickets", "Solo Sin Respuesta"])

    st.divider()
    st.markdown("**3 · Filtros adicionales**")
    seg_sel = st.multiselect(
        "Segmento de contacto",
        sorted(df["segmento"].unique()),
        default=sorted(df["segmento"].unique()),
    )
    prio_sel = st.multiselect(
        "Prioridad",
        sorted(df["prioridad"].fillna("Sin dato").unique()),
        default=sorted(df["prioridad"].fillna("Sin dato").unique()),
    )
    est_sel = st.multiselect(
        "Estado del ticket",
        sorted(df["estado"].fillna("Sin dato").unique()),
        default=sorted(df["estado"].fillna("Sin dato").unique()),
    )

# --- recomputar bandera Sin Respuesta según criterio ---
if criterio == "Solo Resolución":
    df["sin_respuesta"] = df["sr_resolucion"]
elif criterio == "Solo Categoría":
    df["sin_respuesta"] = df["sr_categoria"]
else:
    df["sin_respuesta"] = df["sr_resolucion"] | df["sr_categoria"]

# --- aplicar filtros (excepto toggle Sin Respuesta) ---
df_filt = df[
    df["segmento"].isin(seg_sel)
    & df["prioridad"].fillna("Sin dato").isin(prio_sel)
    & df["estado"].fillna("Sin dato").isin(est_sel)
].copy()

df_sr = df_filt[df_filt["sin_respuesta"]].copy()           # solo sin respuesta
df_view = df_sr if vista == "Solo Sin Respuesta" else df_filt   # vista activa

# ---------------------------------------------------------------------
# CABECERA
# ---------------------------------------------------------------------
st.markdown(f"""
<div class="oy-header">
  <h1>🛠️ Dashboard de Incidencias Técnicas</h1>
  <p>Opción Yo · Corte Mayo 2026 · Fuente: export HubSpot "problemas técnicos"
     &nbsp;|&nbsp; Vista activa: <b>{vista}</b> &nbsp;·&nbsp; {len(df_view)} tickets en pantalla</p>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "📊 Resumen Ejecutivo",
    "🎯 Sin Respuesta",
    "🔁 Reincidencia / Contactos",
    "📁 Distribuciones",
    "⏱️ SLA & Tiempos",
    "🎓 Atención a Especialistas",
    "🔎 Explorador de Tickets",
    "📡 Telemetría Especialistas",
])

# =====================================================================
# TAB 1 · RESUMEN EJECUTIVO
# =====================================================================
with tabs[0]:
    k = dl.kpis_generales(df_view)
    c = st.columns(5)
    with c[0]: kpi("Tickets en vista", k["total"])
    with c[1]: kpi("Sin respuesta", f'{k["sin_respuesta"]}',
                    f'{k["pct_sin_respuesta"]:.1f}% del total', "red")
    with c[2]: kpi("Cerrados / Abiertos", f'{k["cerrados"]} / {k["abiertos"]}',
                    "abiertos = sin fecha de cierre", "blue")
    with c[3]: kpi("Escalados a IT", k["escalados_it"],
                    f'+{int(df_view["it_involucrado"].sum())-k["escalados_it"]} cerrados por IT', "amber")
    with c[4]: kpi("Contactos recurrentes", k["recurrentes"], "con >1 ticket")

    c = st.columns(4)
    with c[0]: kpi("Tiempo medio a cierre", f'{k["horas_media"]:.0f} h',
                    "excluye cierres 00:00:00", "blue")
    with c[1]: kpi("Mediana a cierre", f'{k["horas_mediana"]:.0f} h', "más robusta")
    with c[2]: kpi("P90 a cierre", f'{k["horas_p90"]:.0f} h', "90% cerró por debajo")
    ans_ok = (df_view["ans_cierre"].astype(str).str.lower()
              .eq("ans completado a tiempo").sum())
    ans_tot = df_view["ans_cierre"].notna().sum()
    with c[3]: kpi("ANS cierre a tiempo",
                    f'{(ans_ok/ans_tot*100) if ans_tot else 0:.0f}%',
                    f'{ans_ok} de {ans_tot} con dato', "green")

    st.markdown("####")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Resolución de los tickets**")
        d = dl.distribucion(df_view, "resolucion")
        fig = px.pie(d, names="resolucion", values="Tickets", hole=0.55,
                     color_discrete_sequence=PALETA)
        fig.update_traces(textinfo="percent+label", textposition="outside")
        st.plotly_chart(estilo_plot(fig), use_container_width=True)
    with g2:
        st.markdown("**Top categorías (multivalor separado por ';')**")
        d = dl.distribucion(df_view, "categoria", split_categoria=True).head(10)
        fig = px.bar(d.sort_values("Tickets"), x="Tickets", y="categoria",
                     orientation="h", color_discrete_sequence=[OY_TEAL], text="Tickets")
        st.plotly_chart(estilo_plot(fig), use_container_width=True)

    st.markdown("**Composición por segmento de contacto**")
    seg = (df_view["segmento"].value_counts()
           .rename_axis("Segmento").reset_index(name="Tickets"))
    fig = px.bar(seg, x="Segmento", y="Tickets", color="Segmento",
                 color_discrete_sequence=PALETA, text="Tickets")
    st.plotly_chart(estilo_plot(fig, 280), use_container_width=True)

# =====================================================================
# TAB 2 · SIN RESPUESTA (foco Felipe)
# =====================================================================
with tabs[1]:
    st.markdown(f"#### 🎯 Tickets **Sin Respuesta** · criterio: *{criterio}*")
    st.markdown(
        '<div class="nota">Esta vista <b>siempre</b> muestra solo los tickets '
        'sin respuesta (independiente del toggle global), respetando los demás '
        'filtros. El ranking es por <b>contacto asociado</b>, etiquetado como '
        'Especialista / Interno / Cliente. <b>No se inventan nombres</b> de '
        'especialista a partir del texto.</div>', unsafe_allow_html=True)
    st.markdown("####")

    total_f = len(df_filt)
    sr_n = len(df_sr)
    esp_n = int((df_sr["segmento"] == "Especialista").sum())
    cli_n = int((df_sr["segmento"] == "Cliente externo").sum())
    int_n = int((df_sr["segmento"] == "Interno / Staff").sum())

    c = st.columns(4)
    with c[0]: kpi("Sin respuesta", sr_n,
                    f'{(sr_n/total_f*100) if total_f else 0:.1f}% de {total_f}', "red")
    with c[1]: kpi("De especialistas", esp_n,
                    f'{(esp_n/sr_n*100) if sr_n else 0:.0f}% de los sin respuesta')
    with c[2]: kpi("De clientes externos", cli_n,
                    f'{(cli_n/sr_n*100) if sr_n else 0:.0f}%', "blue")
    with c[3]: kpi("Internos / Staff", int_n,
                    f'{(int_n/sr_n*100) if sr_n else 0:.0f}%', "amber")

    st.markdown("####")
    rank = dl.ranking_reincidencia(df_sr, solo_sin_respuesta=False)
    g1, g2 = st.columns([3, 2])
    with g1:
        st.markdown("**🔝 Ranking de reincidencia en 'Sin respuesta'**")
        st.dataframe(rank, use_container_width=True, hide_index=True,
                     height=430)
    with g2:
        st.markdown("**Top 12 reincidentes**")
        top = rank.head(12).sort_values("Tickets")
        fig = px.bar(top, x="Tickets", y="Contacto", orientation="h",
                     color="Tipo", color_discrete_sequence=PALETA, text="Tickets")
        st.plotly_chart(estilo_plot(fig, 430), use_container_width=True)

    cdl = st.columns(2)
    with cdl[0]:
        st.download_button("⬇️ Descargar ranking (CSV)",
            rank.to_csv(index=False).encode("utf-8-sig"),
            "reincidencia_sin_respuesta.csv", "text/csv", use_container_width=True)
    with cdl[1]:
        st.download_button("⬇️ Descargar ranking (Excel)",
            dl.df_a_excel_bytes(rank, "Reincidencia"),
            "reincidencia_sin_respuesta.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)

# =====================================================================
# TAB 3 · REINCIDENCIA / CONTACTOS
# =====================================================================
with tabs[2]:
    st.markdown("#### 🔁 Contactos recurrentes (sobre la vista activa)")
    rank_all = dl.ranking_reincidencia(df_view, solo_sin_respuesta=False)
    recurrentes = rank_all[rank_all["Tickets"] > 1]
    c = st.columns(3)
    with c[0]: kpi("Contactos únicos", df_view["contacto"].nunique())
    with c[1]: kpi("Contactos recurrentes", len(recurrentes), ">1 ticket", "amber")
    with c[2]:
        top1 = rank_all.iloc[0] if len(rank_all) else None
        kpi("Mayor reincidente",
            f'{top1["Tickets"]}' if top1 is not None else "—",
            f'{top1["Contacto"]} ({top1["Tipo"]})' if top1 is not None else "", "red")

    st.markdown("####")
    st.dataframe(recurrentes, use_container_width=True, hide_index=True, height=320)

    st.markdown("#### 🔍 Detalle por contacto")
    opciones = rank_all["Contacto"] + "  ·  " + rank_all["Email"].fillna("sin email")
    sel = st.selectbox("Elige un contacto", opciones.tolist())
    nombre_sel = sel.split("  ·  ")[0]
    det = df_view[df_view["nombre_contacto"] == nombre_sel][
        ["ticket_id", "categoria", "resolucion", "prioridad", "estado",
         "fecha_cierre", "horas_cierre", "sin_respuesta"]
    ].copy()
    det["horas_cierre"] = det["horas_cierre"].round(1)
    st.dataframe(det, use_container_width=True, hide_index=True)

# =====================================================================
# TAB 4 · DISTRIBUCIONES
# =====================================================================
with tabs[3]:
    st.markdown("#### 📁 Distribuciones de la vista activa")

    def bloque_dist(col, titulo, split=False, donut=False):
        st.markdown(f"**{titulo}**")
        d = dl.distribucion(df_view, col, split_categoria=split)
        if donut:
            fig = px.pie(d, names=col, values="Tickets", hole=0.5,
                         color_discrete_sequence=PALETA)
            fig.update_traces(textinfo="percent+label")
        else:
            fig = px.bar(d.sort_values("Tickets"), x="Tickets", y=col,
                         orientation="h", text="Tickets",
                         color_discrete_sequence=[OY_BLUE])
        st.plotly_chart(estilo_plot(fig, 300), use_container_width=True)

    r1 = st.columns(2)
    with r1[0]: bloque_dist("categoria", "Categoría (multivalor ';')", split=True)
    with r1[1]: bloque_dist("resolucion", "Resolución", donut=True)
    r2 = st.columns(2)
    with r2[0]: bloque_dist("prioridad", "Prioridad", donut=True)
    with r2[1]: bloque_dist("estado", "Estado del ticket")
    st.markdown("**Rangos de tiempo a cierre**")
    d = dl.distribucion(df_view, "rango_cierre")
    fig = px.bar(d.sort_values("Tickets"), x="Tickets", y="rango_cierre",
                 orientation="h", text="Tickets", color_discrete_sequence=[OY_TEAL])
    st.plotly_chart(estilo_plot(fig, 320), use_container_width=True)

# =====================================================================
# TAB 5 · SLA & TIEMPOS
# =====================================================================
with tabs[4]:
    st.markdown("#### ⏱️ Cumplimiento de ANS y tiempos a cierre")
    st.markdown(
        '<div class="nota warn">Ojo: el ANS de <b>1ª respuesta</b> solo trae dato '
        'en una parte de los tickets (el resto queda "Sin dato", típicamente los '
        'que nunca recibieron respuesta). Los % se calculan sobre los que SÍ '
        'tienen dato.</div>', unsafe_allow_html=True)
    st.markdown("####")

    def sla_counts(col):
        s = df_view[col].astype(str).str.lower()
        a_tiempo = s.str.contains("a tiempo").sum()
        vencido = s.str.contains("vencido").sum()
        tarde = s.str.contains("tarde").sum()
        con_dato = df_view[col].notna().sum()
        return a_tiempo, vencido, tarde, con_dato

    a1, v1, t1, d1 = sla_counts("ans_primera")
    a2, v2, t2, d2 = sla_counts("ans_cierre")
    c = st.columns(4)
    with c[0]: kpi("ANS 1ª resp. a tiempo",
                    f'{(a1/d1*100) if d1 else 0:.0f}%', f'{a1} de {d1} con dato', "green")
    with c[1]: kpi("ANS 1ª resp. vencidos", v1, f'{d1} con dato', "red")
    with c[2]: kpi("ANS cierre a tiempo",
                    f'{(a2/d2*100) if d2 else 0:.0f}%', f'{a2} de {d2} con dato', "green")
    with c[3]: kpi("ANS cierre vencidos/tarde", f'{v2+t2}', f'{d2} con dato', "red")

    st.markdown("####")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Estado ANS 1ª respuesta**")
        d = dl.distribucion(df_view, "ans_primera")
        fig = px.bar(d, x="ans_primera", y="Tickets", text="Tickets",
                     color="ans_primera", color_discrete_sequence=PALETA)
        st.plotly_chart(estilo_plot(fig, 300), use_container_width=True)
    with g2:
        st.markdown("**Estado ANS cierre**")
        d = dl.distribucion(df_view, "ans_cierre")
        fig = px.bar(d, x="ans_cierre", y="Tickets", text="Tickets",
                     color="ans_cierre", color_discrete_sequence=PALETA)
        st.plotly_chart(estilo_plot(fig, 300), use_container_width=True)

    st.markdown("**Distribución del tiempo a cierre (horas, excluye 00:00:00)**")
    h = df_view["horas_cierre"]
    h = h[h > 0]
    fig = px.histogram(h, nbins=30, color_discrete_sequence=[OY_BLUE])
    fig.update_layout(showlegend=False, xaxis_title="Horas hasta cierre",
                      yaxis_title="Tickets")
    st.plotly_chart(estilo_plot(fig, 320), use_container_width=True)

# =====================================================================
# TAB 6 · ATENCIÓN A ESPECIALISTAS
# =====================================================================
with tabs[5]:
    st.markdown("#### 🎓 Atención a Especialistas")
    st.markdown(
        '<div class="nota warn"><b>Límite del dato (honesto):</b> el export NO '
        'incluye la <b>duración real</b> de la primera respuesta (la columna '
        '"Respondido A tiempo/Destiempo" viene vacía). Por eso aquí se mide: '
        '(1) <b>cumplimiento del ANS</b> de 1ª respuesta (a tiempo vs vencido) y '
        '(2) <b>tiempo total hasta resolución</b> (creación→cierre). Para obtener '
        'el "tarda X h en atender" exacto, re-exporta de HubSpot incluyendo la '
        'propiedad <i>"Tiempo hasta primera respuesta"</i>.</div>',
        unsafe_allow_html=True)
    st.markdown("####")

    esp = df[df["es_especialista"]]            # subconjunto (E), sobre TODO el set
    ans_e = esp["ans_primera"].astype(str).str.lower()
    a_t = ans_e.str.contains("a tiempo").sum()
    venc = ans_e.str.contains("vencido").sum()
    con_dato = esp["ans_primera"].notna().sum()
    he = esp["horas_cierre"]; he = he[he > 0]

    c = st.columns(4)
    with c[0]: kpi("Tickets de especialistas", len(esp), 'contactos con prefijo "(E)"')
    with c[1]: kpi("ANS 1ª resp. a tiempo",
                    f'{(a_t/con_dato*100) if con_dato else 0:.0f}%',
                    f'{a_t} de {con_dato} con dato', "green")
    with c[2]: kpi("Mediana a resolución", f'{he.median():.0f} h' if len(he) else "—",
                    "creación → cierre", "blue")
    with c[3]: kpi("P90 a resolución", f'{he.quantile(0.9):.0f} h' if len(he) else "—",
                    "90% por debajo", "amber")

    st.markdown("####")
    st.markdown("**Especialista vs Cliente externo · tiempo a resolución y cumplimiento**")
    comp = df[df["segmento"].isin(["Especialista", "Cliente externo"])].copy()
    g1, g2 = st.columns(2)
    with g1:
        cb = comp[comp["horas_cierre"] > 0]
        fig = px.box(cb, x="segmento", y="horas_cierre", color="segmento",
                     color_discrete_sequence=PALETA, points=False)
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Horas a cierre")
        st.plotly_chart(estilo_plot(fig, 340), use_container_width=True)
    with g2:
        tmp = comp.copy()
        tmp["ANS 1ª resp."] = np.where(
            tmp["ans_primera"].astype(str).str.lower().str.contains("a tiempo"), "A tiempo",
            np.where(tmp["ans_primera"].astype(str).str.lower().str.contains("vencido"),
                     "Vencido", "Sin dato"))
        cross = (tmp.groupby(["segmento", "ANS 1ª resp."]).size()
                 .reset_index(name="Tickets"))
        fig = px.bar(cross, x="segmento", y="Tickets", color="ANS 1ª resp.",
                     barmode="group", color_discrete_sequence=PALETA, text="Tickets")
        fig.update_layout(xaxis_title="")
        st.plotly_chart(estilo_plot(fig, 340), use_container_width=True)

    st.download_button("⬇️ Descargar tickets de especialistas (CSV)",
        esp.to_csv(index=False).encode("utf-8-sig"),
        "tickets_especialistas.csv", "text/csv")

# =====================================================================
# TAB 7 · EXPLORADOR DE TICKETS
# =====================================================================
with tabs[6]:
    st.markdown("#### 🔎 Explorador de tickets (vista activa)")
    busca = st.text_input("Buscar en contacto / categoría / descripción", "")
    base = df_view
    if busca.strip():
        b = busca.strip().lower()
        mask = (
            base["nombre_contacto"].astype(str).str.lower().str.contains(b)
            | base["categoria"].astype(str).str.lower().str.contains(b)
            | base["descripcion"].astype(str).str.lower().str.contains(b)
        )
        base = base[mask]

    cols_mostrar = ["ticket_id", "nombre_contacto", "segmento", "categoria",
                    "resolucion", "prioridad", "estado", "fecha_cierre",
                    "horas_cierre", "ans_primera", "ans_cierre", "sin_respuesta"]
    cols_sel = st.multiselect("Columnas a mostrar", cols_mostrar,
                              default=cols_mostrar[:9])
    tabla = base[cols_sel].copy()
    if "horas_cierre" in tabla:
        tabla["horas_cierre"] = tabla["horas_cierre"].round(1)
    st.caption(f"{len(tabla)} tickets")
    st.dataframe(tabla, use_container_width=True, hide_index=True, height=480)

    c = st.columns(2)
    with c[0]:
        st.download_button("⬇️ Descargar tabla filtrada (CSV)",
            tabla.to_csv(index=False).encode("utf-8-sig"),
            "tickets_filtrados.csv", "text/csv", use_container_width=True)
    with c[1]:
        st.download_button("⬇️ Descargar tabla filtrada (Excel)",
            dl.df_a_excel_bytes(tabla, "Tickets"),
            "tickets_filtrados.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)

# =====================================================================
# TAB 8 · TELEMETRÍA DE ESPECIALISTAS
# =====================================================================
with tabs[7]:
    st.markdown("#### 📡 Telemetría de plataforma por especialista")
    st.caption("Fuente: hoja '📋 Mayo - Todos' del reporte de Felipe. "
               "Es una vista paralela: no se cruza por nombre con los tickets de HubSpot.")

    up_esp = st.file_uploader("Sube el reporte de especialistas (.xlsx o .csv)",
                              type=["xlsx", "xls", "csv"], key="up_esp")
    if up_esp is not None:
        esp_df = dl.cargar_especialistas(up_esp)
    elif SAMPLE_ESP.exists():
        esp_df = _esp_desde_ruta(str(SAMPLE_ESP))
    else:
        st.warning("Sube el reporte de especialistas para ver esta pestaña.")
        st.stop()

    total_citas = int(esp_df["Total Citas"].sum())
    total_inc = int(esp_df["Citas c/ Inc."].sum())
    n_esp = int((esp_df["Tipo"] == "Especialista").sum()) if "Tipo" in esp_df else len(esp_df)
    c = st.columns(4)
    with c[0]: kpi("Especialistas", n_esp, "tipo = Especialista")
    with c[1]: kpi("Citas del mes", f'{total_citas:,}'.replace(",", "."))
    with c[2]: kpi("Citas con incidencia", f'{total_inc:,}'.replace(",", "."), color="amber")
    with c[3]: kpi("% incidencia global",
                    f'{(total_inc/total_citas*100) if total_citas else 0:.1f}%', color="red")

    st.markdown("####")
    min_citas = st.slider("Citas mínimas para el ranking (evita % engañosos con pocas citas)",
                          0, 50, 20)
    base_e = esp_df[esp_df["Total Citas"] >= min_citas].copy()

    tm_opts = ["(todos)"] + sorted(esp_df["Talent Manager"].dropna().unique().tolist())
    tm_sel = st.selectbox("Talent Manager", tm_opts)
    if tm_sel != "(todos)":
        base_e = base_e[base_e["Talent Manager"] == tm_sel]

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Top 12 por % de incidencia**")
        top = base_e.sort_values("% Inc.", ascending=False).head(12).copy()
        top["%"] = (top["% Inc."] * 100).round(1)
        fig = px.bar(top.sort_values("%"), x="%", y="Especialista", orientation="h",
                     text="%", color_discrete_sequence=[WARN_RED])
        st.plotly_chart(estilo_plot(fig, 420), use_container_width=True)
    with g2:
        metrica = st.selectbox("Métrica técnica para el ranking", dl.METRICAS_TELEMETRIA)
        st.markdown(f"**Top 12 por {metrica}**")
        top = base_e.sort_values(metrica, ascending=False).head(12)
        fig = px.bar(top.sort_values(metrica), x=metrica, y="Especialista",
                     orientation="h", text=metrica, color_discrete_sequence=[OY_BLUE])
        st.plotly_chart(estilo_plot(fig, 420), use_container_width=True)

    st.markdown("**Tabla completa de especialistas**")
    st.dataframe(base_e, use_container_width=True, hide_index=True, height=360)
    st.download_button("⬇️ Descargar telemetría filtrada (CSV)",
        base_e.to_csv(index=False).encode("utf-8-sig"),
        "telemetria_especialistas.csv", "text/csv")

# ---------------------------------------------------------------------
st.divider()
st.caption("Dashboard de Incidencias Técnicas · Opción Yo · construido con Streamlit. "
           "Cifras validadas contra el reporte de mayo 2026.")
