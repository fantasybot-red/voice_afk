FROM astral/uv:python3.11-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN uv sync

ENV IS_DOCKER=1

CMD ["uv", "run", "src/main.py"]