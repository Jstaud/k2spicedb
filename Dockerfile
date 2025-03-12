# Use a lightweight Python image
FROM python:3.10-slim

# Install Poetry
RUN pip install --no-cache-dir poetry

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

# Copy source code
COPY . /app

# By default, run the CLI
ENTRYPOINT ["poetry", "run", "python", "-m", "k2spicedb.cli"]
