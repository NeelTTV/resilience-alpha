# Temporary deployment/test tooling only. Never used by an application service.
FROM docker:28-cli AS cli
FROM python:3.12-slim
COPY --from=cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=cli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins
COPY services/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock 'ansible-core==2.19.14'
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["sleep", "infinity"]
