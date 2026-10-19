FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home app
COPY services /app/services
COPY docs /app/docs
RUN mkdir /state /logs /policy && chown 10001:10001 /state /logs /policy
USER 10001
EXPOSE 8000
CMD ["uvicorn", "services.payment.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

