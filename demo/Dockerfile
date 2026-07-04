FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY README.md pyproject.toml ./
COPY src ./src
COPY demo ./demo
COPY examples ./examples
COPY xsd ./xsd

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e .

CMD ["archi-twin-context", "--help"]
