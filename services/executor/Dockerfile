FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /app
COPY services/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock 'ansible-core==2.19.14' && useradd --uid 10001 --create-home app
COPY services /app/services
COPY infra/ansible/quarantine.yml /app/infra/ansible/quarantine.yml
RUN mkdir /policy && chown 10001:10001 /policy
USER 10001
CMD ["uvicorn", "services.executor.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
