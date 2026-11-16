# Validación retrospectiva de VIIRS → unión

La implementación calcula factores unión/MODIS y unión/VIIRS por separado, para cada periodo cuando hay muestras suficientes y con un factor global como alternativa. Sin tres periodos globales útiles para VIIRS no se inventa un factor ni se transforma el valor en cero; se informa como no disponible. En la vista de un solo sensor se muestran observaciones, no estimaciones.

Para evaluar el método con el parquet local, sin modificarlo:

```powershell
.\.venv\Scripts\python.exe backend\scripts\validacion_retrospectiva.py --sensor viirs
.\.venv\Scripts\python.exe backend\scripts\numeros_pitch.py
```

Cada año completo del solape se aparta de la calibración; la estimación de sus doce meses desde VIIRS se compara con la unión satelital observada. El entrenamiento puede incluir años posteriores. La unión no es verdad de campo, las detecciones no prueban cobertura completa, y el resultado no valida periodos fuera del solape. Los umbrales y los cambios en sensores a lo largo del tiempo son limitaciones. El resultado no es la precisión de detección de incendios.

## Prueba local en el entorno de desarrollo

Con el parquet de ejemplo del repositorio, **distinto al archivo de 2 212 061 filas de la participante**, SHA-256 `ad0913190f5785e09ab003f5212faf78f3089f96ba458d01b1bf4e062f38f8fc`: 14 años evaluados (2012–2025), mediana del error absoluto porcentual anual **1,27 %**, MAPE **1,23 %**, WAPE **1,18 %**, mayor error absoluto **2,73 %** (2025). Esta cifra no debe trasladarse al pitch de la participante sin ejecutar la validación en su parquet.

## Resultado comunicado por la participante con su parquet local

La participante ejecutó `python backend\scripts\validacion_retrospectiva.py --sensor viirs` y compartió la salida. Su parquet no está disponible en este entorno, por lo que el resultado se documenta como **comunicado por ella**, no como una ejecución reproducida aquí.

- Perú, recuadro configurado; 2 212 061 filas, desde 2000-11-11 hasta 2026-11-01.
- SHA-256: `297dae35869d56788f5108191bd22c2141f9f0371420ebb86f1487bd98455fef`.
- Celdas-día mensuales; 14 años del solape (2012–2025), excluyendo el año evaluado de la calibración. Ningún mes usó el factor global.

| Año | Unión observada | Estimación desde VIIRS | Error firmado | Error absoluto |
|---|---:|---:|---:|---:|
| 2012 | 102 272 | 101 438 | −0,82 % | 0,82 % |
| 2013 | 88 418 | 89 309 | +1,01 % | 1,01 % |
| 2014 | 77 152 | 78 989 | +2,38 % | 2,38 % |
| 2015 | 88 273 | 88 351 | +0,09 % | 0,09 % |
| 2016 | 124 219 | 122 715 | −1,21 % | 1,21 % |
| 2017 | 82 080 | 81 331 | −0,91 % | 0,91 % |
| 2018 | 93 051 | 93 329 | +0,30 % | 0,30 % |
| 2019 | 98 836 | 97 825 | −1,02 % | 1,02 % |
| 2020 | 132 140 | 134 565 | +1,83 % | 1,83 % |
| 2021 | 99 049 | 98 360 | −0,70 % | 0,70 % |
| 2022 | 132 084 | 129 708 | −1,80 % | 1,80 % |
| 2023 | 102 872 | 103 183 | +0,30 % | 0,30 % |
| 2024 | 134 932 | 133 490 | −1,07 % | 1,07 % |
| 2025 | 70 155 | 72 499 | +3,34 % | 3,34 % |

**Resumen:** mediana del error absoluto porcentual anual **1,02 %**; MAPE **1,20 %**; WAPE **1,18 %**; mediana del error firmado **−0,30 %**; máximo **3,34 %** en 2025. Las cifras anuales mostradas se redondean; los errores se calcularon sin redondear.

Es una comparación retrospectiva contra la unión de satélites, no contra incendios de campo. No valida los periodos fuera del solape, otros departamentos ni otras medidas o frecuencias; tener detecciones mensuales no garantiza cobertura completa. El entrenamiento puede incluir años posteriores al año evaluado.
