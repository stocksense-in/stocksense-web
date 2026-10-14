# StockSense API. Build from backend/:  docker build -t stocksense-api .
# Run:  docker run -p 8000:8000 -e SUPABASE_URL=... -e SUPABASE_ANON_KEY=... stocksense-api
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY stocksense ./stocksense
COPY data ./data
COPY _nse_symbols_cache.json .

ENV PORT=8000
EXPOSE 8000
# Hosts like Render/Railway set $PORT.
CMD ["sh", "-c", "uvicorn stocksense.api:app --host 0.0.0.0 --port ${PORT}"]
