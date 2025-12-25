FROM python:3.11.7-slim-bookworm

LABEL com.danswer.maintainer="founders@callosum.app"
LABEL com.danswer.description="This image is the web/frontend container of Callosum which \
contains code for both the Community and Enterprise editions of Callosum. If you do not \
have a contract or agreement with DanswerAI, you are not permitted to use the Enterprise \
Edition features outside of personal development or testing purposes. Please reach out to \
founders@callosum.app for more information. Please visit https://github.com/callosum-dot-app/callosum"

# DO_NOT_TRACK is used to disable telemetry for Unstructured
ENV DANSWER_RUNNING_IN_DOCKER="true" \
    DO_NOT_TRACK="true" \
    PLAYWRIGHT_BROWSERS_PATH="/app/.cache/ms-playwright"

# Create non-root user for security best practices
RUN groupadd -g 1001 callosum && \
    useradd -u 1001 -g callosum -m -s /bin/bash callosum && \
    mkdir -p /var/log/callosum && \
    chmod 755 /var/log/callosum && \
    chown callosum:callosum /var/log/callosum

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

# Install system dependencies
# cmake needed for psycopg (postgres)
# libpq-dev needed for psycopg (postgres)
# curl included just for users' convenience
# zip for Vespa step futher down
# ca-certificates for HTTPS
RUN apt-get update && \
    apt-get install -y \
        cmake \
        curl \
        zip \
        ca-certificates \
        libgnutls30 \
        libblkid1 \
        libmount1 \
        libsmartcols1 \
        libuuid1 \
        libxmlsec1-dev \
        pkg-config \
        gcc \
        nano \
        vim && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean



# Install Python dependencies
# Remove py which is pulled in by retry, py is not needed and is a CVE
COPY ./requirements/default.txt /tmp/requirements.txt
COPY ./requirements/ee.txt /tmp/ee-requirements.txt
RUN uv pip install --system --no-cache-dir --upgrade \
        -r /tmp/requirements.txt \
        -r /tmp/ee-requirements.txt && \
    pip uninstall -y py && \
    playwright install chromium && \
    playwright install-deps chromium && \
    chown -R callosum:callosum /app && \
    ln -s /usr/local/bin/supervisord /usr/bin/supervisord && \
    # Cleanup for CVEs and size reduction
    # https://github.com/tornadoweb/tornado/issues/3107
    # xserver-common and xvfb included by playwright installation but not needed after
    # perl-base is part of the base Python Debian image but not needed for Callosum functionality
    # perl-base could only be removed with --allow-remove-essential
    apt-get update && \
    apt-get remove -y --allow-remove-essential \
        perl-base \
        xserver-common \
        xvfb \
        cmake \
        libldap-2.5-0 \
        libxmlsec1-dev \
        pkg-config \
        gcc && \
    # Install here to avoid some packages being cleaned up above
    apt-get install -y \
        libxmlsec1-openssl \
        # Install postgresql-client for easy manual tests
        postgresql-client && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf ~/.cache/uv /tmp/*.txt && \
    rm -f /usr/local/lib/python3.11/site-packages/tornado/test/test.key

# Pre-downloading models for setups with limited egress
RUN python -c "from tokenizers import Tokenizer; \
Tokenizer.from_pretrained('nomic-ai/nomic-embed-text-v1')"

# Pre-downloading NLTK for setups with limited egress
RUN python -c "import nltk; \
nltk.download('stopwords', quiet=True); \
nltk.download('punkt_tab', quiet=True);"
# nltk.download('wordnet', quiet=True); introduce this back if lemmatization is needed

# Pre-downloading tiktoken for setups with limited egress
RUN python -c "import tiktoken; \
tiktoken.get_encoding('cl100k_base')"

# Set up application files
WORKDIR /app

# Enterprise Version Files
COPY --chown=callosum:callosum ./ee /app/ee
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set up application files
COPY --chown=callosum:callosum ./callosum /app/callosum
COPY --chown=callosum:callosum ./shared_configs /app/shared_configs
COPY --chown=callosum:callosum ./alembic /app/alembic
COPY --chown=callosum:callosum ./alembic_tenants /app/alembic_tenants
COPY --chown=callosum:callosum ./alembic.ini /app/alembic.ini
COPY supervisord.conf /usr/etc/supervisord.conf
COPY --chown=callosum:callosum ./static /app/static

# Escape hatch scripts
COPY --chown=callosum:callosum ./scripts/debugging /app/scripts/debugging
COPY --chown=callosum:callosum ./scripts/force_delete_connector_by_id.py /app/scripts/force_delete_connector_by_id.py
COPY --chown=callosum:callosum ./scripts/supervisord_entrypoint.sh /app/scripts/supervisord_entrypoint.sh
RUN chmod +x /app/scripts/supervisord_entrypoint.sh

# Put logo in assets
COPY --chown=callosum:callosum ./assets /app/assets

ENV PYTHONPATH=/app

# Default CALLOSUM_VERSION, typically overriden during builds by GitHub Actions.
ARG CALLOSUM_VERSION=0.0.0-dev
ENV CALLOSUM_VERSION=${CALLOSUM_VERSION}

# Default command which does nothing
# This container is used by api server and background which specify their own CMD
CMD ["tail", "-f", "/dev/null"]
