FROM python:3.10-slim

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/posts.proto

CMD ["python", "-m", "app.main"]
