# Use official Python image
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY simulator/ ./simulator/

EXPOSE 8080

CMD ["python", "simulator/ddos_simulator.py"]
