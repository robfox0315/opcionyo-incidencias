"""
=====================================================================
  DASHBOARD DE INCIDENCIAS TÉCNICAS · OPCIÓN YO
  Área de Incidencias Técnicas · solicitado por Felipe Higuera
  Versión gerencial: gráficos claros, tiempos en días, insights.
  Identidad de marca:  TEAL #16B6C2 · AZUL #2F80ED
=====================================================================
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import data_loader as dl

# ---------------------------------------------------------------------
OY_TEAL, OY_BLUE, OY_DARK, OY_GREY = "#16B6C2", "#2F80ED", "#0E2A47", "#6B7280"
OK_GREEN, WARN_RED, WARN_AMBER = "#27AE60", "#E74C3C", "#F39C12"
PALETA = [OY_TEAL, OY_BLUE, "#7C4DFF", OK_GREEN, WARN_AMBER, WARN_RED,
          "#00BFA5", "#5C6BC0", "#FF8A65", "#26A69A", "#AB47BC", "#78909C"]

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"


def _buscar_dato(nombre):
    """Busca un CSV de muestra en data/ y, si no, en la raíz del repo.
    Devuelve la ruta (str) o None. Tolera que al subir a GitHub el archivo
    haya quedado fuera de la carpeta data/."""
    for cand in (DATA_DIR / nombre, BASE_DIR / nombre):
        if cand.exists():
            return str(cand)
    return None


SAMPLE_TICKETS = _buscar_dato("problemas_tecnicos_mayo.csv")
SAMPLE_ESP = _buscar_dato("incidencias_especialistas_mayo.csv")
SAMPLE_PRUEBAS = _buscar_dato("seguimiento_pruebas_mayo.csv")

st.set_page_config(page_title="Incidencias Técnicas · Opción Yo",
                   page_icon="🛠️", layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
    .stApp {{ background-color:#F7FAFC; }}
    .block-container {{ padding-top:2rem; padding-bottom:3rem; }}
    h1,h2,h3 {{ color:{OY_DARK}; }}
    .oy-header {{ background:linear-gradient(100deg,{OY_TEAL} 0%,{OY_BLUE} 100%);
        padding:22px 28px; border-radius:16px; color:white; margin-bottom:6px; }}
    .oy-header h1 {{ color:white; margin:0; font-size:1.6rem; }}
    .oy-header p {{ color:#EAF8FA; margin:4px 0 0 0; font-size:.95rem; }}
    .kpi {{ background:white; border-radius:14px; padding:16px 20px;
        border:1px solid #E5EAF0; border-left:6px solid {OY_TEAL};
        box-shadow:0 1px 3px rgba(16,42,71,.06); height:100%; }}
    .kpi .label {{ color:{OY_GREY}; font-size:.74rem; font-weight:600;
        text-transform:uppercase; letter-spacing:.03em; }}
    .kpi .value {{ color:{OY_DARK}; font-size:1.8rem; font-weight:800; line-height:1.1; }}
    .kpi .sub {{ color:{OY_GREY}; font-size:.78rem; margin-top:2px; }}
    .kpi.blue {{ border-left-color:{OY_BLUE}; }}
    .kpi.green {{ border-left-color:{OK_GREEN}; }}
    .kpi.red {{ border-left-color:{WARN_RED}; }}
    .kpi.amber {{ border-left-color:{WARN_AMBER}; }}
    .stTabs [data-baseweb="tab-list"] {{ gap:4px; flex-wrap:wrap; }}
    .stTabs [data-baseweb="tab"] {{ font-size:.88rem; }}
    .intro {{ background:#EAF8FA; border-left:4px solid {OY_TEAL};
        padding:10px 16px; border-radius:8px; font-size:.9rem; color:{OY_DARK}; margin-bottom:6px; }}
    .intro.warn {{ background:#FFF4E5; border-left-color:{WARN_AMBER}; }}
    .ins {{ background:white; border-radius:12px; padding:14px 18px; margin-bottom:10px;
        border:1px solid #E5EAF0; border-left:6px solid {OY_GREY}; }}
    .ins .t {{ font-weight:700; color:{OY_DARK}; font-size:1.02rem; }}
    .ins .d {{ color:#374151; font-size:.9rem; margin:4px 0; }}
    .ins .r {{ color:{OY_DARK}; font-size:.9rem; background:#F4F7FB;
        border-radius:8px; padding:8px 12px; }}
    .ins .r b {{ color:{OY_BLUE}; }}
    .ins.critico {{ border-left-color:{WARN_RED}; }}
    .ins.alerta  {{ border-left-color:{WARN_AMBER}; }}
    .ins.ok      {{ border-left-color:{OK_GREEN}; }}
    .ins.info    {{ border-left-color:{OY_BLUE}; }}
</style>""", unsafe_allow_html=True)


