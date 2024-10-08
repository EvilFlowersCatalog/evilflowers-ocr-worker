# SPDX-FileCopyrightText: 2022 James R. Barlow
# SPDX-License-Identifier: MPL-2.0

FROM ppc64le/ubuntu:22.04 as base

ENV LANG=C.UTF-8
ENV TZ=UTC
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

RUN apt-get update && apt-get install -y --no-install-recommends \
  python3 \
  libqpdf-dev \
  zlib1g \
  liblept5

FROM base as builder

# Note we need leptonica here to build jbig2
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential autoconf automake libtool \
  libleptonica-dev \
  zlib1g-dev \
  python3-dev \
  python3-distutils \
  python3-pip \
  libffi-dev \
  ca-certificates \
  curl \
  git \
  libcairo2-dev \
  pkg-config

# Compile and install jbig2
# Needs libleptonica-dev, zlib1g-dev
RUN \
  mkdir jbig2 \
  && curl -L https://github.com/agl/jbig2enc/archive/ea6a40a.tar.gz | \
  tar xz -C jbig2 --strip-components=1 \
  && cd jbig2 \
  && ./autogen.sh && ./configure && make && make install \
  && cd .. \
  && rm -rf jbig2

COPY . /app

WORKDIR /app

RUN pip3 install --no-cache-dir .[test,webservice,watcher]

FROM base

# For Tesseract 5
RUN apt-get update && apt-get install -y --no-install-recommends \
  software-properties-common gpg-agent
RUN add-apt-repository -y ppa:alex-p/tesseract-ocr-devel

RUN apt-get update && apt-get install -y --no-install-recommends \
  ghostscript \
  fonts-droid-fallback \
  jbig2dec \
  img2pdf \
  libsm6 libxext6 libxrender-dev \
  pngquant \
  python-is-python3 \
  tesseract-ocr \
  tesseract-ocr-all \
  unpaper \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY --from=builder /app/misc/webservice.py /app/
COPY --from=builder /app/misc/watcher.py /app/

# Copy minimal project files to get the test suite.
COPY --from=builder /app/pyproject.toml /app/README.md /app/
COPY --from=builder /app/tests /app/tests

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
