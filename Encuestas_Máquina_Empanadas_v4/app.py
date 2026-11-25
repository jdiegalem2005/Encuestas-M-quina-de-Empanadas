from pathlib import Path
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modelo import (
    cargar_encuesta,
    crear_registro_encuesta,
    guardar_respuesta_adicional,
    siguiente_registro_id,
    filtrar_productores,
    indicadores_generales,
    tabla_frecuencias,
    tabla_prioridades,
    tabla_productividad,
    resumen_mercado,
    proyectar_ciclo_vida,
    calcular_finanzas,
    matriz_requerimientos,
    tabla_calidad_datos,
    ESCENARIOS_COMERCIALES,
    MERCADO_REFERENCIA_QUITO,
    URL_FUENTE_MERCADO,
)

NOMBRE_MAQUINA = "PaFREIR"  # Cambiar aquí el nombre visible de la aplicación.
BASE = Path(__file__).parent
ARCHIVO_BASE = BASE / "encuesta_real.csv"
ARCHIVO_ADICIONALES = BASE / "respuestas_adicionales.csv"
ARCHIVO_ORIGINAL = BASE / "encuesta_original_anonimizada.csv"

st.set_page_config(
    page_title=f"{NOMBRE_MAQUINA} | Del mercado al diseño",
    page_icon="🥟",
    layout="wide",
)

st.markdown("""
<style>
.stApp { background: #f5f7f8; }
h1, h2, h3 { color: #173b3b; }
div[data-testid="stMetric"] {
  background: white; padding: 14px 16px; border-radius: 12px;
  border: 1px solid #dce6e3;
}
div[data-testid="stMetricValue"] { color: #174f49; }
div[data-testid="stDataFrame"] { background: white; }
.small-note { color: #64748b; font-size: 0.86rem; }
</style>
""", unsafe_allow_html=True)


def cargar_base_actualizada() -> pd.DataFrame:
    """Lee la base inicial y las respuestas adicionales guardadas localmente."""
    return cargar_encuesta(ARCHIVO_BASE, ARCHIVO_ADICIONALES)


def registrar_respuesta(respuesta: dict, df_actual: pd.DataFrame) -> None:
    fila = crear_registro_encuesta(respuesta, siguiente_registro_id(df_actual))
    guardar_respuesta_adicional(fila, ARCHIVO_ADICIONALES)


real = cargar_base_actualizada()
originales = pd.read_csv(ARCHIVO_ORIGINAL, encoding="utf-8-sig") if ARCHIVO_ORIGINAL.exists() else None
productores_reales = filtrar_productores(real)
indicadores_base = indicadores_generales(real)
resumen_encuesta = resumen_mercado(real)
precio_mediano_encuesta = indicadores_base["precio_mediano"]
precio_default = 300.0  # Precio de venta elegido para el escenario académico; mediana de encuesta: USD 350.

st.title(f"{NOMBRE_MAQUINA} · del mercado al diseño")
st.caption(f"Diseño de Máquinas · Máquina semiautomática para empanadas de verde · Quito · Horizonte comercial de 48 meses")
st.info("La aplicación utiliza exclusivamente las 100 respuestas reales y anonimizadas de la encuesta realizada, realizada en Quito. Los escenarios comerciales y económicos son supuestos académicos editables; no son respuestas simuladas ni ventas observadas.")

mensaje = st.session_state.pop("mensaje_encuesta", None)
if mensaje:
    st.success(mensaje)

