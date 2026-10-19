FROM python:3.12-slim
RUN pip install --no-cache-dir matplotlib==3.9.2
WORKDIR /analisis
COPY analizar.py .
ENTRYPOINT ["python", "analizar.py"]
