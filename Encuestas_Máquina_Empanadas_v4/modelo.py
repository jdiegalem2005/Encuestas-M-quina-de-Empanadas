"""Modelo de análisis de mercado y ciclo de vida para EmpanaMaq.

La aplicación utiliza exclusivamente respuestas reales de la encuesta.
Las proyecciones comerciales y económicas son supuestos editables, no respuestas
adicionales ni resultados observados.
"""
from __future__ import annotations

from pathlib import Path
import re
import unicodedata
import numpy as np
import pandas as pd

MESES = 48
MERCADO_REFERENCIA_QUITO = 6873
FUENTE_MERCADO = (
    "Consejo Nacional de Competencias, Estado actual de la función de desarrollo "
    "de actividades turísticas, julio de 2024; catastro MINTUR, junio de 2024. "
    "Reporta 6.873 registros de alimentos y bebidas para Quito. Es un universo "
    "de referencia turística, no el número comprobado de negocios que venden empanadas."
)
URL_FUENTE_MERCADO = "https://competencias.gob.ec/wp-content/uploads/2024/09/Informe_semestral_I24_TURISMO-005092024-signed.pdf"

# Escenarios de proyección comercial. No representan bases de encuestas diferentes.
ESCENARIOS_COMERCIALES = {
    "Conservador": {
        "pct_elabora": 0.10,
        "pct_volumen": 0.214,
        "cobertura_48m": 0.15,
        "intencion_tipo": "compra_12m",
        "conversion": 0.30,
        "cap_maquinas_mes": 2,
    },
    "Moderado": {
        "pct_elabora": 0.15,
        "pct_volumen": 0.214,
        "cobertura_48m": 0.25,
        "intencion_tipo": "cualquier_momento",
        "conversion": 0.40,
        "cap_maquinas_mes": 4,
    },
    "Optimista": {
        "pct_elabora": 0.20,
        "pct_volumen": 0.214,
        "cobertura_48m": 0.35,
        "intencion_tipo": "cualquier_momento",
        "conversion": 0.50,
        "cap_maquinas_mes": 6,
    },
}

PRIORIDADES = {
    "prioridad_calidad": "Calidad de las empanadas",
    "prioridad_facil_uso_limpieza": "Facilidad de uso y limpieza",
    "prioridad_precio": "Precio accesible",
    "prioridad_espacio": "Poco espacio ocupado",
    "prioridad_repuestos": "Reparación y repuestos",
}
PRIORIDAD_OPCIONES_FORMULARIO = {
    "prioridad_calidad": "Que las empanadas queden bien hechas",
    "prioridad_facil_uso_limpieza": "Que sea fácil de usar y limpiar",
    "prioridad_precio": "Que tenga un precio que pueda pagar",
    "prioridad_espacio": "Que ocupe poco espacio",
    "prioridad_repuestos": "Que sea fácil conseguir reparación y repuestos",
}

COLUMNAS_ENCUESTA = [
    "registro_id", "codigo_anonimo", "es_productor", "respondio_posterior_a_filtro", "edad",
    "nivel_estudios", "prepara_empanadas", "produccion_diaria_rango",
    "segmento_produccion", "rendimiento_verde_consistente",
    "rendimiento_empanadas_por_usd1_texto", "rendimiento_empanadas_por_usd1_estimado",
    "tipo_normalizacion_rendimiento", "comparable_rendimiento_verde",
    "tiempo_proceso_texto", "tiempo_minutos_estimado", "cantidad_proceso_texto",
    "cantidad_empanadas_estimado", "productividad_empanadas_h", "parte_mas_laboriosa",
    "utilidad_percibida", "prioridades_texto", "numero_prioridades_seleccionadas",
    "prioridades_mas_de_dos", "prioridad_calidad", "prioridad_facil_uso_limpieza",
    "prioridad_precio", "prioridad_espacio", "prioridad_repuestos",
    "momento_compra", "precio_maximo_texto", "precio_maximo_usd_estimado",
    "estado_precio", "barrera_compra", "motivo_abandono", "sugerencias",
]

COLUMNAS_BOOLEANAS = [
    "es_productor", "respondio_posterior_a_filtro", "comparable_rendimiento_verde",
    "prioridades_mas_de_dos", *PRIORIDADES.keys(),
]
COLUMNAS_NUMERICAS = [
    "registro_id", "rendimiento_empanadas_por_usd1_estimado", "tiempo_minutos_estimado",
    "cantidad_empanadas_estimado", "productividad_empanadas_h",
    "numero_prioridades_seleccionadas", "precio_maximo_usd_estimado",
]


def _to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "sí", "si", "yes"])


def _texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    return str(valor).strip()


def _parse_rango_numerico(valor, unidades_hora: bool = False) -> float:
    """Interpreta valores o rangos simples y devuelve su valor o punto medio."""
    s = _texto(valor).lower().replace(",", ".")
    if not s or any(x in s for x in ["no sabe", "no sé", "no se", "no sabo", "depende"]):
        return np.nan
    numeros = re.findall(r"\d+(?:\.\d+)?", s)
    if not numeros:
        return np.nan
    valores = [float(x) for x in numeros]
    es_rango = len(valores) >= 2 and any(sep in s for sep in ["-", "–", " a ", " hasta "])
    return float(np.mean(valores[:2])) if es_rango else float(valores[0])


