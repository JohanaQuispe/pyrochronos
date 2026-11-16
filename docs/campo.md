# Bot y datos de campo

El bot de Telegram puede avisar sobre detecciones recientes de calor cerca de una ubicación compartida. Una detección no confirma un incendio, los datos pueden tener retraso y el aviso no reemplaza fuentes oficiales ni la verificación en campo.

## Empezar

1. Configura `FIRMS_MAP_KEY` y `TELEGRAM_BOT_TOKEN` en tu `.env` local. Nunca compartas esas claves.
2. Desde la carpeta del proyecto, inicia una sola instancia:

   ```bash
   python backend/scripts/bot.py --poll --auto-refresh --zone peru
   ```

3. Abre un chat privado con el bot, envía `/start`, comparte tu ubicación y elige la distancia. `/estado` muestra la configuración guardada, no garantiza que el bot esté funcionando.
4. Opcionalmente añade `--heartbeat` al comando para recibir la confirmación periódica de vigilancia en tu chat privado. Si el proceso o la conexión fallan, esa confirmación también puede dejar de llegar.

El bot intenta actualizar FIRMS y revisar detecciones aproximadamente cada 15 minutos. Si no está en ejecución, no vigila. La confirmación periódica ya fue recibida por la participante; la entrega automática de una alerta por un foco real cercano aún no se ha comprobado. La [guía de comprobación](comprobacion-alerta-real.md) explica cómo revisarlo sin inventar una alerta.

## Qué selecciona

El bot usa detecciones del archivo reciente de los últimos tres días UTC, solo cuando la descarga está fresca y cubre la zona configurada. Calcula un umbral histórico de intensidad FRP por sensor y considera detecciones que alcanzan ese umbral y al menos 20 MW, dentro de la distancia elegida. Los avisos incluyen información del punto y botones para registrar una verificación; también intenta enviar un pin. No avisa de todos los focos, y la fecha disponible es UTC, no la hora exacta de detección.

La selección de zona en la web **no cambia** la zona con la que se inició el bot. El envío y los datos dependen de FIRMS, Telegram, internet y el proceso en ejecución.

## Privacidad y almacenamiento

Las ubicaciones, verificaciones y el historial de envíos se guardan como archivos JSON locales en `data/derived/` o en la carpeta indicada por `PYRO_FIELD_DIR`. En un grupo, las ubicaciones compartidas son visibles para sus miembros; usa el chat privado para compartir una ubicación personal. Al compartirla nuevamente desde otro chat, ese chat pasa a ser el destino de sus avisos.

La API puede mostrar ubicaciones y verificaciones. **No expongas la aplicación públicamente con datos personales sin implementar protección de acceso adecuada.** `PYRO_SETUP_KEY` protege el registro cuando está configurada, pero no protege todos los endpoints de lectura.

El backend conserva herramientas opcionales de NASA POWER, pero el contexto climático no forma parte de la interfaz actual. No hay Supabase ni PostGIS implementados. Más detalles en [arquitectura](arquitectura-tactica.md).