def kpi(label, value, sub="", color=""):
    st.markdown(f"""<div class="kpi {color}"><div class="label">{label}</div>
        <div class="value">{value}</div><div class="sub">{sub}</div></div>""",
        unsafe_allow_html=True)


def fmt_d(h):
    if h is None or (isinstance(h, float) and np.isnan(h)):
        return "—"
    return f"{h/24:.1f} d"


def estilo(fig, h=360, leyenda=True):
    fig.update_layout(
        height=h, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=OY_DARK, size=13),
        showlegend=leyenda,
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, x=0))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F6")
    return fig


def barra_h(d, val, cat, color=OY_TEAL, sufijo="", h=320):
    """Barra horizontal ordenada (mayor arriba), con etiquetas de valor."""
    d = d.sort_values(val)
    fig = px.bar(d, x=val, y=cat, orientation="h",
                 color_discrete_sequence=[color], text=val)
    fig.update_traces(texttemplate="%{text:.0f}" + sufijo, textposition="outside",
                      cliponaxis=False)
    fig.update_layout(xaxis_title="", yaxis_title="")
    return estilo(fig, h, leyenda=False)


def donut(d, names, values, colores=None):
    fig = px.pie(d, names=names, values=values, hole=0.55,
                 color_discrete_sequence=colores or PALETA)
    fig.update_traces(textinfo="percent", textposition="inside",
                      insidetextorientation="horizontal")
    fig.update_layout(legend=dict(orientation="v", x=1, y=0.5))
    return estilo(fig, 320)


# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _tk(ruta): return dl.cargar_tickets(ruta)
@st.cache_data(show_spinner=False)
def _esp(ruta): return dl.cargar_especialistas(ruta)
@st.cache_data(show_spinner=False)
def _pr(ruta): return dl.cargar_pruebas(ruta)


# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🛠️ Incidencias Técnicas")
    st.caption("Opción Yo · Área de Incidencias")
    st.divider()
    st.markdown("**1 · Fuente de datos (HubSpot)**")
    subido = st.file_uploader("Sube el export de HubSpot (.xlsx o .csv)",
                              type=["xlsx", "xls", "csv"], key="up_tickets")
    if subido is not None:
        df = dl.cargar_tickets(subido)
        st.success(f"✅ {subido.name} ({len(df)} tickets)")
    elif SAMPLE_TICKETS is not None:
        df = _tk(SAMPLE_TICKETS)
        st.info(f"📄 Muestra incluida ({len(df)} tickets).")
    else:
        st.error("Sube el export de HubSpot para continuar."); st.stop()

    st.divider()
    st.markdown("**2 · Filtro principal · SIN RESPUESTA**")
    criterio = st.radio("¿Qué cuenta como 'Sin respuesta'?",
                        ["Resolución o Categoría", "Solo Resolución", "Solo Categoría"])
    vista = st.radio("Vista", ["Todos los tickets", "Solo Sin Respuesta"])
    st.divider()
    st.markdown("**3 · Filtros adicionales**")
    seg_sel = st.multiselect("Segmento de contacto", sorted(df["segmento"].unique()),
                             default=sorted(df["segmento"].unique()))
    prio_sel = st.multiselect("Prioridad", sorted(df["prioridad"].fillna("Sin dato").unique()),
                              default=sorted(df["prioridad"].fillna("Sin dato").unique()))
    est_sel = st.multiselect("Estado del ticket", sorted(df["estado"].fillna("Sin dato").unique()),
                             default=sorted(df["estado"].fillna("Sin dato").unique()))

if criterio == "Solo Resolución":
    df["sin_respuesta"] = df["sr_resolucion"]
elif criterio == "Solo Categoría":
    df["sin_respuesta"] = df["sr_categoria"]
else:
    df["sin_respuesta"] = df["sr_resolucion"] | df["sr_categoria"]

df_filt = df[df["segmento"].isin(seg_sel)
             & df["prioridad"].fillna("Sin dato").isin(prio_sel)
             & df["estado"].fillna("Sin dato").isin(est_sel)].copy()
