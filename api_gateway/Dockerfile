FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/posts.proto
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/stats.proto

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
