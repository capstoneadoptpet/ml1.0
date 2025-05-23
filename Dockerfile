FROM python:3.9-slim

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000
EXPOSE ${PORT}

# Change this line to match render.yaml
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]