df_sr = df_filt[df_filt["sin_respuesta"]].copy()
df_view = df_sr if vista == "Solo Sin Respuesta" else df_filt

# ---------------------------------------------------------------------
st.markdown(f"""<div class="oy-header"><h1>🛠️ Dashboard de Incidencias Técnicas</h1>
<p>Opción Yo · Corte Mayo 2026 · Fuente: export HubSpot "problemas técnicos"
&nbsp;|&nbsp; Vista: <b>{vista}</b> · {len(df_view)} tickets en pantalla</p></div>""",
    unsafe_allow_html=True)

tabs = st.tabs([
    "📊 Resumen", "🎯 Sin Respuesta", "🔁 Reincidencia", "📁 Distribuciones",
    "⏱️ SLA & Tiempos", "🎓 Atención Especialistas", "🔎 Explorador",
    "📡 Telemetría", "💡 Insights & Recomendaciones"])

# =====================================================================
# 1 · RESUMEN
# =====================================================================
with tabs[0]:
    st.markdown('<div class="intro">📌 <b>Foto del mes para gerencia.</b> Los tiempos '
                'se muestran en <b>días</b> (1 día = 24 h). "Sin respuesta" = tickets que '
                'cierran sin una respuesta registrada.</div>', unsafe_allow_html=True)
    k = dl.kpis_generales(df_view)
    c = st.columns(5)
    with c[0]: kpi("Tickets en vista", k["total"])
    with c[1]: kpi("Sin respuesta", k["sin_respuesta"], f'{k["pct_sin_respuesta"]:.0f}% del total', "red")
    with c[2]: kpi("Cerrados / Abiertos", f'{k["cerrados"]} / {k["abiertos"]}', "abiertos = sin cierre", "blue")
    with c[3]: kpi("Escalados a IT", k["escalados_it"],
                   f'+{int(df_view["it_involucrado"].sum())-k["escalados_it"]} cerrados por IT', "amber")
    with c[4]: kpi("Contactos recurrentes", k["recurrentes"], "con >1 ticket")
    c = st.columns(4)
    with c[0]: kpi("Tiempo medio a cierre", fmt_d(k["horas_media"]), f'{k["horas_media"]:.0f} h', "blue")
    with c[1]: kpi("Mediana a cierre", fmt_d(k["horas_mediana"]), "más robusta que el promedio")
    with c[2]: kpi("P90 a cierre", fmt_d(k["horas_p90"]), "90% cierra por debajo")
    ans_ok = df_view["ans_cierre"].astype(str).str.lower().eq("ans completado a tiempo").sum()
    ans_tot = df_view["ans_cierre"].notna().sum()
    with c[3]: kpi("ANS cierre a tiempo", f'{(ans_ok/ans_tot*100) if ans_tot else 0:.0f}%',
                   f'{ans_ok} de {ans_tot} con dato', "green")
    res_ok = df_view["resolucion"].astype(str).str.lower().eq("resuelto exitoso").mean()*100
    sin_prio = df_view["prioridad"].isna().mean()*100
    vc = df_view["contacto"].value_counts(); desde_rec = vc[vc>1].sum()
    c = st.columns(4)
    with c[0]: kpi("Resolución efectiva", f'{res_ok:.0f}%', "tickets 'Resuelto exitoso'",
                   "green" if res_ok>=40 else "red")
    with c[1]: kpi("Sin prioridad asignada", f'{sin_prio:.0f}%', "calidad de dato",
                   "amber" if sin_prio>10 else "green")
    with c[2]: kpi("Tickets desde recurrentes", f'{(desde_rec/len(df_view)*100) if len(df_view) else 0:.0f}%',
                   f'{int(desde_rec)} tickets', "amber")
    with c[3]: kpi("Top 10 contactos", f'{(vc.head(10).sum()/len(df_view)*100) if len(df_view) else 0:.0f}%',
                   "concentración (Pareto)", "blue")

    st.markdown("####")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**¿Cómo terminan los tickets? (Resolución)**")
        st.caption("Más de la mitad cierran sin respuesta: ahí está la oportunidad.")
        d = dl.distribucion(df_view, "resolucion")
        colores = [WARN_RED if "sin respuesta" in str(x).lower() else
                   OK_GREEN if "exitoso" in str(x).lower() else c2
                   for x, c2 in zip(d["resolucion"], PALETA)]
        st.plotly_chart(donut(d, "resolucion", "Tickets", colores), use_container_width=True)
    with g2:
        st.markdown("**Categorías más frecuentes**")
        st.caption("Tipo de problema técnico reportado (mayor arriba).")
        d = dl.distribucion(df_view, "categoria", split_categoria=True).head(8)
        st.plotly_chart(barra_h(d, "Tickets", "categoria", OY_TEAL), use_container_width=True)

