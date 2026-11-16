# Comprobación segura de alertas reales

Esto requiere tu bot, una clave FIRMS válida, internet y una ubicación compartida voluntariamente en Telegram. **No pegues claves ni coordenadas en un chat público.** El bot debe estar encendido en una sola terminal; dos procesos de polling con el mismo token interfieren.

1. Inicia `python backend/scripts/bot.py --poll --auto-refresh --zone peru` desde la carpeta del proyecto. En Telegram usa `/start`, comparte tu ubicación por chat privado y elige el radio. `/estado` confirma lo guardado, no la entrega de avisos.
2. En otra terminal, desde la misma carpeta, ejecuta `python backend/scripts/bot.py --check-live --zone peru`. Es solo lectura: informa si la descarga está fresca y cubre la zona, cuántas ubicaciones y coincidencias hay, y cuántas aún no constan como enviadas. No descarga, no envía ni altera el registro de avisos; no muestra coordenadas ni IDs.
3. Si hay un candidato pendiente y el proceso sigue abierto, espera el siguiente ciclo y comprueba **en Telegram** que llegó el aviso real. Mira también el log del bot, sin compartir tokens, IDs ni coordenadas. Una coincidencia en el diagnóstico no prueba entrega. Si no hay candidatos, no se puede forzar una alerta real: espera o usa `--send-demo` para probar el canal, que es una simulación histórica marcada como DEMO y no valida la vigilancia real.
4. Si falla FIRMS, la descarga es antigua, falta cobertura, la ubicación no fue registrada o Telegram rechaza el envío, no cuentes la prueba como superada. No cambies tu ubicación a un foco para aparentar validación en terreno ni borres la deduplicación.

El bot solo avisa detecciones que cumplen el umbral de intensidad y están en el radio configurado, sujetas a descarga, deduplicación y disponibilidad. Los puntos NRT no confirman incendios y pueden tener retraso.

## Idioma del bot

En Telegram escribe `/language en` para mensajes en inglés o `/idioma es` para volver a español. Se guarda por usuario y se mantiene al compartir una ubicación nueva. En grupos, quienes reciban un aviso compartido pueden tener distintos idiomas; el mensaje usa el idioma de la geocerca que genere ese envío.
