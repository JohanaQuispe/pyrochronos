# Uso de inteligencia artificial

Durante el desarrollo se utilizó asistencia de IA en Arena.ai para apoyar tareas de programación, pruebas y redacción. El equipo es responsable de revisar los resultados y sus limitaciones. Las pruebas automatizadas y las comprobaciones realizadas se describen en [verificado.md](verificado.md).

## En la aplicación

La aplicación no usa un modelo de lenguaje para responder preguntas. El asistente de la web y del bot utiliza reglas y plantillas; los cálculos se realizan con código a partir de los datos cargados. Las respuestas deben verificarse y no sustituyen el criterio operativo.

## Datos y servicios externos

El bot consulta NASA FIRMS y se comunica con Telegram para recibir mensajes y enviar avisos. Las ubicaciones que se comparten con el bot y los datos de un aviso pueden transmitirse a través de Telegram. El mapa base solicita imágenes a OpenStreetMap. Los datos locales de ubicaciones y verificaciones requieren protección si la aplicación se publica.

Las claves se configuran en el servidor o en `.env`, que no debe publicarse. No incluyas coordenadas personales, tokens ni claves en capturas o demostraciones.
