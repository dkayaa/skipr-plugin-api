FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /tmp/skipr-api/pyproject.toml
RUN pip install --no-cache-dir /tmp/skipr-api

COPY server/ .

RUN chmod +x entrypoint.sh

EXPOSE 8090

CMD ["./entrypoint.sh"]
