"""tiny fastapi app that holds memory on demand — built to get OOM-killed."""

import os

from fastapi import FastAPI

app = FastAPI()

held = []


@app.get("/")
def index():
    return {
        "app": os.environ.get("APP_NAME", "oom-demo"),
        "env": os.environ.get("APP_ENV", "unknown"),
        "message": os.environ.get("APP_MESSAGE", ""),
        "held_mb": round(sum(len(c) for c in held) / 1_048_576, 1),
    }


@app.post("/eat/{mb}")
def eat(mb: int):
    """allocate mb megabytes and hold them forever."""
    held.append(bytearray(mb * 1_048_576))
    total = round(sum(len(c) for c in held) / 1_048_576, 1)
    return {"allocated_mb": mb, "total_held_mb": total}


@app.post("/free")
def free():
    held.clear()
    return {"status": "freed"}
