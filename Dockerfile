FROM python:3.9-slim

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use PORT from environment with fallback
ENV PORT=5000
EXPOSE ${PORT}

# Configure Gunicorn with proper timeout and worker settings
CMD gunicorn --bind 0.0.0.0:${PORT} \
    --workers=1 \
    --timeout=120 \
    --keep-alive=120 \
    --access-logfile=- \
    --error-logfile=- \
    app:app
