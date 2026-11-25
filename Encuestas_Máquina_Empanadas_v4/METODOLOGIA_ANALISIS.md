# Metodología de análisis de EmpanaMaq

## 1. Fuente y tratamiento de la información

La aplicación utiliza exclusivamente el último archivo de encuesta recibido, compuesto por 100 respuestas de personas ubicadas en Quito, según confirmación del equipo. No se integran las bases anteriores.

De las 100 respuestas, 56 personas indicaron que preparan empanadas de verde y 44 indicaron que no. Las 100 respuestas se conservan para describir la muestra; las preguntas sobre producción, dificultades, utilidad, compra y disposición de pago se analizan sobre los 56 productores.

El archivo fuente contiene un índice y las 16 preguntas, pero no incluye una columna independiente de identificación. Por ello, la aplicación genera códigos internos anónimos `ANON-001` a `ANON-100`. Estos códigos no representan nombres ni datos personales.

La depuración:
- conserva el texto original de las respuestas;
- convierte tiempos escritos a minutos;
- convierte rangos numéricos a su punto medio cuando es necesario;
- calcula productividad cuando existen tiempo y cantidad válidos;
- separa las opciones de selección múltiple;
- extrae valores numéricos de disposición de pago;
- marca posibles valores atípicos mediante la regla 1,5 × RIC, sin eliminarlos;
- conserva las respuestas coincidentes.

## 2. Indicadores descriptivos de la encuesta

### 2.1. Perfil de productores

La proporción de productores en la muestra es:

P_productores = 56 / 100 × 100 = 56 %

Los no productores se conservan en la descripción general, pero no intervienen en el cálculo de productividad ni en la priorización de necesidades del proceso.

### 2.2. Producción diaria

De los 56 productores:
- 44 elaboran menos de 20 empanadas al día (78,6 %).
- 12 elaboran entre 20 y 50 empanadas al día (21,4 %).

El segmento de 20–50 empanadas/día se utiliza como segmento objetivo inicial de la proyección comercial. Esta elección es un criterio de segmentación del proyecto; no significa que los productores de menor volumen no puedan utilizar la máquina.

### 2.3. Productividad manual

Se calcula para cada respuesta válida:

Productividad = cantidad de empanadas / tiempo en horas

Cuando el tiempo está en minutos:

Productividad (empanadas/h) = cantidad × 60 / tiempo (min)

Se obtuvieron 55 pares válidos de tiempo y cantidad. La mediana es aproximadamente 17,14 empanadas/h y el promedio aproximadamente 16,80 empanadas/h. Se utiliza la mediana como referencia central porque es menos sensible a valores extremos.

### 2.4. Dificultad del proceso

40 de los 56 productores identificaron la molienda y preparación de masa como la parte más laboriosa:

40 / 56 × 100 = 71,4 %

Este resultado justifica prestar especial atención a los módulos de molienda y acondicionamiento de masa.

### 2.5. Utilidad percibida e intención de compra

- 28 de 56 productores (50,0 %) consideran que la máquina les serviría mucho.
- 30 de 56 (53,6 %) declararon que podrían comprarla durante los primeros 12 meses.
- 54 de 56 (96,4 %) seleccionaron algún periodo de compra, incluyendo después de un año. Dos participantes respondieron que todavía no saben.

La intención declarada no se interpreta como una venta confirmada. Se utiliza como referencia de interés y se combina con una tasa de conversión supuesta en los escenarios comerciales.

### 2.6. Disposición de pago

La aplicación normaliza las respuestas numéricas y textuales de precio. Los indicadores obtenidos son:
- 56 respuestas numéricas.
- Mediana: USD 350.
- Promedio: USD 330,36.
- Primer cuartil: USD 300.
- Tercer cuartil: USD 350.
- 47 de 56 productores (83,9 %) indicaron una disposición máxima igual o superior a USD 300.

Se selecciona USD 300 como precio de venta de referencia para el ejercicio académico. Es inferior a la mediana de disposición de pago y se encuentra respaldado por la proporción de respuestas iguales o superiores a ese valor. La disposición declarada no equivale a una compra real ni valida por sí sola el precio comercial.

### 2.7. Prioridades de diseño

La pregunta de selección múltiple permite identificar las características más importantes para los productores:

| Prioridad | Selecciones | % de productores |
|---|---:|---:|
| Facilidad de uso y limpieza | 30 | 53,6 % |
| Calidad de las empanadas | 27 | 48,2 % |
| Precio accesible | 27 | 48,2 % |
| Reparación y repuestos | 6 | 10,7 % |
| Poco espacio ocupado | 1 | 1,8 % |

El porcentaje se calcula sobre los 56 productores. Como la pregunta permite seleccionar hasta dos opciones, la suma de porcentajes puede superar el 100 %.

## 3. Estimación del mercado objetivo

La aplicación utiliza como universo de referencia 6.873 establecimientos de alimentos y bebidas de Quito, procedentes del catastro turístico de junio de 2024. El valor no representa el número de establecimientos que efectivamente elaboran empanadas de verde.

La estimación se realiza mediante:

Mercado objetivo = establecimientos de referencia × porcentaje supuesto que elabora empanadas × porcentaje del segmento de 20–50 empanadas/día.

