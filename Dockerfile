FROM python:3.11-slim

# Update and upgrade the system packages
RUN apt update && apt upgrade -y

# Install curl (required to download the uv installer)
RUN apt install -y curl

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add /root/.local/bin to PATH
ENV PATH="/root/.local/bin:$PATH"

# Verify uv installation
RUN uv --version

# Set the working directory
WORKDIR /opt

# Copy necessary files into the container
COPY pyproject.toml .
COPY models/sa_models.py models/.
COPY fargate_tasks/load_db.py .
COPY .env .

# Create a virtual environment
RUN uv venv --python 3.11

# Activate the virtual environment and sync dependencies
RUN . .venv/bin/activate && uv sync

# Set the virtual environment as the default Python interpreter
ENV PATH="/opt/.venv/bin:$PATH"

# # Command to run your application (adjust as needed)
CMD ["python", "load_db.py"]