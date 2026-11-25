# EmpanaMaq — aplicación de encuestas y análisis

Aplicación académica desarrollada con Python, Pandas, Plotly y Streamlit para analizar una encuesta sobre una máquina semiautomática para elaborar empanadas de verde en Quito.

## Base de datos utilizada

- Se utiliza exclusivamente la última encuesta entregada: 100 respuestas de Quito.
- 56 personas indicaron que preparan empanadas de verde y 44 indicaron que no.
- La base anterior de 54 respuestas y las otras versiones de encuestas no se combinan con esta.
- El archivo fuente contiene un índice y las 16 preguntas, sin una columna independiente de identificación. La aplicación genera códigos anónimos internos `ANON-001` a `ANON-100`.
- No se eliminan registros por coincidencia de respuestas.
- Las preguntas posteriores a la pregunta filtro solo se analizan para quienes indicaron que sí preparan empanadas.

## Estructura del proyecto

| Archivo | Función |
|---|---|
| `app.py` | Interfaz de Streamlit y visualización de análisis. |
| `modelo.py` | Normalización, indicadores, proyecciones, finanzas y matriz de requerimientos. |
| `encuesta_fuente_100_respuestas.xlsx` | Archivo Excel recibido como fuente de las 100 respuestas. |
| `encuesta_original_anonimizada.csv` | Exportación de la fuente a CSV, conservando las preguntas originales. |
| `encuesta_real.csv` | Base normalizada utilizada por la aplicación. |
| `preparar_base.py` | Reproduce la conversión de la fuente CSV al formato interno de la app. |
| `verificar.py` | Pruebas automáticas de integridad y cálculos. |
| `METODOLOGIA_ANALISIS.md` | Explicación de los indicadores, fórmulas, supuestos y limitaciones. |
| `SUPUESTOS_ESCENARIOS_Y_COSTOS.md` | Justificación de los tres escenarios y de los valores económicos predeterminados. |
| `REVISION_RUBRICA.md` | Correspondencia entre la aplicación y la rúbrica de la primera fase. |
| `Auditoria_encuesta_100_respuestas.xlsx` | Libro de revisión con base original, normalizada, indicadores, frecuencias, prioridades y controles de calidad. |

## Instalación y ejecución en PyCharm

1. Descomprimir el proyecto.
2. Abrir la carpeta `EMPANAMaq_App_v4` en PyCharm.
3. Crear o seleccionar un entorno virtual.
4. Abrir la terminal integrada y ejecutar:

```bash
python -m pip install -r requirements.txt
```

5. (Opcional) Regenerar la base normalizada:

```bash
python preparar_base.py
```

6. Ejecutar las pruebas:

```bash
python verificar.py
```

7. Iniciar Streamlit:

```bash
python -m streamlit run app.py
```

8. Abrir la dirección local que muestra Streamlit, normalmente `http://localhost:8501`.

## Cambiar el nombre de la máquina

En `app.py`, modificar la variable:

```python
NOMBRE_MAQUINA = "EmpanaMaq"
```

## Qué analiza la aplicación

1. **Encuestas:** consulta de respuestas, registro local de nuevas respuestas, exportación y control de calidad.
2. **Análisis de mercado:** perfil, producción diaria, dificultades, utilidad, intención de compra, prioridades, barreras y disposición de pago.
3. **Productividad, demanda y ciclo comercial:** comparación de productividad manual con la capacidad configurable de la máquina y proyección comercial a 48 meses.
4. **Costos y rentabilidad:** ingresos, costos variables y fijos, margen de contribución, EBITDA, VAN, recuperación y punto de equilibrio.
5. **Sensibilidad:** efecto de cambios en precio y costo unitario sobre el VAN.
6. **Diseño y requerimientos:** relación preliminar entre necesidades observadas y módulos del concepto C1.

## Configuración económica predeterminada

- Costo estimado del prototipo: USD 400.
- Compresor externo: referencia académica aproximada de USD 60, no incluido en los USD 400.
- Precio de venta: USD 300.
- Costo comercial unitario: USD 200.
- Costos fijos: USD 25 mensuales.
- Incremento anual de costos: 3 %.
- Variación anual del precio: 0 %.
- Tasa de descuento anual: 12 %.

El costo unitario y los costos fijos son supuestos académicos de planificación, no cotizaciones definitivas. El costo comercial unitario de USD 200 supone que una unidad posterior puede fabricarse con componentes estandarizados y reutilización de recursos del desarrollo del prototipo.

## Escenarios comerciales predeterminados

- **Conservador:** 10 % de establecimientos que elaborarían empanadas, 21,4 % del segmento de 20–50 empanadas/día, 15 % de cobertura, intención de compra de 12 meses y 30 % de conversión.
- **Moderado:** 15 % de establecimientos que elaborarían empanadas, 21,4 % del segmento de 20–50 empanadas/día, 25 % de cobertura, intención de compra en algún momento y 40 % de conversión.
- **Optimista:** 20 % de establecimientos que elaborarían empanadas, 21,4 % del segmento de 20–50 empanadas/día, 35 % de cobertura, intención de compra en algún momento y 50 % de conversión.

El 21,4 % procede de la encuesta (12 de 56 productores). La intención de compra se calcula con las respuestas reales. Los porcentajes de establecimientos que elaborarían empanadas, cobertura y conversión son supuestos explícitos, no estadísticas observadas.

## Importante: datos reales y supuestos

Las estadísticas descriptivas se calculan exclusivamente con las 100 respuestas reales de Quito. Los escenarios conservador, moderado y optimista son hipótesis comerciales para explorar la demanda; no son encuestas simuladas ni ventas observadas.

El universo de 6.873 establecimientos es una referencia del catastro turístico de alimentos y bebidas de Quito, junio de 2024. No representa el número comprobado de establecimientos que venden empanadas de verde.

La curva de 48 meses representa el ciclo comercial del producto. No reemplaza el análisis ambiental del ciclo de vida mediante OpenLCA.

Las ventas mensuales se muestran como unidades esperadas equivalentes para construir una curva gradual. No representan fracciones de máquinas físicas vendidas ni una predicción estadística ajustada a ventas históricas.

## Registro de nuevas respuestas y despliegue público

El formulario interno permite añadir respuestas y las guarda localmente en `respuestas_adicionales.csv`. Para recopilar respuestas desde Streamlit Cloud se debe conectar almacenamiento externo persistente; no se debe depender del sistema de archivos local del despliegue.

## Validación

Ejecutar `python verificar.py`. Las pruebas comprueban 100 respuestas, 56 productores, 55 productividades calculables, estadísticas de disposición de pago, prioridades, matriz de requerimientos, escenarios, finanzas y registro de una nueva respuesta.

## Limitaciones que deben declararse

- La muestra describe a las 100 personas encuestadas en Quito; no es un censo de todos los negocios de la ciudad.
- La encuesta no distingue cafeterías, restaurantes y emprendedores; no se debe inferir el tipo de establecimiento.
- La encuesta no permite estimar directamente qué proporción de los 6.873 establecimientos vende empanadas de verde.
- La disposición de pago declarada no equivale a una compra confirmada.
- El costo unitario de USD 200 y los costos fijos de USD 25/mes son supuestos académicos que deben sustituirse por cotizaciones y un presupuesto operativo si el proyecto pasa a fabricación comercial.
