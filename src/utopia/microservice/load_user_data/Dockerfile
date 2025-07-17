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

EXPOSE 8001

# Set the default command 
CMD ["uvicorn", "utopia.microservice.load_user_data.load_user_data_app:app", "--host", "0.0.0.0", "--port", "8001"]