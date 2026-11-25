"""Prepara la base de Google Forms para EmpanaMaq.

Uso:
    python preparar_base.py

Lee encuesta_original_anonimizada.csv y genera encuesta_real.csv.
No elimina respuestas coincidentes ni altera el texto original.
"""
from pathlib import Path
import pandas as pd
from modelo import normalizar_encuesta_original

BASE = Path(__file__).parent
ORIGINAL = BASE / "encuesta_original_anonimizada.csv"
SALIDA = BASE / "encuesta_real.csv"

if not ORIGINAL.exists():
    raise FileNotFoundError(f"No se encontró {ORIGINAL.name} en {BASE}")

df_original = pd.read_csv(ORIGINAL, encoding="utf-8-sig")
df_normalizado = normalizar_encuesta_original(df_original)
df_normalizado.to_csv(SALIDA, index=False, encoding="utf-8-sig")

productores = int(df_normalizado["es_productor"].sum())
pares = int(df_normalizado["productividad_empanadas_h"].notna().sum())
print(f"Base normalizada: {len(df_normalizado)} respuestas")
print(f"Productores: {productores}")
print(f"No productores: {len(df_normalizado) - productores}")
print(f"Productividades calculables: {pares}")
print(f"Archivo generado: {SALIDA.name}")
