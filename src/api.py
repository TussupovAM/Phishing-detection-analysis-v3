"""Minimal REST API around the phishing detector (used for the Docker / CD part)."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .phishing_detector import PhishingDetector, load_dataset

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "sample_data.csv"
DATA_PATH = Path(os.environ.get("TRAIN_DATA", DEFAULT_DATA))
THRESHOLD = 0.5


class PredictRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=100,
                            description="URLs to classify (1-100 items)")


class Prediction(BaseModel):
    url: str
    label: int = Field(..., description="1 = phishing, 0 = legitimate")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability of phishing")


@asynccontextmanager
async def lifespan(app: FastAPI):
    data = load_dataset(DATA_PATH)
    app.state.model = PhishingDetector().fit(data["url"], data["label"])
    app.state.n_train = len(data)
    yield


app = FastAPI(title="Phishing Detection API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    """Liveness/readiness probe used by Docker, Jenkins and Kubernetes."""
    return {"status": "ok", "trained_on": app.state.n_train}


@app.post("/predict", response_model=list[Prediction])
def predict(request: PredictRequest) -> list[Prediction]:
    probs = app.state.model.predict_proba(request.urls)
    return [Prediction(url=u, label=int(p >= THRESHOLD), probability=round(p, 4))
            for u, p in zip(request.urls, probs, strict=True)]