# =====================================================================
# 2 · SIN RESPUESTA
# =====================================================================
with tabs[1]:
    st.markdown('<div class="intro">🎯 <b>El foco del área.</b> Esta vista muestra '
                '<b>siempre</b> solo los tickets sin respuesta (respeta los demás filtros). '
                'El ranking es por <b>contacto</b>, etiquetado Especialista / Interno / '
                'Cliente. <b>No se inventan</b> nombres de especialista del texto.</div>',
                unsafe_allow_html=True)
    total_f, sr_n = len(df_filt), len(df_sr)
    esp_n = int((df_sr["segmento"]=="Especialista").sum())
    cli_n = int((df_sr["segmento"]=="Cliente externo").sum())
    int_n = int((df_sr["segmento"]=="Interno / Staff").sum())
    c = st.columns(4)
    with c[0]: kpi("Sin respuesta", sr_n, f'{(sr_n/total_f*100) if total_f else 0:.0f}% de {total_f}', "red")
    with c[1]: kpi("De especialistas", esp_n, f'{(esp_n/sr_n*100) if sr_n else 0:.0f}% del total SR')
    with c[2]: kpi("De clientes externos", cli_n, f'{(cli_n/sr_n*100) if sr_n else 0:.0f}%', "blue")
    with c[3]: kpi("Internos / Staff", int_n, f'{(int_n/sr_n*100) if sr_n else 0:.0f}%', "amber")

    st.markdown("####")
    st.markdown("**🚨 ¿Qué categorías concentran la falta de respuesta? (tasa de fuga)**")
    st.caption("% de tickets que cierran sin respuesta DENTRO de cada categoría. "
               "Rojo intenso = más fuga. Aquí se prioriza la acción.")
    fuga = dl.tasa_sin_respuesta_por_categoria(df_filt, min_tickets=5).head(8)
    fig = px.bar(fuga.sort_values("% sin respuesta"), x="% sin respuesta", y="Categoría",
                 orientation="h", color="% sin respuesta",
                 color_continuous_scale=["#FCE4E4", WARN_RED], text="% sin respuesta")
    fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title="% sin respuesta", yaxis_title="", coloraxis_showscale=False)
    st.plotly_chart(estilo(fig, 340, leyenda=False), use_container_width=True)

    st.markdown("####")
    rank = dl.ranking_reincidencia(df_sr, solo_sin_respuesta=False)
    g1, g2 = st.columns([3, 2])
    with g1:
        st.markdown("**🔝 Ranking de reincidencia en 'Sin respuesta'**")
        st.dataframe(rank, use_container_width=True, hide_index=True, height=420)
    with g2:
        st.markdown("**Top 12 reincidentes**")
        st.caption("Color por tipo de contacto.")
        top = rank.head(12).sort_values("Tickets")
        fig = px.bar(top, x="Tickets", y="Contacto", orientation="h", color="Tipo",
                     color_discrete_sequence=PALETA, text="Tickets")
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="")
        st.plotly_chart(estilo(fig, 420), use_container_width=True)

    c = st.columns(2)
    with c[0]:
        st.download_button("⬇️ Ranking (CSV)", rank.to_csv(index=False).encode("utf-8-sig"),
                           "reincidencia_sin_respuesta.csv", "text/csv", use_container_width=True)
    with c[1]:
        st.download_button("⬇️ Ranking (Excel)", dl.df_a_excel_bytes(rank, "Reincidencia"),
                           "reincidencia_sin_respuesta.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

# =====================================================================
# 3 · REINCIDENCIA
# =====================================================================
with tabs[2]:
    st.markdown('<div class="intro">🔁 Contactos que abren <b>más de un ticket</b>. '
                'Atacar este grupo tiene alto retorno.</div>', unsafe_allow_html=True)
    rank_all = dl.ranking_reincidencia(df_view, solo_sin_respuesta=False)
    recurr = rank_all[rank_all["Tickets"] > 1]
    c = st.columns(3)
    with c[0]: kpi("Contactos únicos", df_view["contacto"].nunique())
    with c[1]: kpi("Contactos recurrentes", len(recurr), ">1 ticket", "amber")
    with c[2]:
        t0 = rank_all.iloc[0] if len(rank_all) else None
        kpi("Mayor reincidente", f'{t0["Tickets"]}' if t0 is not None else "—",
            f'{t0["Contacto"]} ({t0["Tipo"]})' if t0 is not None else "", "red")
    st.markdown("####")
    st.dataframe(recurr, use_container_width=True, hide_index=True, height=300)
    st.markdown("**🔍 Detalle por contacto**")
    opc = (rank_all["Contacto"] + "  ·  " + rank_all["Email"].fillna("sin email")).tolist()
    sel = st.selectbox("Elige un contacto", opc)
    nom = sel.split("  ·  ")[0]
    det = df_view[df_view["nombre_contacto"]==nom][
        ["ticket_id","categoria","resolucion","prioridad","estado","fecha_cierre",
         "horas_cierre","sin_respuesta"]].copy()
    det["dias_cierre"] = (det["horas_cierre"]/24).round(1)
    det = det.drop(columns=["horas_cierre"])
    st.dataframe(det, use_container_width=True, hide_index=True)

# =====================================================================
# 4 · DISTRIBUCIONES
# =====================================================================
with tabs[3]:
    st.markdown('<div class="intro">📁 Cómo se reparten los tickets por cada dimensión. '
                'Barras ordenadas de mayor a menor.</div>', unsafe_allow_html=True)
    r1 = st.columns(2)
    with r1[0]:
        st.markdown("**Categoría** (multivalor separado por ';')")
        st.plotly_chart(barra_h(dl.distribucion(df_view,"categoria",split_categoria=True),
                                "Tickets","categoria",OY_TEAL), use_container_width=True)
    with r1[1]:
        st.markdown("**Resolución**")
        st.plotly_chart(barra_h(dl.distribucion(df_view,"resolucion"),
                                "Tickets","resolucion",OY_BLUE), use_container_width=True)
    r2 = st.columns(2)
    with r2[0]:
        st.markdown("**Prioridad**")
        st.caption("Casi todo es 'Media': la priorización apenas se usa.")
        st.plotly_chart(barra_h(dl.distribucion(df_view,"prioridad"),
                                "Tickets","prioridad",WARN_AMBER), use_container_width=True)
    with r2[1]:
        st.markdown("**Estado del ticket**")
        st.plotly_chart(barra_h(dl.distribucion(df_view,"estado"),
                                "Tickets","estado","#7C4DFF"), use_container_width=True)
    st.markdown("**Rangos de tiempo a cierre**")
    st.plotly_chart(barra_h(dl.distribucion(df_view,"rango_cierre"),
                            "Tickets","rango_cierre",OY_TEAL, h=300), use_container_width=True)

# =====================================================================
# 5 · SLA & TIEMPOS
# =====================================================================
with tabs[4]:
    st.markdown('<div class="intro warn">⏱️ <b>ANS = Acuerdo de Nivel de Servicio</b> '
                '(si se respondió/cerró dentro del plazo pactado). El ANS de 1ª respuesta '
                'solo trae dato en una parte de los tickets; los % se calculan sobre los '
                'que SÍ tienen dato. Tiempos en <b>días</b>.</div>', unsafe_allow_html=True)
    def sla(col):
        s = df_view[col].astype(str).str.lower()
        return (s.str.contains("a tiempo").sum(), s.str.contains("vencido").sum(),
                s.str.contains("tarde").sum(), df_view[col].notna().sum())
    a1,v1,_,d1 = sla("ans_primera"); a2,v2,t2,d2 = sla("ans_cierre")
    c = st.columns(4)
    with c[0]: kpi("ANS 1ª resp. a tiempo", f'{(a1/d1*100) if d1 else 0:.0f}%', f'{a1} de {d1} con dato', "green")
    with c[1]: kpi("ANS 1ª resp. vencidos", v1, f'{d1} con dato', "red")
    with c[2]: kpi("ANS cierre a tiempo", f'{(a2/d2*100) if d2 else 0:.0f}%', f'{a2} de {d2} con dato', "green")
    with c[3]: kpi("ANS cierre vencidos/tarde", v2+t2, f'{d2} con dato', "red")
    st.markdown("####")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Cumplimiento ANS · 1ª respuesta**")
        st.plotly_chart(barra_h(dl.distribucion(df_view,"ans_primera"),
                                "Tickets","ans_primera",OY_BLUE, h=280), use_container_width=True)
    with g2:
        st.markdown("**Cumplimiento ANS · cierre**")
        st.plotly_chart(barra_h(dl.distribucion(df_view,"ans_cierre"),
                                "Tickets","ans_cierre",OY_TEAL, h=280), use_container_width=True)
    st.markdown("**¿Cuántos días tardan en cerrar los tickets?**")
    st.caption("Cada barra = nº de tickets que cerraron en ese rango de días. Excluye cierres 00:00:00.")
    h = df_view["horas_cierre"]; h = (h[h>0]/24)
    fig = px.histogram(h, nbins=24, color_discrete_sequence=[OY_BLUE])
    fig.update_layout(showlegend=False, xaxis_title="Días hasta cierre", yaxis_title="Nº de tickets",
                      bargap=0.05)
    st.plotly_chart(estilo(fig, 320, leyenda=False), use_container_width=True)

# =====================================================================
# 6 · ATENCIÓN ESPECIALISTAS
# =====================================================================
with tabs[5]:
    st.markdown('<div class="intro warn">🎓 <b>Límite del dato (honesto):</b> el export '
                'no trae la <b>duración real</b> de la 1ª respuesta. Aquí medimos '
                '<b>cumplimiento de ANS</b> y <b>tiempo total a resolución (en días)</b>. '
                'Para el "tarda X en atender" exacto, re-exportar de HubSpot la propiedad '
                '"Tiempo hasta primera respuesta".</div>', unsafe_allow_html=True)
    esp = df[df["es_especialista"]]
    ans_e = esp["ans_primera"].astype(str).str.lower()
    a_t = ans_e.str.contains("a tiempo").sum(); con = esp["ans_primera"].notna().sum()
    he = esp["horas_cierre"]; he = he[he>0]
    c = st.columns(4)
    with c[0]: kpi("Tickets de especialistas", len(esp), 'contactos con "(E)"')
    with c[1]: kpi("ANS 1ª resp. a tiempo", f'{(a_t/con*100) if con else 0:.0f}%', f'{a_t} de {con}', "green")
    with c[2]: kpi("Mediana a resolución", fmt_d(he.median()) if len(he) else "—", "creación→cierre", "blue")
    with c[3]: kpi("P90 a resolución", fmt_d(he.quantile(.9)) if len(he) else "—", "90% por debajo", "amber")
    st.markdown("####")
    comp = df[df["segmento"].isin(["Especialista","Cliente externo"])].copy()
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Tiempo a resolución: Especialista vs Cliente**")
        st.caption("Mediana y P90 en días (más bajo = más rápido).")
        cb = comp[comp["horas_cierre"]>0].copy()
        res = (cb.groupby("segmento")["horas_cierre"]
               .agg(Mediana=lambda s:s.median()/24, P90=lambda s:s.quantile(.9)/24)
               .reset_index().melt(id_vars="segmento", var_name="Métrica", value_name="Días"))
        fig = px.bar(res, x="segmento", y="Días", color="Métrica", barmode="group",
                     color_discrete_sequence=[OY_TEAL, OY_BLUE], text="Días")
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="Días a cierre")
        st.plotly_chart(estilo(fig, 340), use_container_width=True)
    with g2:
        st.markdown("**Cumplimiento ANS 1ª respuesta por segmento**")
        st.caption("Cuántos tickets se atendieron a tiempo, vencidos o sin dato.")
        tmp = comp.copy()
        low = tmp["ans_primera"].astype(str).str.lower()
        tmp["ANS"] = np.where(low.str.contains("a tiempo"),"A tiempo",
                     np.where(low.str.contains("vencido"),"Vencido","Sin dato"))
        cross = tmp.groupby(["segmento","ANS"]).size().reset_index(name="Tickets")
        fig = px.bar(cross, x="segmento", y="Tickets", color="ANS", barmode="group",
                     color_discrete_map={"A tiempo":OK_GREEN,"Vencido":WARN_RED,"Sin dato":OY_GREY},
                     text="Tickets")
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="")
        st.plotly_chart(estilo(fig, 340), use_container_width=True)
    st.download_button("⬇️ Tickets de especialistas (CSV)",
                       esp.to_csv(index=False).encode("utf-8-sig"),
                       "tickets_especialistas.csv", "text/csv")

