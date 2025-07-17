FROM python:3.9-slim

# Install Poetry
RUN pip install poetry

WORKDIR /app

# Copy only dependency files first (for better caching)
COPY pyproject.toml poetry.lock* README.md ./
COPY src/ ./src

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the rest of your code
COPY . .

# Set Pythonpath for src layout
ENV PYTHONPATH=/app/src

EXPOSE 8002

# Set the default command 
CMD ["uvicorn", "utopia.microservice.generate_object.generate_object_app_new:app", "--host", "0.0.0.0", "--port", "8002"]
