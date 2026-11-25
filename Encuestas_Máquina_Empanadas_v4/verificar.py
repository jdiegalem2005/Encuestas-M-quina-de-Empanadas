from pathlib import Path
import tempfile
import numpy as np
import pandas as pd

from modelo import (
    cargar_encuesta,
    normalizar_encuesta_original,
    crear_registro_encuesta,
    guardar_respuesta_adicional,
    indicadores_generales,
    filtrar_productores,
    matriz_requerimientos,
    proyectar_ciclo_vida,
    calcular_finanzas,
    siguiente_registro_id,
    resumen_mercado,
    tabla_prioridades,
    tabla_calidad_datos,
    _parse_tiempo_minutos,
    ESCENARIOS_COMERCIALES,
    MERCADO_REFERENCIA_QUITO,
)

BASE = Path(__file__).parent
originales = pd.read_csv(BASE / "encuesta_original_anonimizada.csv", encoding="utf-8-sig")
real = cargar_encuesta(BASE / "encuesta_real.csv")

# La nueva fuente tiene 100 filas, un índice y las 16 preguntas; no incluye un ID separado.
assert originales.shape == (100, 17)
assert len(real) == 100
assert real["codigo_anonimo"].nunique() == 100
assert real["codigo_anonimo"].iloc[0] == "ANON-001"
assert len(filtrar_productores(real)) == 56
assert len(real) - len(filtrar_productores(real)) == 44
assert indicadores_generales(real)["no_productores_con_respuestas_posteriores"] == 0

# Indicadores de productividad y precios de la nueva base.
ind = indicadores_generales(real)
assert ind["pares_productividad"] == 55
assert round(ind["productividad_mediana"], 2) == 17.14
assert round(ind["productividad_promedio"], 2) == 16.80
assert round(ind["tiempo_mediano_min"], 2) == 30.00
assert round(ind["cantidad_mediana"], 2) == 6.00
assert ind["n_precios"] == 56
assert round(ind["precio_mediano"], 2) == 350.00
assert round(ind["precio_promedio"], 2) == 330.36

productores = filtrar_productores(real)
precios = pd.to_numeric(productores["precio_maximo_usd_estimado"], errors="coerce").dropna()
assert int((precios >= 300).sum()) == 47
assert round(100 * (precios >= 300).sum() / len(productores), 1) == 83.9
assert int(real["estado_precio"].astype(str).str.contains("Posible valor atípico").sum()) == 5

# Prioridades y aceptación comercial.
prioridades = tabla_prioridades(real).set_index("Prioridad")["Selecciones"].to_dict()
assert prioridades["Facilidad de uso y limpieza"] == 30
assert prioridades["Calidad de las empanadas"] == 27
assert prioridades["Precio accesible"] == 27
assert prioridades["Reparación y repuestos"] == 6
assert prioridades["Poco espacio ocupado"] == 1
assert int(real["prioridades_mas_de_dos"].sum()) == 4

mercado = resumen_mercado(real)
assert round(mercado["aceptacion_pct"], 2) == 50.00
assert round(mercado["compra_12m_pct"], 2) == 53.57
assert round(mercado["intencion_cualquier_momento_pct"], 2) == 96.43

# Matriz de necesidades y conversiones de tiempo.
matriz = matriz_requerimientos(real, 20, 50)
assert len(matriz) == 8
assert "Fuente del indicador" in matriz.columns
assert round(float(matriz.loc[matriz["Necesidad / requerimiento"] == "Reducir el esfuerzo de preparación", "Indicador observado (%)"].iloc[0]), 2) == 71.43
assert _parse_tiempo_minutos("1h") == 60.0
assert _parse_tiempo_minutos("35m") == 35.0
assert _parse_tiempo_minutos("20-25") == 22.5
assert _parse_tiempo_minutos("media hora") == 30.0
assert _parse_tiempo_minutos("1h 30m") == 90.0

# Tres escenarios acordados; las intenciones se calculan a partir de la encuesta real.
ventas_esperadas = {}
for nombre, escenario in ESCENARIOS_COMERCIALES.items():
    intencion = (
        mercado["compra_12m_pct"] / 100
        if escenario["intencion_tipo"] == "compra_12m"
        else mercado["intencion_cualquier_momento_pct"] / 100
    )
    params = {
        "establecimientos_base": MERCADO_REFERENCIA_QUITO,
        "pct_elabora": escenario["pct_elabora"],
        "pct_volumen": escenario["pct_volumen"],
        "cobertura_48m": escenario["cobertura_48m"],
        "intencion_compra_pct": intencion,
        "conversion": escenario["conversion"],
        "cap_maquinas_mes": escenario["cap_maquinas_mes"],
    }
    tabla, resumen = proyectar_ciclo_vida(params)
    assert len(tabla) == 48
    assert (tabla.loc[tabla["Mes"] <= 6, "Ventas estimadas"] == 0).all()
    assert tabla.loc[tabla["Mes"] >= 7, "Ventas estimadas"].sum() > 0
    assert np.isclose(tabla["Ventas estimadas"].sum(), resumen["ventas_total"])
    ventas_esperadas[nombre] = resumen["ventas_total"]

