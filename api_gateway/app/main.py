from fastapi import FastAPI
from .handlers import router

app = FastAPI(title="API Gateway")
app.include_router(router)
