FROM python:3.9-slim

WORKDIR /app

COPY ./testing_api-main/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./testing_api-main .

EXPOSE 5000

CMD ["python","app.py"]