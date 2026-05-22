FROM molluscai-base:v0.2

WORKDIR /app

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