assert round(ventas_esperadas["Conservador"]) == 4
assert round(ventas_esperadas["Moderado"]) == 21
assert round(ventas_esperadas["Optimista"]) == 50

# Finanzas con los valores predeterminados acordados.
moderado = ESCENARIOS_COMERCIALES["Moderado"]
params_moderado = {
    "establecimientos_base": MERCADO_REFERENCIA_QUITO,
    "pct_elabora": moderado["pct_elabora"],
    "pct_volumen": moderado["pct_volumen"],
    "cobertura_48m": moderado["cobertura_48m"],
    "intencion_compra_pct": mercado["intencion_cualquier_momento_pct"] / 100,
    "conversion": moderado["conversion"],
    "cap_maquinas_mes": moderado["cap_maquinas_mes"],
}
tabla_ciclo, _ = proyectar_ciclo_vida(params_moderado)
fin, resumen_fin = calcular_finanzas(tabla_ciclo, {
    "precio_venta": 300,
    "costo_unitario": 200,
    "costos_fijos_mes": 25,
    "inversion_prototipo": 400,
    "crecimiento_costos_anual": 0.03,
    "variacion_precio_anual": 0.0,
    "tasa_descuento_anual": 0.12,
})
assert len(fin) == 48
assert np.isfinite(resumen_fin["van"])
assert round(resumen_fin["margen_unitario"], 2) == 100.00

# Registro de nuevas respuestas y persistencia local.
respuesta = {
    "edad": "De 30 a 44 años.",
    "nivel_estudios": "Universidad o posgrado.",
    "prepara_empanadas": "Sí, seguido.",
    "produccion_diaria_rango": "De 20 a 50.",
    "rendimiento_verde_consistente": "Sí, siempre salen casi la misma cantidad.",
    "rendimiento_empanadas_por_usd1_texto": "10",
    "tiempo_proceso_texto": "30 minutos",
    "cantidad_proceso_texto": "10",
    "parte_mas_laboriosa": "Moler el verde y preparar la masa.",
    "utilidad_percibida": "Mucho.",
    "prioridades": ["Que las empanadas queden bien hechas.", "Que sea fácil de usar y limpiar."],
    "momento_compra": "En los primeros 3 meses desde que salga a la venta.",
    "precio_maximo_texto": "USD 250",
    "barrera_compra": "Que sea muy cara.",
    "motivo_abandono": "Que se dañe seguido.",
    "sugerencias": "Prueba de funcionamiento.",
}
nueva = crear_registro_encuesta(respuesta, siguiente_registro_id(real))
assert nueva["registro_id"] == 101
assert nueva["codigo_anonimo"] == "APP-101"
assert nueva["es_productor"] is True
assert round(nueva["productividad_empanadas_h"], 2) == 20.00
assert nueva["prioridad_calidad"] is True

respuesta_no = {
    "edad": "De 18 a 29 años.",
    "nivel_estudios": "Secundaria o bachillerato.",
    "prepara_empanadas": "No.",
}
no_productor = crear_registro_encuesta(respuesta_no, 102)
assert no_productor["es_productor"] is False
assert pd.isna(no_productor["tiempo_minutos_estimado"])

with tempfile.TemporaryDirectory() as tmp:
    destino = Path(tmp) / "respuestas_adicionales.csv"
    guardar_respuesta_adicional(nueva, destino)
    guardada = pd.read_csv(destino)
    assert len(guardada) == 1
    assert int(guardada.loc[0, "registro_id"]) == 101
    combinada = cargar_encuesta(BASE / "encuesta_real.csv", destino)
    assert len(combinada) == 101
    assert len(filtrar_productores(combinada)) == 57

# Los patrones coincidentes se reportan, no se borran.
calidad = tabla_calidad_datos(real, originales)
assert any(calidad["Control"].str.contains("Patrones de respuesta repetidos", case=False))

print("OK: 100 respuestas reales de Quito; 56 productores; 55 productividades válidas.")
print("OK: mediana de pago USD 350; 47/56 productores declaran USD 300 o más.")
print("OK: prioridades, calidad de datos, matriz de requerimientos y registro adicional.")
print("OK: escenarios aproximados: conservador 4, moderado 21 y optimista 50 máquinas.")
