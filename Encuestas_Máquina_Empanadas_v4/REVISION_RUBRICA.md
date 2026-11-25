# Revisión de EmpanaMaq frente a la rúbrica de la primera fase

La aplicación contribuye principalmente al criterio de encuestas, análisis de datos y priorización de necesidades. No sustituye los demás entregables del proyecto.

| Criterio | Puntos | Aporte de EmpanaMaq | Pendiente |
|---|---:|---|---|
| 1. Planteamiento, metodología y ciclo de vida | 10 | Curva comercial de 48 meses y supuestos de mercado. | Redacción del problema, objetivos, metodología y ciclo de vida físico/ambiental. |
| 2. Análisis preliminar en OpenLCA | 12 | La app no reemplaza OpenLCA. | Unidad funcional, límites, inventario, base de datos, método de impacto y resultados. |
| 3. Encuesta Python/Streamlit y necesidades | 12 | Cuestionario, 100 respuestas reales anonimizadas, estadísticas, prioridades y descarga. | Enlace público funcional y almacenamiento persistente para respuestas en línea. |
| 4. Tres casas de calidad QFD | 20 | La matriz de requerimientos aporta necesidades y porcentajes para alimentar la primera casa. | Tres casas relacionadas con escalas, relaciones, ponderaciones y cálculos. |
| 5. Análisis funcional y modular | 10 | La pestaña de diseño relaciona necesidades con los módulos C1. | Diagrama funcional, entradas, salidas e interfaces. |
| 6. Matriz morfológica y alternativas | 10 | La app contextualiza necesidades de diseño. | Presentar alternativas compatibles por subfunción. |
| 7. Selección del concepto y módulos | 8 | C1 se muestra como concepto seleccionado preliminarmente. | Justificar criterios, pesos y matriz de decisión. |
| 8. Agente de IA para bocetos | 10 | No está implementado en la app. | Documentar agente, entradas, prompts, resultados e iteraciones. |
| 9. Boceto y representación conceptual | 5 | Los módulos de C1 aportan la estructura de referencia. | Presentar vistas y módulos identificados. |
| 10. Calidad técnica del informe y trazabilidad | 3 | Datos originales, base normalizada, código y metodología facilitan trazabilidad. | Integrar referencias, anexos, figuras y coherencia entre encuesta, QFD y concepto. |

## Criterio 3: encuesta

La base utilizada es exclusivamente la última encuesta entregada, de 100 respuestas de Quito, de las cuales 56 corresponden a productores. La aplicación anonimiza los registros con códigos internos y conserva las respuestas originales. Los análisis condicionados a producción utilizan solamente las 56 respuestas afirmativas.

La aplicación está preparada para presentar el cuestionario, resultados estadísticos, análisis de datos y priorización. Para completar la evidencia de la rúbrica se debe publicar y comprobar un enlace público funcional. Si se reciben respuestas mediante Streamlit Cloud, se debe conectar almacenamiento externo persistente.

## Trazabilidad

La aplicación sirve como fuente de necesidades, no como sustituto del proceso completo:

Respuestas → análisis estadístico → necesidades jerarquizadas → QFD 1 → QFD 2 → QFD 3 → funciones y módulos → matriz morfológica → alternativas → matriz de decisión → concepto seleccionado → boceto.

La curva comercial de 48 meses no reemplaza el análisis ambiental del ciclo de vida mediante OpenLCA.
