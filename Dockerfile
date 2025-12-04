# Stage 1: builder
FROM python:3.11-slim AS builder
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /build

# install build deps (only if needed by some packages)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# create venv for isolation
ENV VENV_PATH=/opt/venv
RUN python -m venv $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH"

# copy dependency spec and install (cache-friendly)
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# copy app code
COPY . /build

# Stage 2: runtime
FROM python:3.11-slim AS runtime
ENV TZ=UTC
ENV DEBIAN_FRONTEND=noninteractive

# create non-root user
RUN groupadd --gid 1000 appgroup || true \
 && useradd --uid 1000 --gid appgroup --create-home --shell /bin/bash appuser || true

WORKDIR /app

# install minimal system packages: cron (daemon), tzdata (timezone), ca-certs
RUN apt-get update \
  && apt-get install -y --no-install-recommends cron tzdata ca-certificates gosu \
  && rm -rf /var/lib/apt/lists/*

# ensure UTC timezone
RUN ln -snf /usr/share/zoneinfo/UTC /etc/localtime && echo "UTC" > /etc/timezone

# copy virtualenv with installed deps from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# copy app source
COPY --from=builder /build /app

# copy cron file into /etc/cron.d and set permissions
COPY cron/app-cron /etc/cron.d/app-cron
RUN chmod 0644 /etc/cron.d/app-cron \
 && crontab /etc/cron.d/app-cron || true

# create volumes and set ownership
RUN mkdir -p /data /cron /var/run /var/log \
  && chown -R appuser:appgroup /data /cron /var/log \
  && chmod 755 /data /cron /var/log \
  && chown root:root /var/run && chmod 755 /var/run


VOLUME [ "/data", "/cron" ]

EXPOSE 8080

# entrypointCOPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r//g' /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Keep entrypoint running as root so it can start cron and then drop privileges using gosu
USER 0
ENTRYPOINT [ "/usr/local/bin/docker-entrypoint.sh" ]
CMD [ "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info" ]



RUN mkdir -p /var/run/cron \
    && chown -R appuser:appgroup /var/run/cron \
    && chmod 775 /var/run/cron