def _parse_tiempo_minutos(valor) -> float:
    """Convierte tiempos escritos libremente a minutos; los rangos usan su punto medio."""
    s = _texto(valor).lower().replace(",", ".")
    if not s or any(x in s for x in ["no sabe", "no sé", "no se", "depende"]):
        return np.nan
    if "hora y media" in s:
        return 90.0
    if "media hora" in s:
        return 30.0

    horas = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hora|horas)\b", s)
    minutos = re.search(r"(\d+(?:\.\d+)?)\s*(?:m|min|mins|minuto|minutos)\b", s)
    if horas or minutos:
        total = float(horas.group(1)) * 60 if horas else 0.0
        total += float(minutos.group(1)) if minutos else 0.0
        return total

    # Cuando no se escribe la unidad, la pregunta establece que el dato está en minutos.
    return _parse_rango_numerico(s)


def _parse_rendimiento_verde(valor) -> tuple[float, str, bool]:
    s = _texto(valor).lower()
    if not s:
        return np.nan, "Sin respuesta", False
    if any(x in s for x in ["no sabe", "no sé", "no se", "no sabo"]):
        return np.nan, "No sabe", False
    if any(x in s for x in ["plátano", "platano", "racima"]):
        return np.nan, "Unidad distinta o respuesta contextual", False
    value = _parse_rango_numerico(s)
    if not np.isfinite(value):
        return np.nan, "Respuesta no numérica", False
    is_range = len(re.findall(r"\d+(?:[.,]\d+)?", s)) >= 2 and any(sep in s for sep in ["-", "–", " a ", " hasta "])
    return value, ("Rango; punto medio" if is_range else "Valor numérico declarado"), True


def _parse_precio(valor) -> tuple[float, str]:
    s = _texto(valor).lower().replace(",", ".")
    if not s:
        return np.nan, "Sin respuesta"
    if any(x in s for x in ["no sabe", "no sé", "no se", "no sab", "no la compraría", "no la compraria", "moledora"]):
        return np.nan, "No define precio de esta máquina"
    numeros = re.findall(r"\d+(?:\.\d+)?", s)
    if not numeros:
        return np.nan, "Respuesta no numérica"
    valor_num = float(numeros[0])
    if valor_num in (1, 2500):
        return valor_num, "Valor numérico; revisar valor atípico"
    return valor_num, "Valor numérico declarado"


def _segmento_produccion(valor) -> str:
    s = _texto(valor).lower()
    if "menos de 20" in s:
        return "Bajo (<20/día)"
    if "20 a 50" in s:
        return "Medio (20–50/día)"
    if "más de 50" in s or "mas de 50" in s:
        return "Alto (>50/día)"
    if "no sabe" in s:
        return "No sabe"
    return "Sin dato"


