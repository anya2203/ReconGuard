from fastapi import FastAPI

from app.database import Base, engine
import app.models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ReconGuard")


@app.get("/health")
def health_check():
    return {"status": "healthy"}