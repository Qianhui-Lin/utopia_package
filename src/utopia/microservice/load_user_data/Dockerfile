FROM python:3.9-slim AS builder

WORKDIR /app


RUN pip install poetry

RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* README.md ./
COPY src/ ./src

# Install Poetry
RUN poetry install --no-interaction --no-ansi \
    && rm -rf /root/.cache/pypoetry /root/.cache/pip

# Second stage: minimal final image
FROM python:3.9-slim

WORKDIR /app

COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the rest of your code
#COPY . .

# Set Pythonpath for src layout
ENV PYTHONPATH=/app/src

EXPOSE 8001

# Set the default command 
CMD ["uvicorn", "utopia.microservice.load_user_data.load_user_data_app:app", "--host", "0.0.0.0", "--port", "8001"]

#testing for ci_2