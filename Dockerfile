FROM python:3.12-slim
WORKDIR /app
COPY server.py schema.sql ./
COPY web ./web
ENV HOST=0.0.0.0 PORT=8000 DATABASE_PATH=/data/addresses.sqlite3
VOLUME /data
EXPOSE 8000
CMD ["python", "server.py"]
