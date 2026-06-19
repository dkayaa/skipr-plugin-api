FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /tmp/pyproject.toml
RUN pip install --no-cache-dir /tmp/pyproject.toml

COPY server/ .

RUN chmod +x entrypoint.sh

EXPOSE 8090

CMD ["./entrypoint.sh"]
