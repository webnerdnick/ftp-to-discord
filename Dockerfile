FROM python:3.11-slim

WORKDIR /app

ADD requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

ADD server.py /app/server.py

EXPOSE 21 30000-30010

CMD ["python", "/app/server.py"]
