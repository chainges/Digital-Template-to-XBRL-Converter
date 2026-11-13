FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
CMD ["python", "-c", "import os; from waitress import serve; from digital_converter_webapp import create_app; serve(create_app(), host='0.0.0.0', port=int(os.environ.get('PORT', '8080')))"]