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