El 21,4 % del segmento de producción procede de la encuesta. El porcentaje de establecimientos que elaboraría empanadas es un supuesto editable porque la muestra no permite estimarlo para todos los negocios de Quito.

## 4. Escenarios comerciales

La demanda esperada a 48 meses se estima mediante:

Demanda esperada = mercado objetivo × cobertura comercial × intención declarada × conversión efectiva.

Los tres escenarios predeterminados son:

| Parámetro | Conservador | Moderado | Optimista |
|---|---:|---:|---:|
| Establecimientos que elaborarían empanadas | 10 % | 15 % | 20 % |
| Segmento 20–50 empanadas/día | 21,4 % | 21,4 % | 21,4 % |
| Cobertura comercial a 48 meses | 15 % | 25 % | 35 % |
| Intención utilizada | 53,6 % | 96,4 % | 96,4 % |
| Conversión efectiva | 30 % | 40 % | 50 % |
| Capacidad de fabricación | 2/mes | 4/mes | 6/mes |
| Demanda aproximada | 4 | 21 | 50 |

El escenario conservador utiliza la intención de compra declarada dentro de los primeros 12 meses. Los escenarios moderado y optimista utilizan la intención declarada en algún momento. La conversión es un supuesto que reduce el interés declarado a una estimación de compradores efectivos.

Los porcentajes de establecimientos que elaborarían empanadas, cobertura comercial y conversión no son resultados de la encuesta; se utilizan como hipótesis de planificación.

## 5. Curva comercial de 48 meses

La proyección separa las etapas siguientes:

| Etapa | Meses |
|---|---|
| Desarrollo | 1–6 |
| Introducción | 7–12 |
| Crecimiento | 13–24 |
| Madurez | 25–36 |
| Saturación | 37–42 |
| Declive | 43–48 |

Se utiliza una distribución ponderada de la demanda para representar una introducción gradual, un crecimiento, una etapa de mayor estabilidad y una reducción posterior. Las ventas mensuales se muestran como unidades esperadas equivalentes para evitar una curva excesivamente irregular cuando el número total de unidades es pequeño. No son fracciones de máquinas físicas ni una predicción estadística ajustada a datos históricos.

Esta curva representa el ciclo comercial del producto y no reemplaza el análisis ambiental de ciclo de vida realizado mediante OpenLCA.

## 6. Supuestos económicos

Los valores predeterminados del ejercicio son:

| Parámetro | Valor |
|---|---:|
| Costo del prototipo | USD 400 |
| Compresor externo de referencia | USD 60, fuera del costo del prototipo |
| Precio de venta por máquina | USD 300 |
| Costo comercial unitario estimado | USD 200 |
| Costos fijos mensuales | USD 25 |
| Incremento anual de costos | 3 % |
| Variación anual del precio | 0 % |
| Tasa de descuento anual | 12 % |

El precio de USD 300 se selecciona a partir de la encuesta. El costo de USD 200 por unidad adicional y los costos fijos de USD 25 mensuales son supuestos académicos para evaluar el proyecto, no cotizaciones definitivas.

Los USD 25 mensuales se distribuyen de forma referencial en administración y comunicaciones (USD 8), promoción (USD 7), uso compartido de instalaciones y servicios (USD 5) y reserva de mantenimiento menor (USD 5). No se consideran salarios ni alquiler de un taller independiente.

El costo del prototipo de USD 400 no incluye el compresor externo, estimado en aproximadamente USD 60. El costo comercial unitario de USD 200 supone estandarización y reutilización de recursos tras desarrollar el prototipo; esta hipótesis requiere una lista de materiales y cotizaciones para validarse.

## 7. Indicadores financieros

Margen de contribución unitario:

MC = precio de venta − costo comercial unitario = 300 − 200 = USD 100.

EBITDA mensual simplificado:

EBITDA = ingresos − costos variables − costos fijos.

Punto de equilibrio operativo mensual:

Q_PE = costos fijos mensuales / margen de contribución unitario = 25 / 100 = 0,25 máquinas/mes.

El punto de equilibrio operativo no incluye recuperar el costo inicial del prototipo. Para recuperar también los USD 400 iniciales, se debe considerar el flujo acumulado de todo el horizonte.

El VAN se calcula descontando los flujos mensuales a partir de una tasa anual del 12 %, convertida a tasa mensual equivalente. El modelo no incluye impuestos, financiamiento, depreciación ni capital de trabajo; sus resultados son preliminares.

## 8. Limitaciones

- La muestra corresponde a 100 personas de Quito y no es un censo de establecimientos.
- No se preguntó si cada productor corresponde a cafetería, restaurante o emprendimiento independiente.
- No se puede estimar directamente con la encuesta qué porcentaje de los 6.873 establecimientos vende empanadas de verde.
- La intención de compra y la disposición de pago son declaradas, no transacciones observadas.
- Los escenarios comerciales y económicos son hipótesis editables.
- Los costos deben actualizarse con cotizaciones y una lista de materiales.
- La capacidad de 20–50 empanadas/h es un rango de diseño configurable y requiere validación experimental.
