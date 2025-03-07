from fastapi import FastAPI
from .handlers import router



app = FastAPI(title="User Service")
app.include_router(router)
