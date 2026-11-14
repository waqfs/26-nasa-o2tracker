FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN pip install --no-cache-dir -e . --no-deps
EXPOSE 8010
CMD ["python", "scripts/serve.py"]
