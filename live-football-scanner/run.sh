#!/usr/bin/env bash
# Avvio rapido: installa le dipendenze, compila la dashboard e avvia il server su http://127.0.0.1:8000
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  echo "File .env mancante: copia .env.example in .env e inserisci API_FOOTBALL_KEY." >&2
fi
python3 -m pip install -q -r backend/requirements.txt
if [ ! -f backend/models/inplay_model.json ]; then
  echo "Modello non trovato: scarico i dati StatsBomb e addestro (circa 10 minuti)..."
  (cd backend && python3 -m training.statsbomb_download && python3 -m training.train)
fi
if [ ! -d frontend/dist ]; then
  (cd frontend && npm install --no-audit --no-fund && npm run build)
fi
cd backend
exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}"
