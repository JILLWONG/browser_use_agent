FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-wqy-zenhei \
        fonts-liberation \
        gnupg \
        libdrm2 \
        libnspr4 \
        libnss3 \
        libxrandr2 \
        libasound2 \
        libx11-xcb1 \
        libxcb-dri3-0 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libatspi2.0-0 \
        libgbm1 \
        libgtk-3-0 \
        libxinerama1 \
        libpango-1.0-0 \
        libvulkan1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxkbcommon0 \
        libxcursor1 \
        libxi6 \
        libxss1 \
        libgl1-mesa-glx \
        xdg-utils \
        xvfb \
        wget \
        unzip \
        libmagic1 \
        libreoffice \
        dpkg \
        apt-transport-https \
        ca-certificates \
        software-properties-common \
        dbus-x11 \
        curl && \
    rm -rf /var/lib/apt/lists/* && \
    fc-cache -fv

RUN apt --fix-broken install -y

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
ENV HOME=/tmp
ENV SEARCH_PORT="19090"
ENV PATH="/tmp/bin:${PATH}"
ENV PYTHONPATH="/var/task"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install Chrome
RUN apt update -y
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt install ./google-chrome-stable_current_amd64.deb

# Set up dbus
RUN mkdir -p /run/dbus
ENV DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
RUN service dbus start

ENV PATH="/usr/bin/google-chrome:${PATH}"

# Set working directory
WORKDIR /var/task

# Copy Python project files
COPY pyproject.toml uv.lock* ./
COPY README.md ./
COPY src/ ./src/
COPY browser-use/ ./browser-use/

# Install Python dependencies using uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --index-strategy unsafe-best-match

# Install browser-use from local directory
RUN uv add ./browser-use

RUN pip install playwright==1.52.0 -i https://mirrors.aliyun.com/pypi/simple/
RUN playwright install


# Expose Flask port
EXPOSE ${SEARCH_PORT}

# Use uv to run the application
CMD ["uv", "run", "browser-fastapi"]