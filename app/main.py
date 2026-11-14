from fastapi import FastAPI

app = FastAPI(title="ads-platform")

@app.get("/health")
def health():
    return {"status": "ok"}