# =====================================================================
# 7 · EXPLORADOR
# =====================================================================
with tabs[6]:
    st.markdown('<div class="intro">🔎 Tabla completa filtrable. Busca y descarga lo que '
                'necesites para gerencia.</div>', unsafe_allow_html=True)
    busca = st.text_input("Buscar en contacto / categoría / descripción", "")
    base = df_view
    if busca.strip():
        b = busca.strip().lower()
        base = base[base["nombre_contacto"].astype(str).str.lower().str.contains(b)
                    | base["categoria"].astype(str).str.lower().str.contains(b)
                    | base["descripcion"].astype(str).str.lower().str.contains(b)]
    base = base.copy(); base["dias_cierre"] = (base["horas_cierre"]/24).round(1)
    cols = ["ticket_id","nombre_contacto","segmento","categoria","resolucion","prioridad",
            "estado","fecha_cierre","dias_cierre","ans_primera","ans_cierre","sin_respuesta"]
    sel = st.multiselect("Columnas", cols, default=cols[:9])
    tabla = base[sel]
    st.caption(f"{len(tabla)} tickets")
    st.dataframe(tabla, use_container_width=True, hide_index=True, height=460)
    c = st.columns(2)
    with c[0]:
        st.download_button("⬇️ Tabla (CSV)", tabla.to_csv(index=False).encode("utf-8-sig"),
                           "tickets_filtrados.csv", "text/csv", use_container_width=True)
    with c[1]:
        st.download_button("⬇️ Tabla (Excel)", dl.df_a_excel_bytes(tabla, "Tickets"),
                           "tickets_filtrados.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

# =====================================================================
# 8 · TELEMETRÍA
# =====================================================================
with tabs[7]:
    st.markdown('<div class="intro">📡 Telemetría de plataforma por especialista '
                '(sesiones). Vista <b>paralela</b>: no se cruza por nombre con los tickets '
                'de HubSpot.</div>', unsafe_allow_html=True)
    up_e = st.file_uploader("Reporte de especialistas (.xlsx o .csv) — NO el de HubSpot",
                            type=["xlsx","xls","csv"], key="up_esp")
    esp_df = None
    if up_e is not None:
        try:
            esp_df = dl.cargar_especialistas(up_e)
            st.success(f"✅ Reporte cargado: {up_e.name}")
        except Exception as e:
            st.error(f"⚠️ {e}")
            if SAMPLE_ESP is not None:
                st.info("Sigo mostrando la **muestra incluida** mientras tanto.")
                esp_df = _esp(SAMPLE_ESP)
    elif SAMPLE_ESP is not None:
        esp_df = _esp(SAMPLE_ESP)
    if esp_df is None:
        st.warning("Sube el reporte de especialistas (hoja '📋 Mayo - Todos')."); st.stop()

    tot_c = int(esp_df["Total Citas"].sum()); tot_i = int(esp_df["Citas c/ Inc."].sum())
    n_e = int((esp_df["Tipo"]=="Especialista").sum()) if "Tipo" in esp_df else len(esp_df)
    c = st.columns(4)
    with c[0]: kpi("Especialistas", n_e)
    with c[1]: kpi("Citas del mes", f'{tot_c:,}'.replace(",", "."))
    with c[2]: kpi("Citas con incidencia", f'{tot_i:,}'.replace(",", "."), "", "amber")
    with c[3]: kpi("% incidencia global", f'{(tot_i/tot_c*100) if tot_c else 0:.1f}%', "", "red")

    # --- NUEVO: Incidencias por tipo (resumen) ---
    st.markdown("#### 🧩 Incidencias por tipo (resumen)")
    st.caption("Suma de eventos técnicos del mes. 2 tipos concentran el ~84%: ahí está la causa raíz.")
    tipo = dl.incidencias_por_tipo(esp_df)
    g1, g2 = st.columns([3, 2])
    with g1:
        d = tipo.sort_values("Eventos")
        fig = px.bar(d, x="Eventos", y="Tipo", orientation="h", text="Eventos",
                     color="% del total", color_continuous_scale=["#D6F0F2", OY_BLUE])
        fig.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="Eventos en el mes", yaxis_title="", coloraxis_showscale=False)
        st.plotly_chart(estilo(fig, 300, leyenda=False), use_container_width=True)
    with g2:
        st.dataframe(tipo[["Tipo","Eventos","% del total","Nivel"]],
                     use_container_width=True, hide_index=True, height=260)

    # --- NUEVO: Efectividad de pruebas técnicas ---
    pr = None
    if SAMPLE_PRUEBAS is not None:
        pr = _pr(SAMPLE_PRUEBAS)
    elif up_e is not None and getattr(up_e, "name", "").lower().endswith((".xlsx", ".xls")):
        try: pr = dl.cargar_pruebas(up_e)
        except Exception: pr = None
    if pr is not None:
        rp = dl.resumen_pruebas(pr)
        st.markdown("#### 🔧 Efectividad del seguimiento de pruebas técnicas")
        st.caption("Pruebas 1-a-1 a especialistas con incidencias y su mejora tras seguimiento.")
        c = st.columns(4)
        with c[0]: kpi("Pruebas realizadas", rp["realizadas"])
        with c[1]: kpi("Resultado inicial 'Malo'", rp["result_malo"], "", "red")
        with c[2]: kpi("Mejoraron a 'Bueno'", rp["mejoraron"], "tras seguimiento", "green")
        with c[3]: kpi("Tasa de mejora", f'{rp["pct_mejora"]:.0f}%', "de los 'Malo'", "green")

    # --- Ranking de especialistas ---
    st.markdown("#### 🏅 Ranking de especialistas")
    min_c = st.slider("Citas mínimas (evita % engañosos con pocas citas)", 0, 50, 20)
    base_e = esp_df[esp_df["Total Citas"] >= min_c].copy()
    tm = ["(todos)"] + sorted(esp_df["Talent Manager"].dropna().unique().tolist())
    tm_sel = st.selectbox("Talent Manager", tm)
    if tm_sel != "(todos)":
        base_e = base_e[base_e["Talent Manager"]==tm_sel]
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Top 12 por % de incidencia**")
        top = base_e.sort_values("% Inc.", ascending=False).head(12).copy()
        top["%"] = (top["% Inc."]*100).round(0)
        fig = px.bar(top.sort_values("%"), x="%", y="Especialista", orientation="h",
                     text="%", color_discrete_sequence=[WARN_RED])
        fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="% de citas con incidencia", yaxis_title="")
        st.plotly_chart(estilo(fig, 420, leyenda=False), use_container_width=True)
    with g2:
        met = st.selectbox("Métrica técnica", dl.METRICAS_TELEMETRIA)
        st.markdown(f"**Top 12 por {met}**")
        st.plotly_chart(barra_h(base_e.sort_values(met, ascending=False).head(12),
                                met, "Especialista", OY_BLUE, h=420), use_container_width=True)
    st.dataframe(base_e, use_container_width=True, hide_index=True, height=320)
    st.download_button("⬇️ Telemetría (CSV)", base_e.to_csv(index=False).encode("utf-8-sig"),
                       "telemetria_especialistas.csv", "text/csv")

