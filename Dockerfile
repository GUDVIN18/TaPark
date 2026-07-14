FROM python:3.11

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONPATH=/app

EXPOSE 8881
CMD ["bash", "-c", "uvicorn main:app --host 0.0.0.0 --port 8881 --workers 1"]