# -------------------------
# Parámetros globales
# -------------------------
with st.sidebar:
    st.header("Configuración del análisis")
    escenario = st.selectbox("Escenario de supuestos comerciales", list(ESCENARIOS_COMERCIALES.keys()), index=1)
    preset = ESCENARIOS_COMERCIALES[escenario]

    st.divider()
    st.subheader("Mercado objetivo · Quito")
    establecimientos = st.number_input(
        "Establecimientos de alimentos y bebidas (referencia)",
        min_value=0, max_value=1000000, value=MERCADO_REFERENCIA_QUITO, step=100,
        help="Referencia del catastro turístico de junio de 2024. No equivale al número comprobado de negocios que venden empanadas de verde."
    )
    pct_elabora = st.slider(
        "Porcentaje que podría elaborar empanadas de verde",
        min_value=0, max_value=100, value=int(preset["pct_elabora"] * 100), step=1,
        key=f"elabora_{escenario}",
        help="Supuesto editable. La encuesta no permite estimar este porcentaje para todos los establecimientos de Quito."
    ) / 100
    pct_volumen = st.slider(
        "Porcentaje del segmento de 20–50 empanadas/día",
        min_value=0.0, max_value=100.0, value=float(preset["pct_volumen"] * 100), step=0.1,
        key=f"volumen_{escenario}",
        help="Referencia observada: 12 de 56 productores (21,4 %) declararon producir entre 20 y 50 empanadas al día. Se utiliza como segmento objetivo inicial."
    ) / 100
    cobertura_48m = st.slider(
        "Cobertura comercial del mercado objetivo en 48 meses",
        min_value=0, max_value=100, value=int(preset["cobertura_48m"] * 100), step=1,
        key=f"cobertura_{escenario}",
        help="Porcentaje del mercado objetivo al que se estima que la empresa podría llegar comercialmente."
    ) / 100
    conversion = st.slider(
        "Conversión de interés en compra efectiva",
        min_value=0, max_value=100, value=int(preset["conversion"] * 100), step=1,
        key=f"conversion_{escenario}",
        help="Supuesto de escenario. No debe confundirse con el porcentaje de encuestados que declaró intención de compra."
    ) / 100
    if preset["intencion_tipo"] == "compra_12m":
        intencion_base = resumen_encuesta["compra_12m_pct"]
        texto_intencion = "Compra declarada durante los primeros 12 meses"
    else:
        intencion_base = resumen_encuesta["intencion_cualquier_momento_pct"]
        texto_intencion = "Compra declarada en algún momento"
    intencion_compra = st.slider(
        "Intención de compra utilizada",
        min_value=0.0, max_value=100.0, value=round(float(intencion_base), 1), step=0.1,
        key=f"intencion_{escenario}",
        help=f"Se toma como referencia {texto_intencion.lower()} en la encuesta. El porcentaje es editable como supuesto del escenario."
    ) / 100
    cap_maquinas_mes = st.number_input(
        "Capacidad de fabricación comercial (máquinas/mes)",
        min_value=0, max_value=500, value=int(preset["cap_maquinas_mes"]), step=1,
        help="Capacidad hipotética para fabricar y entregar máquinas; es diferente de las empanadas por hora que produce cada equipo."
    )

    st.divider()
    st.subheader("Capacidad técnica de la máquina")
    capacidad_min = st.number_input(
        "Capacidad mínima (empanadas/h)", min_value=1, max_value=500,
        value=20, step=1, key="capacidad_min_emp_h"
    )
    capacidad_max = st.number_input(
        "Capacidad máxima (empanadas/h)", min_value=1, max_value=500,
        value=50, step=1, key="capacidad_max_emp_h"
    )
    if capacidad_max < capacidad_min:
        st.warning("La capacidad máxima no puede ser menor que la mínima. Se igualó temporalmente a la mínima.")
        capacidad_max = capacidad_min
    if capacidad_min < capacidad_max:
        capacidad_emp_h = st.slider(
            "Capacidad seleccionada para el análisis",
            min_value=int(capacidad_min), max_value=int(capacidad_max),
            value=int((capacidad_min + capacidad_max) // 2), step=1,
            key=f"capacidad_seleccionada_{capacidad_min}_{capacidad_max}"
        )
    else:
        capacidad_emp_h = int(capacidad_min)
        st.metric("Capacidad seleccionada", f"{capacidad_emp_h} emp/h")
    horas_dia = st.number_input("Horas de operación por día", 1, 16, 4, 1)
    dias_mes = st.number_input("Días de operación por mes", 1, 31, 22, 1)

    st.divider()
    st.subheader("Supuestos económicos · USD")
    inversion_prototipo = st.number_input(
        "Costo estimado del prototipo", 0.0, 100000.0, 400.0, 25.0,
        help="Presupuesto académico del prototipo. No incluye el compresor externo."
    )
    st.caption("Referencia adicional: compresor externo estimado en aproximadamente USD 60; no está incluido en los USD 400 del prototipo.")
    precio_venta = st.number_input(
        "Precio de venta por máquina", 0.0, 100000.0, 300.0, 10.0,
        help="Precio elegido para el escenario académico. La mediana de disposición de pago de la encuesta es USD 350."
    )
    costo_unitario = st.number_input(
        "Costo comercial unitario estimado", 0.0, 100000.0, 200.0, 10.0,
        help="Supuesto académico para una unidad adicional, considerando estandarización y reutilización de recursos; pendiente de cotización."
    )
    costos_fijos_mes = st.number_input(
        "Costos fijos mensuales", 0.0, 100000.0, 25.0, 5.0,
        help="Estimación simplificada para una operación pequeña con instalaciones y recursos compartidos."
    )
    st.caption("Referencia de USD 25/mes: administración y comunicaciones $8, promoción $7, uso compartido de instalaciones/servicios $5 y reserva de mantenimiento menor $5.")
    crecimiento_costos = st.slider("Incremento anual de costos", 0.0, 0.30, 0.03, 0.01)
    variacion_precio = st.slider("Variación anual del precio", -0.20, 0.30, 0.0, 0.01)
    descuento = st.slider("Tasa de descuento anual", 0.0, 0.50, 0.12, 0.01)

# El análisis de encuestas siempre utiliza el conjunto real completo.
intencion_pct = intencion_compra
p_mercado = {
    "establecimientos_base": int(establecimientos),
    "pct_elabora": pct_elabora,
    "pct_volumen": pct_volumen,
    "cobertura_48m": cobertura_48m,
    "intencion_compra_pct": intencion_pct,
    "conversion": conversion,
    "cap_maquinas_mes": int(cap_maquinas_mes),
}
tabla_ciclo, resumen_ciclo = proyectar_ciclo_vida(p_mercado)
p_finanzas = {
    "precio_venta": precio_venta,
    "costo_unitario": costo_unitario,
    "costos_fijos_mes": costos_fijos_mes,
    "inversion_prototipo": inversion_prototipo,
    "crecimiento_costos_anual": crecimiento_costos,
    "variacion_precio_anual": variacion_precio,
    "tasa_descuento_anual": descuento,
}
tabla_finanzas, resumen_finanzas = calcular_finanzas(tabla_ciclo, p_finanzas)

# -------------------------
# Encabezado de indicadores
# -------------------------
ind_real = indicadores_generales(real)
cols = st.columns(4)
cols[0].metric("Respuestas recopiladas", f"{len(real):,}")
cols[1].metric("Productores", f"{len(productores_reales):,}")
cols[2].metric(
    "Productividad manual mediana",
    f"{ind_real['productividad_mediana']:.1f} emp/h" if np.isfinite(ind_real["productividad_mediana"]) else "Sin dato"
)
cols[3].metric("Mercado objetivo estimado", f"{resumen_ciclo['mercado_objetivo']:,.0f}")

# -------------------------
# Pestañas
# -------------------------
tabs = st.tabs([
    "1 · Encuestas",
    "2 · Análisis de mercado",
    "3 · Demanda y ciclo comercial",
    "4 · Costos y rentabilidad",
    "5 · Sensibilidad",
    "6 · Diseño y requerimientos",
])

with tabs[0]:
    st.subheader("Encuesta y base de respuestas")
    st.write("Cuestionario anónimo dirigido a personas y establecimientos que preparan empanadas de verde para comercializarlas. No se solicitan nombres ni correos electrónicos.")

    a, b, c, d = st.columns(4)
    a.metric("Total de respuestas", len(real))
    b.metric("Preparan empanadas", len(productores_reales))
    c.metric("No preparan", len(real) - len(productores_reales))
    d.metric("No productores con respuestas posteriores", ind_real["no_productores_con_respuestas_posteriores"])

    with st.expander("＋ Registrar una nueva respuesta", expanded=st.session_state.get("encuesta_detalle_activo", False)):
        st.caption("La encuesta no solicita datos personales. Si la persona responde que no prepara empanadas de verde, el formulario termina después de la pregunta 3, igual que en el cuestionario original.")

        if "encuesta_detalle_activo" not in st.session_state:
            st.session_state["encuesta_detalle_activo"] = False

        if not st.session_state["encuesta_detalle_activo"]:
            with st.form("formulario_inicio_encuesta"):
                st.markdown("**Datos generales**")
                st.caption("Escriba las respuestas con el mismo texto utilizado en el Google Forms original.")
                edad = st.text_input("1. ¿En qué grupo de edad se encuentra?", placeholder="Ej. De 18 a 29 años.")
                estudios = st.text_input("2. ¿Cuál es el nivel de estudios más alto que ha cursado, aunque no lo haya terminado?", placeholder="Ej. Universidad o posgrado.")
                prepara = st.text_input("3. ¿Usted prepara empanadas de verde? Si responde «No», termina la encuesta.", placeholder="Ej. Sí, seguido. / Sí, algunas veces. / No.")
                continuar = st.form_submit_button("Continuar", type="primary")

            if continuar:
                faltantes = [nombre for nombre, valor in [
                    ("grupo de edad", edad), ("nivel de estudios", estudios), ("pregunta de filtro", prepara)
                ] if not valor.strip()]
                if faltantes:
                    st.error("Complete: " + ", ".join(faltantes) + ".")
                else:
                    parcial = {"edad": edad, "nivel_estudios": estudios, "prepara_empanadas": prepara}
                    if prepara.strip().lower().startswith(("no",)):
                        try:
                            registrar_respuesta(parcial, real)
                            st.session_state["mensaje_encuesta"] = "Respuesta anónima registrada correctamente. Se actualizaron los resultados."
                            st.rerun()
                        except Exception as exc:
                            st.error(f"No se pudo guardar la respuesta: {exc}")
                    else:
                        st.session_state["encuesta_parcial"] = parcial
                        st.session_state["encuesta_detalle_activo"] = True
                        st.rerun()
        else:
            st.info("Paso 2 de 2 · Complete las preguntas sobre preparación y posible adquisición de la máquina.")
            st.caption("Los campos de opciones se ingresan como texto para no inventar alternativas que no aparezcan en el cuestionario original. Copie la opción exacta del Google Forms. En la pregunta 11, separe las opciones seleccionadas con punto y coma.")
            with st.form("formulario_detalle_encuesta"):
                produccion = st.text_input("4. Cuando prepara empanadas, ¿cuántas hace aproximadamente al día?", placeholder="Ej. Menos de 20. / De 20 a 50.")
                rendimiento_constante = st.text_input("5. Cuando compra $1 de verde, ¿le alcanza para hacer siempre la misma cantidad de empanadas del mismo tamaño?", placeholder="Copie la opción exacta del cuestionario.")
                rendimiento = st.text_input("6. Aproximadamente, ¿cuántas empanadas obtiene con $1 de verde? Escriba la cantidad de empanadas o «No sabe».", placeholder="Ej. 10 o No sabe")
                tiempo = st.text_input("7. Desde que empieza a moler el verde ya cocinado hasta que termina de rellenar y cerrar las empanadas, ¿cuánto tiempo se demora? Sin contar la fritura.", placeholder="Ej. 30 minutos, 1h o 35m")
                cantidad = st.text_input("8. ¿Cuántas empanadas hace en ese tiempo?", placeholder="Ej. 10 o De 5 a 6")
                laboriosa = st.text_input("9. ¿Qué parte le toma más trabajo?", placeholder="Copie la opción exacta del cuestionario.")
                utilidad = st.text_input("10. ¿Cuánto le serviría una máquina así en su negocio?", placeholder="Ej. Mucho.")
                prioridades_texto = st.text_area("11. ¿Qué sería lo más importante para usted? Elija hasta dos.", placeholder="Escriba cada opción exactamente como aparece y sepárelas con punto y coma.")
                momento = st.text_input("12. Si funcionara bien y tuviera un precio que pudiera pagar, ¿cuándo pensaría comprarla?", placeholder="Copie la opción exacta del cuestionario.")
                precio = st.text_input("13. Viéndola funcionar bien, ¿cuánto podría pagar como máximo?", placeholder="Ej. 200, No sabe todavía o No la compraría")
                barrera = st.text_input("14. ¿Qué lo detendría de comprarla?", placeholder="Copie la opción exacta del cuestionario.")
                abandono = st.text_input("15. Si ya tuviera la máquina, ¿qué motivo principal haría que dejara de usarla?", placeholder="Copie la opción exacta del cuestionario.")
                sugerencias = st.text_area("16. ¿Tiene alguna sugerencia? Opcional.")
                enviar = st.form_submit_button("Guardar respuesta", type="primary")

            if enviar:
                prioridades = [x.strip() for x in prioridades_texto.split(";") if x.strip()]
                respuesta = {
                    **st.session_state.get("encuesta_parcial", {}),
                    "produccion_diaria_rango": produccion,
                    "rendimiento_verde_consistente": rendimiento_constante,
                    "rendimiento_empanadas_por_usd1_texto": rendimiento,
                    "tiempo_proceso_texto": tiempo,
                    "cantidad_proceso_texto": cantidad,
                    "parte_mas_laboriosa": laboriosa,
                    "utilidad_percibida": utilidad,
                    "prioridades": prioridades,
                    "momento_compra": momento,
                    "precio_maximo_texto": precio,
                    "barrera_compra": barrera,
                    "motivo_abandono": abandono,
                    "sugerencias": sugerencias,
                }
                try:
                    registrar_respuesta(respuesta, real)
                    st.session_state["encuesta_detalle_activo"] = False
                    st.session_state.pop("encuesta_parcial", None)
                    st.session_state["mensaje_encuesta"] = "Respuesta anónima registrada correctamente. La base y los indicadores se actualizaron."
                    st.rerun()
                except Exception as exc:
                    st.error(f"No se pudo guardar la respuesta: {exc}")

            if st.button("Cancelar registro", key="cancelar_registro_encuesta"):
                st.session_state["encuesta_detalle_activo"] = False
                st.session_state.pop("encuesta_parcial", None)
                st.rerun()

    st.markdown("#### Respuestas recopiladas")
    columnas_vista = [
        "codigo_anonimo", "edad", "nivel_estudios", "prepara_empanadas",
        "produccion_diaria_rango", "parte_mas_laboriosa", "utilidad_percibida",
        "momento_compra", "precio_maximo_texto", "barrera_compra",
        "motivo_abandono", "sugerencias",
    ]
    nombres_vista = {
        "codigo_anonimo": "Código anónimo",
        "edad": "Edad",
        "nivel_estudios": "Nivel de estudios",
        "prepara_empanadas": "Prepara empanadas",
        "produccion_diaria_rango": "Producción diaria",
        "parte_mas_laboriosa": "Etapa más laboriosa",
        "utilidad_percibida": "Utilidad percibida",
        "momento_compra": "Momento de compra",
        "precio_maximo_texto": "Precio máximo declarado",
        "barrera_compra": "Barrera de compra",
        "motivo_abandono": "Motivo de abandono",
        "sugerencias": "Sugerencias",
    }
    st.dataframe(
        real[[c for c in columnas_vista if c in real.columns]].rename(columns=nombres_vista),
        use_container_width=True, hide_index=True
    )
    st.download_button(
        "Descargar base normalizada y anonimizada (CSV)",
        real.to_csv(index=False).encode("utf-8-sig"),
        "encuesta_empanamaq_normalizada_anonimizada.csv",
        "text/csv"
    )
    if originales is not None:
        st.download_button(
            "Descargar respuestas originales anonimizadas (CSV)",
            originales.to_csv(index=False).encode("utf-8-sig"),
            "encuesta_original_100_anonimizada.csv",
            "text/csv"
        )
    st.caption("Las respuestas nuevas ingresadas desde esta instalación se guardan localmente en respuestas_adicionales.csv. Para que el formulario público conserve respuestas en Streamlit Cloud se debe conectar un almacenamiento externo persistente.")

    st.markdown("#### Calidad y trazabilidad de los datos")
    calidad = tabla_calidad_datos(real, originales)
    st.dataframe(calidad, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("Análisis de mercado")
    st.caption(f"Los análisis de necesidades y compra se calculan sobre las {len(productores_reales)} personas que declararon preparar empanadas de verde. El perfil de edad y estudios describe las {len(real)} respuestas de Quito.")
    dfm = productores_reales.copy()
    r = resumen_mercado(real)
    c1, c2, c3 = st.columns(3)
    c1.metric("Productores analizados", r["n"])
    c2.metric("Considera que le serviría mucho", f"{r['aceptacion_pct']:.1f}%")
    c3.metric("Declaró intención de compra", f"{r['intencion_cualquier_momento_pct']:.1f}%")

    if len(dfm):
        st.markdown("#### Perfil general de las personas encuestadas")
        perfil1, perfil2 = st.columns(2)
        with perfil1:
            edad_df = real["edad"].fillna("Sin respuesta").value_counts().rename_axis("Grupo de edad").reset_index(name="Frecuencia")
            st.plotly_chart(px.bar(edad_df, x="Grupo de edad", y="Frecuencia", title=f"Distribución por edad ({len(real)} respuestas)"), use_container_width=True)
        with perfil2:
            estudios_df = real["nivel_estudios"].fillna("Sin respuesta").value_counts().rename_axis("Nivel de estudios").reset_index(name="Frecuencia")
            st.plotly_chart(px.bar(estudios_df, x="Nivel de estudios", y="Frecuencia", title=f"Nivel de estudios ({len(real)} respuestas)"), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fprod = tabla_frecuencias(dfm, "produccion_diaria_rango")
            st.plotly_chart(px.bar(fprod, x="Respuesta", y="Frecuencia", title="Producción diaria declarada", text="Frecuencia"), use_container_width=True)
        with col2:
            flab = tabla_frecuencias(dfm, "parte_mas_laboriosa")
            st.plotly_chart(px.bar(flab, x="Respuesta", y="Frecuencia", title="Etapa más laboriosa del proceso", text="Frecuencia"), use_container_width=True)

        col_cons, col_yield = st.columns(2)
        with col_cons:
            fcons = tabla_frecuencias(dfm, "rendimiento_verde_consistente")
            st.plotly_chart(px.bar(fcons, x="Respuesta", y="Frecuencia", title="Consistencia del rendimiento al comprar verde"), use_container_width=True)
        with col_yield:
            rendimientos = pd.to_numeric(dfm["rendimiento_empanadas_por_usd1_estimado"], errors="coerce").dropna()
            if len(rendimientos):
                st.metric("Rendimiento mediano por USD 1 de verde", f"{rendimientos.median():.1f} empanadas", help=f"Calculado con {len(rendimientos)} respuestas numéricas comparables.")
                st.plotly_chart(px.histogram(pd.DataFrame({"Empanadas por USD 1 de verde": rendimientos}), x="Empanadas por USD 1 de verde", nbins=10, title="Rendimiento declarado por USD 1 de verde"), use_container_width=True)
            else:
                st.info("No hay respuestas numéricas comparables para este indicador.")

        col3, col4 = st.columns(2)
        with col3:
            futil = tabla_frecuencias(dfm, "utilidad_percibida")
            st.plotly_chart(px.pie(futil, names="Respuesta", values="Frecuencia", title="Utilidad percibida de la máquina"), use_container_width=True)
        with col4:
            fcompra = tabla_frecuencias(dfm, "momento_compra")
            st.plotly_chart(px.bar(fcompra, x="Respuesta", y="Frecuencia", title="Momento declarado de compra", text="Frecuencia"), use_container_width=True)

        col5, col6 = st.columns(2)
        with col5:
            prioridades = tabla_prioridades(dfm)
            st.plotly_chart(px.bar(prioridades.sort_values("Selecciones"), x="Selecciones", y="Prioridad", orientation="h", title="Características más valoradas"), use_container_width=True)
            st.dataframe(prioridades, use_container_width=True, hide_index=True)
        with col6:
            fbarrera = tabla_frecuencias(dfm, "barrera_compra")
            st.plotly_chart(px.bar(fbarrera, x="Respuesta", y="Frecuencia", title="Principales barreras de compra"), use_container_width=True)
            fabandono = tabla_frecuencias(dfm, "motivo_abandono")
            st.plotly_chart(px.bar(fabandono, x="Respuesta", y="Frecuencia", title="Motivos potenciales de abandono"), use_container_width=True)

        precios = pd.to_numeric(dfm.get("precio_maximo_usd_estimado"), errors="coerce").dropna()
        if len(precios):
            st.markdown("#### Disposición de pago declarada")
            x1, x2, x3 = st.columns(3)
            x1.metric("Respuestas numéricas", len(precios))
            x2.metric("Mediana", f"USD {precios.median():,.0f}")
            x3.metric("Promedio", f"USD {precios.mean():,.0f}")
            st.plotly_chart(px.histogram(pd.DataFrame({"Precio máximo (USD)": precios}), x="Precio máximo (USD)", nbins=12, title="Distribución de precios máximos declarados"), use_container_width=True)
            n_atipicos_precio = int(dfm.get("estado_precio", pd.Series(index=dfm.index, dtype=object)).astype(str).str.contains("Posible valor atípico", case=False, na=False).sum())
            st.caption(
                f"Se identificaron {n_atipicos_precio} posibles valores atípicos mediante la regla 1,5 × RIC. "
                "Se conservan en la base y en los gráficos; no se eliminan automáticamente."
            )
            n_precios_ge_300 = int((precios >= 300).sum())
            st.caption(
                f"Disposición de pago igual o superior a USD 300: {n_precios_ge_300} de {len(precios)} "
                f"respuestas numéricas ({100*n_precios_ge_300/len(precios):.1f}%)."
            )
    else:
        st.warning("Todavía no existen respuestas de personas que preparen empanadas.")

    st.markdown("#### Interpretación para el diseño")
    st.write("La encuesta permite identificar necesidades de los productores, pero no permite distinguir el tipo de establecimiento ni estimar directamente la proporción de negocios de Quito que vende empanadas de verde. Para esas variables se utilizan supuestos externos y editables.")

with tabs[2]:
    st.subheader("Productividad, demanda y ciclo comercial")
    st.caption("Esta pestaña proyecta la adopción comercial durante 48 meses. No sustituye el análisis ambiental del ciclo de vida del equipo que se realizará mediante OpenLCA.")
    st.markdown("#### Productividad del proceso actual frente a la máquina")
    prod = tabla_productividad(real)
    mediana_manual = float(prod["productividad_empanadas_h"].median()) if len(prod) else np.nan
    promedio_manual = float(prod["productividad_empanadas_h"].mean()) if len(prod) else np.nan
    produccion_dia_maquina = capacidad_emp_h * horas_dia
    produccion_mes_maquina = produccion_dia_maquina * dias_mes
    a, b, c, d = st.columns(4)
    a.metric("Productividad manual mediana", f"{mediana_manual:.1f} emp/h" if np.isfinite(mediana_manual) else "Sin dato")
    b.metric("Capacidad seleccionada", f"{capacidad_emp_h} emp/h")
    c.metric("Producción diaria estimada", f"{produccion_dia_maquina:,.0f} emp/día")
    d.metric("Producción mensual estimada", f"{produccion_mes_maquina:,.0f} emp/mes")
    comp = pd.DataFrame({
        "Proceso": ["Manual · mediana de encuesta", "Máquina · capacidad seleccionada"],
        "Empanadas por hora": [mediana_manual, capacidad_emp_h]
    })
    st.plotly_chart(px.bar(comp, x="Proceso", y="Empanadas por hora", title="Comparación de productividad por hora", text_auto=".1f"), use_container_width=True)
    st.caption(f"La capacidad se puede configurar entre {capacidad_min} y {capacidad_max} empanadas por hora. La producción diaria y mensual se calcula con las horas y días de operación configurados; debe validarse mediante tiempos de ciclo y pruebas.")

    st.divider()
    st.markdown("#### Estimación del mercado objetivo")
    st.markdown(f"Fuente del universo de referencia: [Consejo Nacional de Competencias / Catastro MINTUR, junio de 2024]({URL_FUENTE_MERCADO}). El registro incluye establecimientos turísticos de alimentos y bebidas; no identifica cuáles elaboran empanadas de verde.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Establecimientos de referencia", f"{resumen_ciclo['establecimientos_base']:,}")
    m2.metric("Podrían elaborar empanadas", f"{resumen_ciclo['establecimientos_empanadas']:,.0f}")
    m3.metric("Mercado objetivo filtrado", f"{resumen_ciclo['mercado_objetivo']:,.0f}")
    st.write(f"Con el escenario de proyección **{escenario}**, y utilizando una intención declarada de compra de **{resumen_ciclo['intencion_declarada_pct']:.1f}%**, la demanda teórica acumulada a 48 meses es de **{resumen_ciclo['demanda_total']:,} máquinas**. Después de aplicar la capacidad comercial mensual, las ventas estimadas son **{resumen_ciclo['ventas_total']:,} máquinas**.")
    st.plotly_chart(px.line(tabla_ciclo, x="Mes", y=["Demanda potencial de máquinas", "Ventas estimadas"], title="Demanda mensual y ventas limitadas por capacidad comercial"), use_container_width=True)
    st.plotly_chart(px.line(tabla_ciclo, x="Mes", y=["Demanda acumulada", "Ventas acumuladas"], title="Adopción acumulada durante el ciclo comercial"), use_container_width=True)
    etapa_anual = tabla_ciclo.groupby(["Año", "Etapa"], sort=False)[["Demanda potencial de máquinas", "Ventas estimadas", "Demanda no atendida"]].sum().reset_index()
    st.markdown("#### Resumen anual por etapa")
    st.dataframe(etapa_anual, use_container_width=True, hide_index=True)
    st.caption("La proyección aplica: establecimientos de referencia × porcentaje supuesto que elabora empanadas × segmento observado de 20–50 empanadas/día × cobertura × intención declarada × conversión. La curva contempla desarrollo (meses 1–6), introducción (7–12), crecimiento (13–24), madurez (25–36), saturación (37–42) y declive (43–48). Las ventas mensuales se muestran como unidades esperadas equivalentes para visualizar una curva gradual; no representan fracciones de máquinas físicas ni una predicción ajustada a ventas históricas.")
    st.download_button("Descargar proyección de demanda (48 meses)", tabla_ciclo.to_csv(index=False).encode("utf-8-sig"), "proyeccion_ciclo_comercial_48_meses.csv", "text/csv")

with tabs[3]:
    st.subheader("Costos y rentabilidad")
    st.warning("Supuestos académicos: prototipo USD 400 (sin compresor externo; referencia adicional USD 60), precio de venta USD 300, costo comercial unitario USD 200 y costos fijos USD 25/mes. El precio se encuentra por debajo de la mediana declarada de USD 350. El costo unitario y los costos fijos son estimaciones simplificadas, no cotizaciones definitivas.")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ingresos proyectados", f"USD {resumen_finanzas['ingresos_totales']:,.2f}")
    k2.metric("EBITDA acumulado", f"USD {resumen_finanzas['ebitda_total']:,.2f}")
    k3.metric("VAN", f"USD {resumen_finanzas['van']:,.2f}")
    k4.metric("Recuperación simple", f"Mes {resumen_finanzas['payback_mes']}" if resumen_finanzas["payback_mes"] else "No recupera en 48 meses")
    if precio_venta <= costo_unitario:
        st.error("El margen de contribución unitario es cero o negativo. Con estos supuestos no existe punto de equilibrio operativo positivo.")
    else:
        st.success(f"Margen de contribución unitario inicial: USD {resumen_finanzas['margen_unitario']:,.2f}.")
        if resumen_finanzas["punto_equilibrio_mensual"] is not None:
            st.write(f"Punto de equilibrio operativo aproximado: {resumen_finanzas['punto_equilibrio_mensual']:.1f} máquinas por mes, antes de recuperar la inversión inicial.")
    st.plotly_chart(px.line(tabla_finanzas, x="Mes", y=["Ingresos (USD)", "Costo variable (USD)", "Costos fijos (USD)", "EBITDA (USD)"], title="Proyección económica mensual"), use_container_width=True)
    st.plotly_chart(px.line(tabla_finanzas, x="Mes", y="Caja acumulada (USD)", title="Caja acumulada considerando inversión inicial"), use_container_width=True)
    st.dataframe(tabla_finanzas, use_container_width=True, hide_index=True)
    st.download_button("Descargar resultados económicos", tabla_finanzas.to_csv(index=False).encode("utf-8-sig"), "resultados_economicos_48_meses.csv", "text/csv")
    st.download_button(
        "Descargar supuestos económicos y comerciales",
        json.dumps({**p_mercado, **p_finanzas, "escenario_comercial": escenario,
                    "capacidad_min_empanadas_h": int(capacidad_min),
                    "capacidad_max_empanadas_h": int(capacidad_max),
                    "capacidad_seleccionada_empanadas_h": int(capacidad_emp_h)}, ensure_ascii=False, indent=2).encode("utf-8"),
        "supuestos_modelo.json", "application/json"
    )

with tabs[4]:
    st.subheader("Análisis de sensibilidad")
    st.write("Se evalúa cómo cambia el VAN cuando se modifican el precio de venta y el costo comercial unitario. Los demás supuestos se mantienen constantes.")
    factores_precio = [0.70, 0.85, 1.00, 1.15, 1.30]
    factores_costo = [0.70, 0.85, 1.00, 1.15, 1.30]
    filas = []
    for fp in factores_precio:
        for fc in factores_costo:
            pf = dict(p_finanzas)
            pf["precio_venta"] = precio_venta * fp
            pf["costo_unitario"] = costo_unitario * fc
            _, rf = calcular_finanzas(tabla_ciclo, pf)
            filas.append({"Precio relativo": f"{fp:.2f}x", "Costo relativo": f"{fc:.2f}x", "VAN (USD)": rf["van"]})
    sensibilidad = pd.DataFrame(filas)
    piv = sensibilidad.pivot(index="Costo relativo", columns="Precio relativo", values="VAN (USD)")
    fig = go.Figure(data=go.Heatmap(
        z=piv.values, x=piv.columns, y=piv.index, colorscale="RdYlGn",
        colorbar=dict(title="VAN USD"), text=np.round(piv.values, 0), texttemplate="%{text:,.0f}"
    ))
    fig.update_layout(title="VAN según variación de precio y costo unitario", xaxis_title="Precio de venta", yaxis_title="Costo comercial unitario")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sensibilidad, use_container_width=True, hide_index=True)
    st.caption("La sensibilidad es determinista: no asigna probabilidades a los escenarios ni representa intervalos de confianza.")

with tabs[5]:
    st.subheader("Del análisis de mercado a los requerimientos de diseño")
    st.markdown("#### Matriz de necesidades y módulos")
    req = matriz_requerimientos(real, int(capacidad_min), int(capacidad_max))
    st.dataframe(req.style.format({"Indicador observado (%)": "{:.1f}%"}), use_container_width=True, hide_index=True)
    st.caption(f"Los porcentajes se calculan sobre {len(productores_reales)} productores. La columna 'Fuente del indicador' aclara si el valor proviene de una prioridad seleccionada, una dificultad, un motivo de abandono o el volumen diario; no todos son ponderaciones QFD.")

    st.markdown("#### Concepto mecánico C1")
    modulos = pd.DataFrame([
        ["M1 · Molienda", "Molino comercial con transmisión", "Motor eléctrico", "Reducir esfuerzo de molienda; desmontaje y limpieza"],
        ["M2 · Acondicionamiento y dosificación", "Pistón, placa perforada, cámara y boquilla", "Cilindro neumático por evaluar", "Uniformidad de masa, porción y control de alimentación"],
        ["M3 · Aplanado y corte", "Disco aplanador y aro cortador", "Cilindro neumático por evaluar", "Diámetro de 125 mm y espesor objetivo de 3–4 mm"],
        ["M4 · Transporte", "Banda intermitente", "Motorreductor eléctrico", "Posicionamiento repetible y coordinación de estaciones"],
        ["M5 · Dosificación de queso", "Tolva, sinfín y boquilla", "Motorreductor eléctrico", "Dosis objetivo de 40 g; calibración pendiente"],
        ["M6 · Doblado y sellado", "Molde articulado y palanca", "Cilindro neumático por evaluar", "Centrado, presión de borde y bloqueo seguro durante retiro"],
    ], columns=["Módulo", "Solución C1", "Accionamiento híbrido preliminar", "Requerimiento / validación"])
    st.dataframe(modulos, use_container_width=True, hide_index=True)
    st.info("La propuesta híbrida mantiene motores en operaciones rotativas continuas o dosificadas (molienda, banda y sinfín) y estudia neumática para movimientos lineales o articulados (pistón, prensa y cierre). Es una arquitectura preliminar; compresor, cilindros, electroválvulas, preparación de aire y protecciones deben cotizarse y dimensionarse.")

    st.markdown("#### Parámetros iniciales del producto")
    producto = pd.DataFrame([
        ["Diámetro de tortilla", "125 mm", "Definición preliminar del documento modular"],
        ["Espesor", "3–4 mm", "Objetivo nominal: 3,5 mm"],
        ["Queso por empanada", "40 g", "Objetivo sujeto a calibración del sinfín"],
        ["Capacidad", f"{capacidad_min}–{capacidad_max} empanadas/h", "Rango configurable; validar mediante pruebas"],
        ["Presupuesto del prototipo", f"USD {inversion_prototipo:,.2f}", "Estimación inicial, pendiente de cotizaciones"],
    ], columns=["Parámetro", "Valor", "Condición"])
    st.dataframe(producto, use_container_width=True, hide_index=True)

    st.markdown("#### Pendientes para validar el diseño")
    st.markdown("""
- Medir el tiempo real de cada módulo y verificar si se alcanza la capacidad seleccionada.
- Calibrar la masa por porción y la dosis de queso.
- Verificar fuerza, carrera, torque, potencia y factor de seguridad de los mecanismos.
- Comparar el costo total de la arquitectura electromecánica y la híbrida electroneumática.
- Comprobar limpieza, desmontaje, seguridad del cierre y facilidad de mantenimiento.
- Confirmar el presupuesto mediante cotizaciones de componentes.
    """)

st.divider()
st.caption(f"{NOMBRE_MAQUINA} · aplicación académica. Las estadísticas se calculan con respuestas reales y anonimizadas recopiladas en Quito. El ciclo comercial proyectado y las estimaciones financieras son supuestos editables; no sustituyen el análisis ambiental del ciclo de vida mediante OpenLCA.")
