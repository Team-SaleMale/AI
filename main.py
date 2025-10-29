from fastapi import FastAPI

app = FastAPI(title="ValueBid AI Server")

@app.get("/")
def tmp():
    return {
        "status": "ok",
        "message": "ValueBid AI Server is running!",
        "version": "1.0.0"
    }