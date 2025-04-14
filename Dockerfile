# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm

# Install the project into root
WORKDIR /

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/.venv/bin:$PATH"

# Install Google Chrome
RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | \
    tee -a /etc/apt/sources.list.d/google.list && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | \
    apt-key add - && \
    apt-get update && \
    apt-get install -y google-chrome-stable libxss1

# Install Chrome WebDriver
RUN BROWSER_MAJOR=$(google-chrome --version | sed 's/.* \([0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+\)\s*/\1/g') && \
    mkdir -p /opt/chromedriver-$BROWSER_MAJOR && \
    echo https://storage.googleapis.com/chrome-for-testing-public/$BROWSER_MAJOR/linux64/chromedriver-linux64.zip && \
    curl -sS -o /tmp/chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/$BROWSER_MAJOR/linux64/chromedriver-linux64.zip && \
    unzip -qq /tmp/chromedriver-linux64.zip -d /opt/chromedriver-$BROWSER_MAJOR && \
    rm /tmp/chromedriver-linux64.zip && \
    chmod +x /opt/chromedriver-$BROWSER_MAJOR/chromedriver-linux64/chromedriver && \
    ln -fs /opt/chromedriver-$BROWSER_MAJOR/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    DRIVER_MAJOR=$(chromedriver --version | sed 's/.* \([0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+\).*$/\1/g') && \
    echo "chrome version: $BROWSER_MAJOR" && \
    echo "chromedriver version: $DRIVER_MAJOR" && \
    if [ $BROWSER_MAJOR != $DRIVER_MAJOR ]; then echo "VERSION MISMATCH"; exit 1; fi

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the FastAPI application by default
# Uses `fastapi dev` to enable hot-reloading when the `watch` sync occurs
# Uses `--host 0.0.0.0` to allow access from outside the container
#CMD ["fastapi", "dev", "--host", "0.0.0.0", "src/uv_docker_example"]