# =====================================================================
# 9 · INSIGHTS & RECOMENDACIONES
# =====================================================================
with tabs[8]:
    st.markdown('<div class="intro">💡 <b>Lectura automática</b> de los datos de la vista '
                'activa + <b>acción sugerida</b> para cada hallazgo. Pensado para presentar '
                'a gerencia. Se actualiza con los filtros.</div>', unsafe_allow_html=True)
    ins = dl.generar_insights(df_view)
    orden = {"critico":0,"alerta":1,"ok":2,"info":3}
    ins = sorted(ins, key=lambda x: orden.get(x["nivel"], 9))
    n_crit = sum(1 for i in ins if i["nivel"]=="critico")
    n_al = sum(1 for i in ins if i["nivel"]=="alerta")
    c = st.columns(3)
    with c[0]: kpi("Hallazgos críticos", n_crit, "requieren acción ya", "red")
    with c[1]: kpi("Alertas", n_al, "vigilar de cerca", "amber")
    with c[2]: kpi("Total de hallazgos", len(ins))
    st.markdown("####")
    for i in ins:
        st.markdown(f"""<div class="ins {i['nivel']}">
            <div class="t">{i['icono']} {i['titulo']}</div>
            <div class="d">{i['detalle']}</div>
            <div class="r">✅ <b>Acción:</b> {i['recomendacion']}</div></div>""",
            unsafe_allow_html=True)

st.divider()
st.caption("Dashboard de Incidencias Técnicas · Opción Yo · Streamlit · "
           "cifras validadas contra el reporte de mayo 2026.")
