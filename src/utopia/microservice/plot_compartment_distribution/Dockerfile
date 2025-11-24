FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies needed for building packages like psutil
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        python3-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry
# RUN pip install poetry

RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* README.md ./
COPY src/ ./src

# Install Poetry
RUN poetry install --no-interaction --no-ansi \
    && rm -rf /root/.cache/pypoetry /root/.cache/pip

# Second stage: minimal final image
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the rest of your code
#COPY . .

# Set Pythonpath for src layout
ENV PYTHONPATH=/app/src

EXPOSE 8010


# Set the default command 
CMD ["uvicorn", "utopia.microservice.plot_compartment_distribution.plot_compartment_distribution_app:app", "--host", "0.0.0.0", "--port", "8010"]