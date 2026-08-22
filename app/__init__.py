from fastapi import FastAPI

app = FastAPI(
    title="ReconGuard API",
    description="AI-powered financial reconciliation controller",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}