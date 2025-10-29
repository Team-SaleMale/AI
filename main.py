from fastapi import FastAPI

app = FastAPI(title="Auction AI Server")

@app.get("/")
def tmp():
    return {
        "status": "ok",
        "message": "Auction AI Server is running!",
        "version": "1.0.0"
    }