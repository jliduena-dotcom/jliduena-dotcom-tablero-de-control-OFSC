"""
Dashboard de Avance Operativo — OFSC Field Service
====================================================
Reconstrucción en Streamlit del dashboard originalmente generado como
HTML estático (Chart.js). Migrado a Python/pandas para:
  - Poder mantenerlo y extenderlo en el lenguaje que estás aprendiendo.
  - Publicarlo gratis en Streamlit Community Cloud.
  - Actualizar los datos subiendo un nuevo CSV/Excel sin tocar código.

Autor original del HTML: generar_dashboard.py (no disponible en esta migración).
Esta versión: reconstruida a partir del esquema de datos decodificado del HTML.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN GENERAL
# ─────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Avance Operativo — OFSC",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# IMPORTANTE: ruta calculada relativa a la ubicación de ESTE archivo
# (Path(__file__).parent), no al directorio de trabajo del proceso.
# En Streamlit Cloud, cuando app.py vive en una subcarpeta, el working
# directory sigue siendo la raíz del repo — una ruta relativa tipo
# "data/dashboard_data.csv" fallaría con FileNotFoundError.
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "dashboard_data.csv"
PROY_SERVICIOS_FACTOR = 1.63  # constante original: servicios proyectados por instalación

COLUMNAS_ESPERADAS = [
    "ciudad", "empresa", "franja", "grupo", "estado", "red_tecnologia",
    "razon_no_completado", "gestionado", "fecha", "canal", "red_tipo",
    "subtipo", "tecnico",
]

GRUPO_COLORES = {
    "Instalaciones": "#2563EB", "Arreglos": "#059669", "Postventa": "#7C3AED",
    "Traslados": "#D97706", "Desconexiones": "#DC2626", "Otros": "#0891B2",
}


# ─────────────────────────────────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────────────────────────────────
@st.cache_data
def cargar_datos(path_or_buffer) -> pd.DataFrame:
    if hasattr(path_or_buffer, "name") and path_or_buffer.name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(path_or_buffer)
    else:
        df = pd.read_csv(path_or_buffer)

    faltantes = [c for c in COLUMNAS_ESPERADAS if c not in df.columns]
    if faltantes:
        st.error(
            "El archivo cargado no tiene las columnas esperadas. "
            f"Faltan: {', '.join(faltantes)}"
        )
        st.stop()

    # Normalizaciones
    if df["gestionado"].dtype == object:
        df["gestionado"] = df["gestionado"].astype(str).str.lower().isin(["true", "1", "si", "sí"])
    df["gestionado"] = df["gestionado"].astype(bool)
    df["razon_no_completado"] = df["razon_no_completado"].fillna("")
    df["empresa"] = df["empresa"].fillna("Sin empresa")
    return df


# ─────────────────────────────────────────────────────────────────────────
# FUNCIONES DE NEGOCIO (equivalentes a las del HTML original)
# ─────────────────────────────────────────────────────────────────────────
def efectividad(df: pd.DataFrame) -> float:
    """Completado / (Completado + No completado) * 100"""
    comp = (df["estado"] == "Completado").sum()
    nocomp = (df["estado"] == "No completado").sum()
    denom = comp + nocomp
    return round(comp / denom * 100) if denom else 0


def proyeccion(df: pd.DataFrame) -> int:
    """Proyección de completadas = efectividad% * total de órdenes del grupo"""
    ef = efectividad(df) / 100
    return round(ef * len(df))


def pct(numerador: int, denominador: int) -> int:
    return round(numerador / denominador * 100) if denominador else 0


def badge_clase(pct_valor: int) -> str:
    if pct_valor >= 80:
        return "🟢"
    if pct_valor >= 50:
        return "🟡"
    return "🔴"


# ─────────────────────────────────────────────────────────────────────────
# SIDEBAR: CARGA DE ARCHIVO + FILTROS
# ─────────────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Datos y filtros")

archivo_subido = st.sidebar.file_uploader(
    "Actualizar datos (CSV o Excel)",
    type=["csv", "xlsx", "xls"],
    help=(
        "Sube un archivo con las columnas: "
        + ", ".join(COLUMNAS_ESPERADAS)
        + ". Si no subes nada, se usa el dataset de ejemplo incluido."
    ),
)

df = cargar_datos(archivo_subido) if archivo_subido is not None else cargar_datos(DATA_PATH)

st.sidebar.markdown("---")
st.sidebar.subheader("Filtros")


def multiselect_filtro(label, columna):
    opciones = sorted(df[columna].dropna().unique().tolist())
    seleccion = st.sidebar.multiselect(label, opciones)
    return seleccion


f_ciudad = multiselect_filtro("Ciudad", "ciudad")
f_empresa = multiselect_filtro("Compañía / Aliado", "empresa")
f_franja = multiselect_filtro("Franja (AM/PM)", "franja")
f_grupo = multiselect_filtro("Tipo de trabajo (grupo)", "grupo")
f_estado = multiselect_filtro("Estado", "estado")
f_red = multiselect_filtro("Red / Tecnología", "red_tecnologia")
f_canal = multiselect_filtro("Canal", "canal")
f_naptipo = multiselect_filtro("Red neutra / Red Claro", "red_tipo")
f_subtipo = multiselect_filtro("Subtipo", "subtipo")

data = df.copy()
for col, seleccion in [
    ("ciudad", f_ciudad), ("empresa", f_empresa), ("franja", f_franja),
    ("grupo", f_grupo), ("estado", f_estado), ("red_tecnologia", f_red),
    ("canal", f_canal), ("red_tipo", f_naptipo), ("subtipo", f_subtipo),
]:
    if seleccion:
        data = data[data[col].isin(seleccion)]

if st.sidebar.button("🔄 Restablecer filtros"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"Registros totales: {len(df):,} · Con filtros: {len(data):,}")

# ─────────────────────────────────────────────────────────────────────────
# ENCABEZADO
# ─────────────────────────────────────────────────────────────────────────
col_title, col_badge = st.columns([5, 1])
with col_title:
    st.title("📊 Dashboard Avance Operativo — OFSC")
    st.caption("Migración a Streamlit del dashboard original (HTML/Chart.js)")
with col_badge:
    if "fecha" in data.columns and data["fecha"].notna().any():
        st.metric("Fecha", str(data["fecha"].max()))

tab_dash, tab_proy, tab_resumen, tab_tec = st.tabs(
    ["📊 Dashboard", "📆 Proyección", "🎯 Resumen Ejecutivo", "👥 Control Técnicos"]
)

# ─────────────────────────────────────────────────────────────────────────
# TAB 1: DASHBOARD
# ─────────────────────────────────────────────────────────────────────────
with tab_dash:
    if data.empty:
        st.warning("No hay registros para los filtros seleccionados.")
    else:
        am = data[data["franja"] == "AM"]
        pm = data[data["franja"] == "PM"]
        am_gest = am["gestionado"].sum()
        pm_gest = pm["gestionado"].sum()

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total órdenes", f"{len(data):,}")
        c2.metric("Avance AM", f"{pct(am_gest, len(am))}%", help="% gestionadas en franja AM")
        c3.metric("Avance PM", f"{pct(pm_gest, len(pm))}%", help="% gestionadas en franja PM")
        c4.metric("Avance global", f"{pct(am_gest + pm_gest, len(data))}%")
        c5.metric("Efectividad", f"{efectividad(data)}%", help="Completado / (Completado + No completado)")

        st.markdown("---")

        colA, colB = st.columns(2)

        with colA:
            st.subheader("Distribución por franja horaria")
            df_franja = pd.DataFrame({
                "Franja": ["AM gestionadas", "AM pendientes", "PM gestionadas", "PM pendientes"],
                "Cantidad": [am_gest, len(am) - am_gest, pm_gest, len(pm) - pm_gest],
            })
            fig = px.bar(df_franja, x="Franja", y="Cantidad", color="Franja",
                         color_discrete_sequence=["#2563EB", "#93C5FD", "#F59E0B", "#FDE68A"])
            fig.update_layout(showlegend=False, height=320)
            st.plotly_chart(fig, use_container_width=True)

        with colB:
            st.subheader("Órdenes en proceso por estado")
            en_proceso = data[data["estado"].isin(["Iniciado", "Pendiente", "en ruta"])]
            conteo = en_proceso["estado"].value_counts().reindex(["Iniciado", "Pendiente", "en ruta"]).fillna(0)
            fig2 = px.bar(x=conteo.index, y=conteo.values, labels={"x": "Estado", "y": "Cantidad"},
                          color=conteo.index, color_discrete_sequence=["#0891B2", "#F59E0B", "#7C3AED"])
            fig2.update_layout(showlegend=False, height=320)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        st.subheader("Avance por tipo de trabajo (% gestionado AM · PM)")
        filas = []
        for grupo, sub in data.groupby("grupo"):
            sam = sub[sub["franja"] == "AM"]
            spm = sub[sub["franja"] == "PM"]
            filas.append({"Grupo": grupo, "AM %": pct(sam["gestionado"].sum(), len(sam)),
                          "PM %": pct(spm["gestionado"].sum(), len(spm))})
        df_grupo = pd.DataFrame(filas)
        if not df_grupo.empty:
            fig3 = go.Figure()
            fig3.add_bar(name="AM %", x=df_grupo["Grupo"], y=df_grupo["AM %"], marker_color="#2563EB")
            fig3.add_bar(name="PM %", x=df_grupo["Grupo"], y=df_grupo["PM %"], marker_color="#F59E0B")
            fig3.update_layout(barmode="group", height=350)
            st.plotly_chart(fig3, use_container_width=True)

        st.markdown("---")
        colC, colD = st.columns(2)

        with colC:
            st.subheader("Estado de órdenes por compañía")
            vista = st.radio("Vista", ["Total", "AM", "PM"], horizontal=True, key="vista_comp")
            sub = data if vista == "Total" else data[data["franja"] == vista]
            tabla = pd.crosstab(sub["empresa"], sub["estado"])
            if not tabla.empty:
                fig4 = px.bar(tabla, barmode="stack", height=380)
                fig4.update_layout(xaxis_title="Compañía", yaxis_title="Órdenes", legend_title="Estado")
                st.plotly_chart(fig4, use_container_width=True)

        with colD:
            st.subheader("Aliados operativos — % avance por franja")
            filas2 = []
            for emp, sub in data.groupby("empresa"):
                sam = sub[sub["franja"] == "AM"]
                spm = sub[sub["franja"] == "PM"]
                filas2.append({"Empresa": emp, "AM %": pct(sam["gestionado"].sum(), len(sam)),
                              "PM %": pct(spm["gestionado"].sum(), len(spm))})
            df_ali = pd.DataFrame(filas2)
            if not df_ali.empty:
                fig5 = go.Figure()
                fig5.add_bar(name="AM %", x=df_ali["Empresa"], y=df_ali["AM %"], marker_color="#2563EB")
                fig5.add_bar(name="PM %", x=df_ali["Empresa"], y=df_ali["PM %"], marker_color="#F59E0B")
                fig5.update_layout(barmode="group", height=380)
                st.plotly_chart(fig5, use_container_width=True)

        st.markdown("---")
        colE, colF = st.columns(2)

        with colE:
            st.subheader("🌐 Red Neutra — Pendientes e Instalaciones")
            rn = data[data["red_tipo"] == "Red neutra"]
            rn_pend = rn[rn["estado"] == "Pendiente"]
            k1, k2, k3 = st.columns(3)
            k1.metric("Total c/Nap", len(rn))
            k2.metric("Pendientes", len(rn_pend))
            k3.metric("Gestionados", int(rn["gestionado"].sum()))

            rn_inst = rn[rn["grupo"] == "Instalaciones"]
            if not rn_inst.empty:
                conteo_inst = rn_inst["estado"].value_counts()
                fig6 = px.pie(values=conteo_inst.values, names=conteo_inst.index,
                              title="Instalaciones con Nap por estado")
                fig6.update_layout(height=320)
                st.plotly_chart(fig6, use_container_width=True)

        with colF:
            st.subheader("Razón de no realización")
            no_comp = data[(data["estado"] == "No completado") & (data["razon_no_completado"] != "")]
            if not no_comp.empty:
                conteo_razon = no_comp["razon_no_completado"].value_counts()
                fig7 = px.bar(x=conteo_razon.values, y=conteo_razon.index, orientation="h",
                             labels={"x": "Cantidad", "y": ""}, color_discrete_sequence=["#DC2626"])
                fig7.update_layout(height=320)
                st.plotly_chart(fig7, use_container_width=True)
            else:
                st.info("No hay causas de no realización registradas con los filtros actuales.")

        st.markdown("---")
        st.subheader("Detalle por ciudad y compañía")
        detalle = []
        for (ciudad, empresa_n), sub in data.groupby(["ciudad", "empresa"]):
            sam = sub[sub["franja"] == "AM"]
            spm = sub[sub["franja"] == "PM"]
            am_g, pm_g = sam["gestionado"].sum(), spm["gestionado"].sum()
            detalle.append({
                "Ciudad": ciudad, "Compañía": empresa_n,
                "AM total": len(sam), "AM gest.": am_g, "AM %": pct(am_g, len(sam)),
                "PM total": len(spm), "PM gest.": pm_g, "PM %": pct(pm_g, len(spm)),
                "Total": len(sub), "Avance": pct(am_g + pm_g, len(sub)),
            })
        df_detalle = pd.DataFrame(detalle).sort_values("Total", ascending=False)
        st.dataframe(df_detalle, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────
# TAB 2: PROYECCIÓN
# ─────────────────────────────────────────────────────────────────────────
with tab_proy:
    if data.empty:
        st.warning("No hay registros para los filtros seleccionados.")
    else:
        st.caption(
            "Proyección = Efectividad% × Total de órdenes del segmento. "
            "Réplica exacta de la fórmula original del dashboard."
        )

        st.subheader("Proyección por tipo de trabajo")
        cols = st.columns(3)
        i = 0
        for grupo, sub in data.groupby("grupo"):
            ef, proy = efectividad(sub), proyeccion(sub)
            with cols[i % 3]:
                st.metric(grupo, f"{proy} / {len(sub)}", f"{ef}% efectividad")
            i += 1

        st.markdown("---")
        st.subheader("Proyección por aliado operativo")
        cols2 = st.columns(3)
        i = 0
        for emp, sub in data.groupby("empresa"):
            ef, proy = efectividad(sub), proyeccion(sub)
            with cols2[i % 3]:
                st.metric(emp, f"{proy} / {len(sub)}", f"{ef}% efectividad")
            i += 1

        st.markdown("---")
        st.subheader("Proyección por ciudad y compañía")
        filas_p = []
        for (ciudad, empresa_n), sub in data.groupby(["ciudad", "empresa"]):
            comp_n = (sub["estado"] == "Completado").sum()
            nocomp_n = (sub["estado"] == "No completado").sum()
            ini = (sub["estado"] == "Iniciado").sum()
            pend = (sub["estado"] == "Pendiente").sum()
            ruta = (sub["estado"] == "en ruta").sum()
            canc = (sub["estado"] == "Cancelado").sum()
            ef = efectividad(sub)
            proy = proyeccion(sub)
            filas_p.append({
                "Ciudad": ciudad, "Compañía": empresa_n, "Total": len(sub),
                "Complet.": comp_n, "No Complet.": nocomp_n, "Inic.": ini,
                "Pend.": pend, "En Ruta": ruta, "Cancel.": canc,
                "Efect. %": ef, "Proyecc.": proy,
                "Proy. Servicios": round(proy * PROY_SERVICIOS_FACTOR),
            })
        df_proy = pd.DataFrame(filas_p).sort_values("Total", ascending=False)
        st.dataframe(df_proy, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────
# TAB 3: RESUMEN EJECUTIVO
# ─────────────────────────────────────────────────────────────────────────
with tab_resumen:
    if data.empty:
        st.warning("No hay registros para los filtros seleccionados.")
    else:
        st.subheader("Métricas globales")
        inst = data[data["grupo"] == "Instalaciones"]
        inst_ef = efectividad(inst) / 100 if len(inst) else 0
        inst_proy = round(inst_ef * len(inst))
        proy_serv = round(inst_proy * PROY_SERVICIOS_FACTOR)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total órdenes", f"{len(data):,}")
        c2.metric("Efectividad global", f"{efectividad(data)}%")
        c3.metric("Instalaciones proyectadas", f"{inst_proy:,}")
        c4.metric("Proy. Servicios", f"{proy_serv:,}", "Install. proyect. × 1.63")

        st.markdown("---")
        colG, colH = st.columns(2)

        with colG:
            st.subheader("Instalaciones proyectadas por canal")
            if not inst.empty:
                filas_c = []
                for canal, sub in inst.groupby("canal"):
                    ef = efectividad(sub) / 100
                    filas_c.append({"Canal": canal, "Proyección": round(ef * len(sub))})
                df_canal = pd.DataFrame(filas_c).sort_values("Proyección", ascending=False)
                fig8 = px.bar(df_canal, x="Canal", y="Proyección", color_discrete_sequence=["#7C3AED"])
                fig8.update_layout(height=350)
                st.plotly_chart(fig8, use_container_width=True)
            else:
                st.info("No hay instalaciones con los filtros actuales.")

        with colH:
            st.subheader("Efectividad por compañía")
            filas_e = [{"Empresa": emp, "Efectividad %": efectividad(sub)}
                       for emp, sub in data.groupby("empresa")]
            df_ef = pd.DataFrame(filas_e).sort_values("Efectividad %", ascending=False)
            fig9 = px.bar(df_ef, x="Empresa", y="Efectividad %", color_discrete_sequence=["#059669"])
            fig9.update_layout(height=350)
            st.plotly_chart(fig9, use_container_width=True)

        st.markdown("---")
        st.subheader("Efectividad por tipo de trabajo")
        filas_g = [{"Grupo": grupo, "Efectividad %": efectividad(sub)}
                   for grupo, sub in data.groupby("grupo")]
        df_efg = pd.DataFrame(filas_g).sort_values("Efectividad %", ascending=False)
        fig10 = px.bar(df_efg, x="Grupo", y="Efectividad %",
                       color="Grupo", color_discrete_map=GRUPO_COLORES)
        fig10.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig10, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────
# TAB 4: CONTROL TÉCNICOS
# ─────────────────────────────────────────────────────────────────────────
with tab_tec:
    if data.empty:
        st.warning("No hay registros para los filtros seleccionados.")
    else:
        st.subheader("Ranking de técnicos")

        col_orden, col_busq = st.columns([1, 2])
        with col_orden:
            orden = st.selectbox("Ordenar por", ["Total órdenes", "Instalaciones", "Efectividad"])
        with col_busq:
            busqueda = st.text_input("Buscar técnico", placeholder="Nombre técnico...")

        filas_t = []
        for tecnico, sub in data.groupby("tecnico"):
            if not tecnico:
                continue
            estados_count = sub["estado"].value_counts()
            grupos_count = sub["grupo"].value_counts()
            filas_t.append({
                "Técnico": tecnico,
                "Compañía": sub["empresa"].mode().iat[0] if not sub["empresa"].mode().empty else "",
                "Ciudad": sub["ciudad"].mode().iat[0] if not sub["ciudad"].mode().empty else "",
                "Total": len(sub),
                "Complet.": estados_count.get("Completado", 0),
                "No Comp.": estados_count.get("No completado", 0),
                "Inic.": estados_count.get("Iniciado", 0),
                "Pend.": estados_count.get("Pendiente", 0),
                "En Ruta": estados_count.get("en ruta", 0),
                "Cancel.": estados_count.get("Cancelado", 0),
                "Inst.": grupos_count.get("Instalaciones", 0),
                "Arregl.": grupos_count.get("Arreglos", 0),
                "Postv.": grupos_count.get("Postventa", 0),
                "Trasl.": grupos_count.get("Traslados", 0),
                "Descon.": grupos_count.get("Desconexiones", 0),
                "Otros": grupos_count.get("Otros", 0),
                "R.Neutra": (sub["red_tipo"] == "Red neutra").sum(),
                "Efectividad": efectividad(sub),
            })
        df_tec = pd.DataFrame(filas_t)

        if busqueda:
            df_tec = df_tec[df_tec["Técnico"].str.contains(busqueda, case=False, na=False)]

        columna_orden = {"Total órdenes": "Total", "Instalaciones": "Inst.", "Efectividad": "Efectividad"}[orden]
        df_tec = df_tec.sort_values(columna_orden, ascending=False).reset_index(drop=True)
        df_tec.index = df_tec.index + 1

        st.dataframe(df_tec, use_container_width=True)
        st.caption(f"{len(df_tec)} técnicos con órdenes asignadas (filtros actuales).")

st.markdown("---")
st.caption(
    "Migrado desde el dashboard HTML original a Streamlit. "
    "Actualiza los datos desde la barra lateral (CSV/Excel) sin necesidad de tocar el código."
)
