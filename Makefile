.PHONY: datos api web build test boletin bot

datos:            ## normaliza los CSV crudos y construye el parquet
	python backend/scripts/build_dataset.py --raw data/raw

descargar:        ## descarga los archivos anuales de Peru desde FIRMS
	python backend/scripts/download_history.py --country Peru --years 2000-2025

build:            ## compila el frontend
	cd frontend && npm install && npm run build

api:              ## servidor (web + API en el mismo puerto)
	python -m uvicorn api.main:app --app-dir backend --host 0.0.0.0 --port 8000

test:
	python -m pytest backend/tests -q

boletin:          ## imprime el boletin (sin enviarlo)
	python backend/scripts/notify_telegram.py --zone madrededios

bot:              ## guia y diagnostico de la conexion con Telegram
	python backend/scripts/telegram_setup.py
