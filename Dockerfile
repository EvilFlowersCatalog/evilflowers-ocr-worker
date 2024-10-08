FROM jbarlow83/ocrmypdf

RUN apt update -y && apt install tesseract-ocr-all -y

# Create a non-root user called 'celery' and set ownership of the directory
RUN useradd --system --home /usr/local/src --shell /bin/bash celery \
    && mkdir -p /usr/local/src \
    && chown -R celery:celery /usr/local/src

# Switch to the working directory
WORKDIR /usr/local/src

# Copy the application code and set ownership to 'celery'
COPY --chown=celery:celery . .

# Install Python dependencies
RUN pip install celery[redis] ocrmypdf

# Switch to the 'celery' user
USER celery

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 CMD celery -A evilflowers_ocr_worker status || exit 1

# Set the entrypoint and command to run the Celery worker
ENTRYPOINT ["celery", "-A", "evilflowers_ocr_worker", "worker", "-Q", "evilflowers_ocr_worker", "-E"]

