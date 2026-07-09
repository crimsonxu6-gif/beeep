from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.guidance import router as guidance_router

app = FastAPI(title="Beeep Guidance Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(guidance_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
