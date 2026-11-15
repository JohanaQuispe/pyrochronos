# Validación retrospectiva: salida de los datos locales

La participante ejecutó `python backend\scripts\validacion_retrospectiva.py` en su equipo y compartió
esta salida. El parquet local **no está disponible en el entorno del repositorio**, por lo que estas
cifras se documentan como resultado comunicado, no como una ejecución reproducida aquí.

- Zona: Perú, recuadro configurado; 2 212 061 filas en el archivo.
- Cobertura global del archivo: 2000-11-11 a 2026-11-01; solape configurado: 2012-01-01 a 2025-12-31.
- SHA-256 del archivo parquet: `297dae35869d56788f5108191bd22c2141f9f0371420ebb86f1487bd98455fef`.
- Celdas-día mensuales; calibración dejando fuera todo el año evaluado. Ningún mes recurrió al factor global.

| Año | Unión observada | Estimación desde MODIS | Error firmado | Error absoluto |
|---|---:|---:|---:|---:|
| 2012 | 102 272 | 106 417 | +4,05 % | 4,05 % |
| 2013 | 88 418 | 84 210 | −4,76 % | 4,76 % |
| 2014 | 77 152 | 69 163 | −10,36 % | 10,36 % |
| 2015 | 88 273 | 85 833 | −2,76 % | 2,76 % |
| 2016 | 124 219 | 137 268 | +10,50 % | 10,50 % |
| 2017 | 82 080 | 85 866 | +4,61 % | 4,61 % |
| 2018 | 93 051 | 94 121 | +1,15 % | 1,15 % |
| 2019 | 98 836 | 105 687 | +6,93 % | 6,93 % |
| 2020 | 132 140 | 125 374 | −5,12 % | 5,12 % |
| 2021 | 99 049 | 102 290 | +3,27 % | 3,27 % |
| 2022 | 132 084 | 151 298 | +14,55 % | 14,55 % |
| 2023 | 102 872 | 103 654 | +0,76 % | 0,76 % |
| 2024 | 134 932 | 147 862 | +9,58 % | 9,58 % |
| 2025 | 70 155 | 56 336 | −19,70 % | 19,70 % |

**Resumen:** 14 años; mediana del error absoluto porcentual anual **4,94 %**; media (MAPE) **7,01 %**;
error absoluto ponderado por volumen (WAPE) **7,04 %**; mediana del error firmado **+2,21 %**.
Las estimaciones mostradas se redondean a enteros; el programa calcula los porcentajes sin redondear.

La unión MODIS+VIIRS es una referencia satelital, no confirmación en campo. La validación es
retrospectiva y el entrenamiento puede incluir años posteriores al evaluado. No demuestra la
precisión de incendios confirmados, no valida directamente antes de 2012 ni el caso de VIIRS sin
MODIS. Doce meses con detecciones de ambos sensores no garantizan cobertura satelital completa.
El archivo de ejemplo del repositorio es diferente y produce cifras distintas. Ver `metodologia.md`.