def _normalizar_opcion(valor: str) -> str:
    """Normaliza texto para comparar opciones sin depender de tildes o puntuación final."""
    texto = unicodedata.normalize("NFKD", _texto(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", texto.lower()).strip()


def _parsear_prioridades(valor) -> set[str]:
    """Separa una respuesta de selección múltiple y devuelve las claves reconocidas."""
    partes = [p.strip() for p in re.split(r"[;\n]+", _texto(valor)) if p.strip()]
    equivalencias = {
        _normalizar_opcion(opcion): clave
        for clave, opcion in PRIORIDAD_OPCIONES_FORMULARIO.items()
    }
    seleccionadas = set()
    for parte in partes:
        clave = equivalencias.get(_normalizar_opcion(parte))
        if clave:
            seleccionadas.add(clave)
    return seleccionadas


def normalizar_encuesta_original(df_original: pd.DataFrame) -> pd.DataFrame:
    """Transforma el archivo original de la encuesta al esquema interno de EmpanaMaq.

    Acepta dos formatos:
    - 17 columnas: índice + 16 preguntas (código anónimo generado como ANON-001...).
    - 18 columnas: índice + código anónimo + 16 preguntas.

    Conserva todas las filas, incluso cuando existan respuestas coincidentes.
    """
    if df_original.shape[1] == 18:
        offset = 2
        tiene_codigo = True
    elif df_original.shape[1] == 17:
        offset = 1
        tiene_codigo = False
    else:
        raise ValueError(
            "Formato no reconocido. Se esperaban 17 columnas "
            "(índice + 16 preguntas) o 18 (índice + código + 16 preguntas); "
            f"se recibieron {df_original.shape[1]}."
        )

    filas = []
    for posicion, (_, raw) in enumerate(df_original.iterrows(), start=1):
        codigo = _texto(raw.iloc[1]) if tiene_codigo else f"ANON-{posicion:03d}"
        codigo = codigo or f"ANON-{posicion:03d}"

        edad = _texto(raw.iloc[offset + 0]) or None
        estudios = _texto(raw.iloc[offset + 1]) or None
        prepara = _texto(raw.iloc[offset + 2]) or None
        es_productor = prepara.lower().startswith(("sí", "si"))

        # Las preguntas posteriores al filtro solo se procesan para productores.
        produccion = _texto(raw.iloc[offset + 3]) if es_productor else ""
        consistencia = _texto(raw.iloc[offset + 4]) if es_productor else ""
        rendimiento_texto = _texto(raw.iloc[offset + 5]) if es_productor else ""
        tiempo_texto = _texto(raw.iloc[offset + 6]) if es_productor else ""
        cantidad_texto = _texto(raw.iloc[offset + 7]) if es_productor else ""
        laboriosa = _texto(raw.iloc[offset + 8]) if es_productor else ""
        utilidad = _texto(raw.iloc[offset + 9]) if es_productor else ""
        prioridades_texto = _texto(raw.iloc[offset + 10]) if es_productor else ""
        momento = _texto(raw.iloc[offset + 11]) if es_productor else ""
        precio_texto = _texto(raw.iloc[offset + 12]) if es_productor else ""
        barrera = _texto(raw.iloc[offset + 13]) if es_productor else ""
        abandono = _texto(raw.iloc[offset + 14]) if es_productor else ""
        sugerencias = _texto(raw.iloc[offset + 15]) if es_productor else ""

        prioridades = _parsear_prioridades(prioridades_texto)
        numero_prioridades = len([p for p in re.split(r"[;\n]+", prioridades_texto) if p.strip()])

        tiempo_min = _parse_tiempo_minutos(tiempo_texto) if es_productor else np.nan
        cantidad = _parse_rango_numerico(cantidad_texto) if es_productor else np.nan
        productividad = (
            cantidad / (tiempo_min / 60.0)
            if np.isfinite(tiempo_min) and tiempo_min > 0 and np.isfinite(cantidad)
            else np.nan
        )
        rendimiento, tipo_rendimiento, comparable = (
            _parse_rendimiento_verde(rendimiento_texto)
            if es_productor else (np.nan, "No aplica", False)
        )
        precio, estado_precio = (
            _parse_precio(precio_texto)
            if es_productor else (np.nan, "No aplica")
        )

        fila = {
            "registro_id": posicion,
            "codigo_anonimo": codigo,
            "es_productor": bool(es_productor),
            "respondio_posterior_a_filtro": bool(es_productor),
            "edad": edad,
            "nivel_estudios": estudios,
            "prepara_empanadas": prepara,
            "produccion_diaria_rango": produccion or None,
            "segmento_produccion": _segmento_produccion(produccion) if es_productor else "Sin dato",
            "rendimiento_verde_consistente": consistencia or None,
            "rendimiento_empanadas_por_usd1_texto": rendimiento_texto or None,
            "rendimiento_empanadas_por_usd1_estimado": rendimiento,
            "tipo_normalizacion_rendimiento": tipo_rendimiento,
            "comparable_rendimiento_verde": bool(comparable),
            "tiempo_proceso_texto": tiempo_texto or None,
            "tiempo_minutos_estimado": tiempo_min,
            "cantidad_proceso_texto": cantidad_texto or None,
            "cantidad_empanadas_estimado": cantidad,
            "productividad_empanadas_h": productividad,
            "parte_mas_laboriosa": laboriosa or None,
            "utilidad_percibida": utilidad or None,
            "prioridades_texto": prioridades_texto or None,
            "numero_prioridades_seleccionadas": numero_prioridades,
            "prioridades_mas_de_dos": numero_prioridades > 2,
            "prioridad_calidad": "prioridad_calidad" in prioridades,
            "prioridad_facil_uso_limpieza": "prioridad_facil_uso_limpieza" in prioridades,
            "prioridad_precio": "prioridad_precio" in prioridades,
            "prioridad_espacio": "prioridad_espacio" in prioridades,
            "prioridad_repuestos": "prioridad_repuestos" in prioridades,
            "momento_compra": momento or None,
            "precio_maximo_texto": precio_texto or None,
            "precio_maximo_usd_estimado": precio,
            "estado_precio": estado_precio,
            "barrera_compra": barrera or None,
            "motivo_abandono": abandono or None,
            "sugerencias": sugerencias or None,
        }
        filas.append(fila)

    normalizada = pd.DataFrame(filas).reindex(columns=COLUMNAS_ENCUESTA)

    # Detectar valores potencialmente atípicos con la regla 1,5 × RIC, sin borrarlos.
    precios = pd.to_numeric(normalizada["precio_maximo_usd_estimado"], errors="coerce").dropna()
    if len(precios) >= 4:
        q1, q3 = precios.quantile([0.25, 0.75])
        ric = q3 - q1
        if ric > 0:
            limite_inferior, limite_superior = q1 - 1.5 * ric, q3 + 1.5 * ric
            mascara = (
                normalizada["precio_maximo_usd_estimado"].lt(limite_inferior)
                | normalizada["precio_maximo_usd_estimado"].gt(limite_superior)
            )
            normalizada.loc[mascara, "estado_precio"] = (
                "Posible valor atípico por regla 1,5 × RIC; conservado"
            )

    return normalizada

def cargar_encuesta(path: str | Path, adicionales_path: str | Path | None = None) -> pd.DataFrame:
    """Carga la base original y concatena respuestas adicionales guardadas localmente."""
    base_path = Path(path)
    df = pd.read_csv(base_path, encoding="utf-8-sig")
    if adicionales_path is not None and Path(adicionales_path).exists():
        extra = pd.read_csv(adicionales_path, encoding="utf-8-sig")
        if not extra.empty:
            df = pd.concat([df, extra], ignore_index=True, sort=False)

    for col in COLUMNAS_BOOLEANAS:
        if col in df.columns:
            df[col] = _to_bool(df[col])
    for col in COLUMNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in COLUMNAS_ENCUESTA:
        if col not in df.columns:
            df[col] = np.nan
    return df[COLUMNAS_ENCUESTA].copy()


def siguiente_registro_id(df: pd.DataFrame) -> int:
    ids = pd.to_numeric(df.get("registro_id", pd.Series(dtype=float)), errors="coerce").dropna()
    return int(ids.max()) + 1 if len(ids) else 1


def crear_registro_encuesta(respuesta: dict, registro_id: int) -> dict:
    """Convierte las respuestas del formulario Streamlit al esquema normalizado."""
    prepara = _texto(respuesta.get("prepara_empanadas"))
    es_productor = prepara.lower().startswith("sí") or prepara.lower().startswith("si")

    # Para quienes no preparan empanadas, el formulario termina en la pregunta 3.
    campos_detalle = [
        "produccion_diaria_rango", "rendimiento_verde_consistente",
        "rendimiento_empanadas_por_usd1_texto", "tiempo_proceso_texto",
        "cantidad_proceso_texto", "parte_mas_laboriosa", "utilidad_percibida",
        "prioridades", "momento_compra", "precio_maximo_texto", "barrera_compra",
        "motivo_abandono", "sugerencias",
    ]
    detalle = {k: respuesta.get(k) for k in campos_detalle} if es_productor else {k: None for k in campos_detalle}

    prioridades_sel = detalle.get("prioridades") or []
    prioridades_texto = ";".join(str(x).strip() for x in prioridades_sel if str(x).strip())
    tiempo_texto = _texto(detalle.get("tiempo_proceso_texto")) or None
    cantidad_texto = _texto(detalle.get("cantidad_proceso_texto")) or None
    rendimiento_texto = _texto(detalle.get("rendimiento_empanadas_por_usd1_texto")) or None
    precio_texto = _texto(detalle.get("precio_maximo_texto")) or None

    tiempo_min = _parse_tiempo_minutos(tiempo_texto)
    cantidad = _parse_rango_numerico(cantidad_texto)
    productividad = cantidad / (tiempo_min / 60.0) if np.isfinite(tiempo_min) and tiempo_min > 0 and np.isfinite(cantidad) else np.nan
    rendimiento, tipo_rendimiento, comparable = _parse_rendimiento_verde(rendimiento_texto)
    precio, estado_precio = _parse_precio(precio_texto)

    row = {
        "registro_id": int(registro_id),
        "codigo_anonimo": f"APP-{int(registro_id):03d}",
        "es_productor": bool(es_productor),
        "respondio_posterior_a_filtro": bool(es_productor),
        "edad": _texto(respuesta.get("edad")) or None,
        "nivel_estudios": _texto(respuesta.get("nivel_estudios")) or None,
        "prepara_empanadas": prepara or None,
        "produccion_diaria_rango": _texto(detalle.get("produccion_diaria_rango")) or None,
        "segmento_produccion": _segmento_produccion(detalle.get("produccion_diaria_rango")) if es_productor else "Sin dato",
        "rendimiento_verde_consistente": _texto(detalle.get("rendimiento_verde_consistente")) or None,
        "rendimiento_empanadas_por_usd1_texto": rendimiento_texto,
        "rendimiento_empanadas_por_usd1_estimado": rendimiento,
        "tipo_normalizacion_rendimiento": tipo_rendimiento,
        "comparable_rendimiento_verde": bool(comparable),
        "tiempo_proceso_texto": tiempo_texto,
        "tiempo_minutos_estimado": tiempo_min,
        "cantidad_proceso_texto": cantidad_texto,
        "cantidad_empanadas_estimado": cantidad,
        "productividad_empanadas_h": productividad,
        "parte_mas_laboriosa": _texto(detalle.get("parte_mas_laboriosa")) or None,
        "utilidad_percibida": _texto(detalle.get("utilidad_percibida")) or None,
        "prioridades_texto": prioridades_texto or None,
        "numero_prioridades_seleccionadas": len(prioridades_sel),
        "prioridades_mas_de_dos": len(prioridades_sel) > 2,
        "momento_compra": _texto(detalle.get("momento_compra")) or None,
        "precio_maximo_texto": precio_texto,
        "precio_maximo_usd_estimado": precio,
        "estado_precio": estado_precio,
        "barrera_compra": _texto(detalle.get("barrera_compra")) or None,
        "motivo_abandono": _texto(detalle.get("motivo_abandono")) or None,
        "sugerencias": _texto(detalle.get("sugerencias")) or None,
    }
    prioridades_normalizadas = _parsear_prioridades(prioridades_texto)
    for col in PRIORIDAD_OPCIONES_FORMULARIO:
        row[col] = col in prioridades_normalizadas
    return row


def guardar_respuesta_adicional(respuesta_normalizada: dict, path: str | Path) -> None:
    """Guarda una respuesta nueva en un archivo separado de la base original."""
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fila = pd.DataFrame([respuesta_normalizada]).reindex(columns=COLUMNAS_ENCUESTA)
    escribir_cabecera = not destino.exists() or destino.stat().st_size == 0
    fila.to_csv(
        destino,
        mode="a",
        header=escribir_cabecera,
        index=False,
        encoding="utf-8-sig" if escribir_cabecera else "utf-8",
    )


def filtrar_productores(df: pd.DataFrame) -> pd.DataFrame:
    if "es_productor" not in df.columns:
        return df.iloc[0:0].copy()
    return df.loc[_to_bool(df["es_productor"])].copy()


def _serie_numerica(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def indicadores_generales(df: pd.DataFrame) -> dict:
    productores = filtrar_productores(df)
    no_productores = len(df) - len(productores)
    tiempo = _serie_numerica(productores, "tiempo_minutos_estimado")
    cantidad = _serie_numerica(productores, "cantidad_empanadas_estimado")
    productividad = _serie_numerica(productores, "productividad_empanadas_h")
    validos = productividad.replace([np.inf, -np.inf], np.nan).dropna()
    precios = _serie_numerica(productores, "precio_maximo_usd_estimado").dropna()
    mucha_utilidad = productores.get("utilidad_percibida", pd.Series(index=productores.index, dtype=object)).astype(str).str.contains("Mucho", case=False).sum()
    no_productores_con_respuestas = 0
    if "respondio_posterior_a_filtro" in df.columns:
        no_productores_con_respuestas = int((~_to_bool(df["es_productor"]) & _to_bool(df["respondio_posterior_a_filtro"])).sum())
    return {
        "registros": int(len(df)),
        "productores": int(len(productores)),
        "no_productores": int(no_productores),
        "no_productores_con_respuestas_posteriores": no_productores_con_respuestas,
        "pares_productividad": int(validos.count()),
        "productividad_mediana": float(validos.median()) if len(validos) else np.nan,
        "productividad_promedio": float(validos.mean()) if len(validos) else np.nan,
        "tiempo_mediano_min": float(tiempo.dropna().median()) if tiempo.notna().any() else np.nan,
        "cantidad_mediana": float(cantidad.dropna().median()) if cantidad.notna().any() else np.nan,
        "precio_mediano": float(precios.median()) if len(precios) else np.nan,
        "precio_promedio": float(precios.mean()) if len(precios) else np.nan,
        "n_precios": int(len(precios)),
        "aceptacion_mucho": int(mucha_utilidad),
    }


def tabla_calidad_datos(df: pd.DataFrame, originales: pd.DataFrame | None = None) -> pd.DataFrame:
    """Resume controles de calidad sin eliminar registros ni corregir respuestas originales."""
    productores = filtrar_productores(df)
    productividad = tabla_productividad(df)
    valores_productividad = pd.to_numeric(productividad.get("productividad_empanadas_h", pd.Series(dtype=float)), errors="coerce").dropna()
    outliers_productividad = 0
    if len(valores_productividad) >= 4:
        q1_prod, q3_prod = valores_productividad.quantile([0.25, 0.75])
        ric_prod = q3_prod - q1_prod
        if ric_prod > 0:
            outliers_productividad = int(
                ((valores_productividad < q1_prod - 1.5 * ric_prod)
                 | (valores_productividad > q3_prod + 1.5 * ric_prod)).sum()
            )
    precios = _serie_numerica(productores, "precio_maximo_usd_estimado").dropna()
    outliers_precio = int(
        productores.get("estado_precio", pd.Series(index=productores.index, dtype=object))
        .astype(str).str.contains("Posible valor atípico", case=False, na=False).sum()
    )
    prioridades_exceso = int(
        _to_bool(productores.get("prioridades_mas_de_dos", pd.Series(False, index=productores.index))).sum()
    )
    patrones_total = "No calculado"
    patrones_productores = "No calculado"
    if originales is not None and len(originales):
        cols_contenido = [c for c in originales.columns if c not in ["index", "ID simulado"]]
        patrones_total = int(originales.duplicated(subset=cols_contenido).sum())
        if len(originales.columns) > 3:
            indice_pregunta_filtro = 4 if "ID simulado" in originales.columns else 3
            mask = originales.iloc[:, indice_pregunta_filtro].astype(str).str.strip().str.lower().str.startswith(("sí", "si"))
            patrones_productores = int(originales.loc[mask].duplicated(subset=cols_contenido).sum())

    filas = [
        ["Total de respuestas", f"{len(df)} registros", "Se conservan todas las participaciones confirmadas como reales."],
        ["Personas que preparan empanadas", f"{len(productores)} ({100*len(productores)/len(df):.1f}%)" if len(df) else "0", "Se utilizan para los análisis condicionados a productores."],
        ["Personas que no preparan empanadas", f"{len(df)-len(productores)} ({100*(len(df)-len(productores))/len(df):.1f}%)" if len(df) else "0", "Se conservan para describir la muestra, pero no para productividad o necesidades del proceso."],
        ["No productores con respuestas posteriores al filtro", str(indicadores_generales(df)["no_productores_con_respuestas_posteriores"]), "No se detectan respuestas fuera del salto del cuestionario."],
        ["Productividad calculable", f"{len(productividad)} de {len(productores)} productores", "Se excluye únicamente el registro cuya cantidad fue respondida como 'Depende'; no se elimina de la base."],
        ["Productividades potencialmente atípicas", f"{outliers_productividad} observaciones", "Se identifican con la regla 1,5 × RIC; se conservan y se prioriza la mediana para reducir la influencia de extremos."],
        ["Rendimiento numérico por USD 1 de verde", f"{int(_serie_numerica(productores, 'rendimiento_empanadas_por_usd1_estimado').notna().sum())} respuestas", "Se excluyen 'No sabe' y respuestas con unidad distinta, por ejemplo, por plátano o racima."],
        ["Precios máximos numéricos", f"{len(precios)} respuestas", "Las respuestas no numéricas se conservan como texto y no entran al promedio o mediana."],
        ["Precios potencialmente atípicos", f"{outliers_precio} respuestas", "Se identifican con la regla 1,5 × RIC y se conservan para revisión; no se eliminan."],
        ["Respuestas con más de dos prioridades", f"{prioridades_exceso} respuestas", "Se conservan todas las selecciones originales; se señala la desviación del máximo indicado."],
        ["Patrones de respuesta repetidos en toda la muestra", str(patrones_total), "Se conservaron: el equipo confirma que corresponden a participantes diferentes; coincidencia no equivale a duplicado de persona."],
        ["Patrones repetidos entre productores", str(patrones_productores), "Se conservan por la confirmación de que cada registro corresponde a una persona real distinta."],
        ["Tipo de establecimiento", "No disponible", "La encuesta no distingue cafetería, restaurante o emprendedor; no se infiere esa clasificación."],
        ["Cobertura geográfica", "Quito, Ecuador", "Ubicación confirmada por el equipo; no se dispone de detalle por barrio o parroquia."],
    ]
    return pd.DataFrame(filas, columns=["Control", "Resultado", "Tratamiento aplicado"])


def tabla_frecuencias(df: pd.DataFrame, columna: str, etiqueta: str | None = None) -> pd.DataFrame:
    productores = filtrar_productores(df)
    if columna not in productores.columns:
        return pd.DataFrame(columns=["Respuesta", "Frecuencia"])
    vc = productores[columna].fillna("Sin respuesta").value_counts(dropna=False)
    return pd.DataFrame({"Respuesta": vc.index.astype(str), "Frecuencia": vc.values})


def tabla_prioridades(df: pd.DataFrame) -> pd.DataFrame:
    productores = filtrar_productores(df)
    rows = []
    for col, label in PRIORIDADES.items():
        values = _to_bool(productores[col]) if col in productores.columns else pd.Series(dtype=bool)
        n = int(values.sum()) if len(values) else 0
        rows.append({"Prioridad": label, "Selecciones": n,
                     "% de productores": 100 * n / len(productores) if len(productores) else 0})
    return pd.DataFrame(rows).sort_values("Selecciones", ascending=False)


def tabla_productividad(df: pd.DataFrame) -> pd.DataFrame:
    productores = filtrar_productores(df).copy()
    for c in ["tiempo_minutos_estimado", "cantidad_empanadas_estimado", "productividad_empanadas_h"]:
        productores[c] = _serie_numerica(productores, c)
    productores = productores.replace([np.inf, -np.inf], np.nan)
    return productores.dropna(subset=["tiempo_minutos_estimado", "cantidad_empanadas_estimado", "productividad_empanadas_h"])


def resumen_mercado(df: pd.DataFrame) -> dict:
    productores = filtrar_productores(df)
    n = len(productores)
    if n == 0:
        return {"n": 0, "aceptacion_pct": 0.0, "compra_12m_pct": 0.0, "intencion_cualquier_momento_pct": 0.0}
    utilidad = productores.get("utilidad_percibida", pd.Series(index=productores.index, dtype=object)).astype(str)
    compra = productores.get("momento_compra", pd.Series(index=productores.index, dtype=object))
    compra_temprana = compra.isin([
        "En los primeros 3 meses desde que salga a la venta.",
        "Entre 4 y 12 meses después.",
    ])
    compra_alguna_vez = compra.isin([
        "En los primeros 3 meses desde que salga a la venta.",
        "Entre 4 y 12 meses después.",
        "Después de un año.",
    ])
    return {
        "n": n,
        "aceptacion_pct": 100 * utilidad.str.contains("Mucho", case=False).sum() / n,
        "compra_12m_pct": 100 * compra_temprana.sum() / n,
        "intencion_cualquier_momento_pct": 100 * compra_alguna_vez.sum() / n,
    }


def calcular_tamano_mercado(establecimientos: int, pct_elabora: float, pct_volumen: float) -> dict:
    base = max(0, int(establecimientos))
    p1 = float(np.clip(pct_elabora, 0, 1))
    p2 = float(np.clip(pct_volumen, 0, 1))
    mercado_empanadas = base * p1
    mercado_objetivo = mercado_empanadas * p2
    return {
        "establecimientos_base": base,
        "establecimientos_empanadas": mercado_empanadas,
        "mercado_objetivo": mercado_objetivo,
    }


def _asignar_enteros_preservando_total(valores: np.ndarray, total: int) -> np.ndarray:
    if total <= 0 or len(valores) == 0 or valores.sum() <= 0:
        return np.zeros(len(valores), dtype=int)
    exactos = valores / valores.sum() * total
    base = np.floor(exactos).astype(int)
    faltan = int(total - base.sum())
    if faltan > 0:
        orden = np.argsort(-(exactos - base))
        base[orden[:faltan]] += 1
    return base


def proyectar_ciclo_vida(parametros: dict) -> tuple[pd.DataFrame, dict]:
    """Proyecta ventas esperadas durante 48 meses mediante una curva comercial didáctica.

    Las ventas mensuales se expresan como unidades esperadas equivalentes para
    conservar una curva gradual; no representan fracciones de máquinas físicas vendidas.
    """
    meses = np.arange(1, MESES + 1)
    market = calcular_tamano_mercado(
        parametros.get("establecimientos_base", MERCADO_REFERENCIA_QUITO),
        parametros.get("pct_elabora", 0.15),
        parametros.get("pct_volumen", 0.214),
    )
    cobertura = float(np.clip(parametros.get("cobertura_48m", 0.25), 0, 1))
    conversion = float(np.clip(parametros.get("conversion", 0.40), 0, 1))
    intencion = float(np.clip(parametros.get("intencion_compra_pct", 0.964), 0, 1))
    compradores_teoricos = market["mercado_objetivo"] * cobertura * intencion * conversion

    # Distribución relativa de la demanda: seis meses de desarrollo sin ventas.
    pesos = np.zeros(MESES, dtype=float)
    pesos[6:12] = np.linspace(0.35, 0.85, 6)       # Introducción: meses 7–12
    pesos[12:24] = np.linspace(0.95, 1.45, 12)    # Crecimiento: meses 13–24
    pesos[24:36] = np.linspace(1.45, 1.25, 12)    # Madurez: meses 25–36
    pesos[36:42] = np.linspace(1.15, 0.75, 6)     # Saturación: meses 37–42
    pesos[42:48] = np.linspace(0.65, 0.20, 6)     # Declive: meses 43–48

    if pesos.sum() > 0:
        demanda = pesos / pesos.sum() * compradores_teoricos
    else:
        demanda = np.zeros(MESES, dtype=float)

    cap_maquinas = max(0, int(parametros.get("cap_maquinas_mes", 4)))
    ventas = np.minimum(demanda, cap_maquinas)
    no_atendida = demanda - ventas

    etapas = np.select(
        [meses <= 6, meses <= 12, meses <= 24, meses <= 36, meses <= 42],
        ["Desarrollo", "Introducción", "Crecimiento", "Madurez", "Saturación"],
        default="Declive",
    )
    tabla = pd.DataFrame({
        "Mes": meses,
        "Año": ((meses - 1) // 12 + 1),
        "Etapa": etapas,
        "Demanda potencial de máquinas": demanda,
        "Ventas estimadas": ventas,
        "Demanda no atendida": no_atendida,
        "Demanda acumulada": np.cumsum(demanda),
        "Ventas acumuladas": np.cumsum(ventas),
    })
    resumen = {
        **market,
        "cobertura_48m_pct": cobertura * 100,
        "intencion_declarada_pct": intencion * 100,
        "conversion_pct": conversion * 100,
        "compradores_teoricos": float(compradores_teoricos),
        "demanda_total": float(demanda.sum()),
        "ventas_total": float(ventas.sum()),
        "demanda_no_atendida": float(no_atendida.sum()),
        "cap_maquinas_mes": cap_maquinas,
    }
    return tabla, resumen

def calcular_finanzas(tabla_demanda: pd.DataFrame, p: dict) -> tuple[pd.DataFrame, dict]:
    """Modelo económico simplificado, sin impuestos ni financiación."""
    meses = tabla_demanda["Mes"].to_numpy(dtype=int)
    ventas = tabla_demanda["Ventas estimadas"].to_numpy(dtype=float)
    precio0 = max(0.0, float(p.get("precio_venta", 200)))
    costo0 = max(0.0, float(p.get("costo_unitario", 200)))
    fijo0 = max(0.0, float(p.get("costos_fijos_mes", 0)))
    inversion = max(0.0, float(p.get("inversion_prototipo", 400)))
    inflacion = float(np.clip(p.get("crecimiento_costos_anual", 0.03), -0.5, 1.0))
    var_precio = float(np.clip(p.get("variacion_precio_anual", 0.0), -0.5, 1.0))
    descuento_anual = float(np.clip(p.get("tasa_descuento_anual", 0.12), 0, 2))
    precio = precio0 * (1 + var_precio) ** ((meses - 1) // 12)
    costo_unitario = costo0 * (1 + inflacion) ** ((meses - 1) // 12)
    costos_fijos = fijo0 * (1 + inflacion) ** ((meses - 1) // 12)
    ingresos = ventas * precio
    costo_variable = ventas * costo_unitario
    margen_contribucion = ingresos - costo_variable
    ebitda = margen_contribucion - costos_fijos
    tasa_mensual = (1 + descuento_anual) ** (1 / 12) - 1 if descuento_anual > 0 else 0
    flujo = ebitda.copy()
    caja_acumulada = np.cumsum(flujo) - inversion
    van = -inversion + float(np.sum(ebitda / ((1 + tasa_mensual) ** meses)))
    recuperacion = np.flatnonzero(caja_acumulada >= 0)
    margen_unitario = precio0 - costo0
    punto_equilibrio = (fijo0 / margen_unitario) if margen_unitario > 0 else np.nan
    resultados = pd.DataFrame({
        "Mes": meses,
        "Año": ((meses - 1) // 12 + 1),
        "Ventas esperadas (máquinas equivalentes)": np.round(ventas, 3),
        "Precio de venta (USD)": precio,
        "Ingresos (USD)": ingresos,
        "Costo variable (USD)": costo_variable,
        "Costos fijos (USD)": costos_fijos,
        "Margen de contribución (USD)": margen_contribucion,
        "EBITDA (USD)": ebitda,
        "Flujo neto (USD)": flujo,
        "Caja acumulada (USD)": caja_acumulada,
    })
    resumen = {
        "ingresos_totales": float(ingresos.sum()),
        "costos_variables_totales": float(costo_variable.sum()),
        "costos_fijos_totales": float(costos_fijos.sum()),
        "ebitda_total": float(ebitda.sum()),
        "van": float(van),
        "payback_mes": int(recuperacion[0] + 1) if len(recuperacion) else None,
        "margen_unitario": float(margen_unitario),
        "punto_equilibrio_mensual": float(punto_equilibrio) if np.isfinite(punto_equilibrio) else None,
        "inversion_prototipo": float(inversion),
    }
    return resultados, resumen


def matriz_requerimientos(df: pd.DataFrame, capacidad_min: int = 20, capacidad_max: int = 50) -> pd.DataFrame:
    """Relaciona necesidades con módulos C1 e identifica la pregunta que sustenta cada indicador."""
    productores = filtrar_productores(df)
    n = len(productores)
    prioridades = tabla_prioridades(productores)
    pmap = dict(zip(prioridades["Prioridad"], prioridades["% de productores"]))

    parte_laboriosa = productores.get(
        "parte_mas_laboriosa", pd.Series(index=productores.index, dtype=object)
    ).astype(str)
    motivo_abandono = productores.get(
        "motivo_abandono", pd.Series(index=productores.index, dtype=object)
    ).astype(str)
    produccion = productores.get(
        "produccion_diaria_rango", pd.Series(index=productores.index, dtype=object)
    ).astype(str)

    esfuerzo_pct = 100 * parte_laboriosa.str.contains("Moler", case=False, na=False).sum() / n if n else 0
    confiabilidad_pct = 100 * motivo_abandono.str.contains("dañe seguido", case=False, na=False).sum() / n if n else 0
    volumen_medio_alto_pct = 100 * produccion.str.contains("20 a 50", case=False, na=False).sum() / n if n else 0

    items = [
        ["Uniformidad y calidad del producto", "Seleccionó calidad de las empanadas", pmap.get("Calidad de las empanadas", 0), "M2, M3, M5 y M6", "Dosificación uniforme, espesor, centrado y sellado repetible"],
        ["Facilidad de uso y limpieza", "Seleccionó facilidad de uso y limpieza", pmap.get("Facilidad de uso y limpieza", 0), "Todos los módulos", "Superficies accesibles, desmontaje y limpieza de zonas de contacto"],
        ["Costo accesible", "Seleccionó precio accesible", pmap.get("Precio accesible", 0), "Todos los módulos", "Reducir piezas especiales y evaluar el costo del accionamiento híbrido"],
        ["Mantenimiento y repuestos", "Seleccionó reparación y repuestos", pmap.get("Reparación y repuestos", 0), "Todos los módulos", "Componentes comerciales y subconjuntos reemplazables"],
        ["Tamaño compacto", "Seleccionó poco espacio ocupado", pmap.get("Poco espacio ocupado", 0), "Estructura y distribución", "Disposición compacta sin comprometer acceso y seguridad"],
        ["Capacidad de producción", "Declaró producir entre 20 y 50 empanadas al día; el rango técnico por hora es una decisión del equipo", volumen_medio_alto_pct, "M1–M6", f"Contrastar la capacidad propuesta de {capacidad_min}–{capacidad_max} empanadas/h con la demanda diaria; validar tiempos de ciclo y operación por lotes"],
        ["Reducir el esfuerzo de preparación", "Identificó la molienda como la etapa más laboriosa", esfuerzo_pct, "M1 y M2", "Priorizar molienda, alimentación y dosificación de masa"],
        ["Confiabilidad", "Indicó fallas frecuentes como motivo de abandono", confiabilidad_pct, "Todos los módulos", "Proteger accionamientos y facilitar inspección y mantenimiento"],
    ]
    return pd.DataFrame(
        items,
        columns=[
            "Necesidad / requerimiento",
            "Fuente del indicador",
            "Indicador observado (%)",
            "Módulos relacionados",
            "Implicación preliminar de diseño",
        ],
    )


