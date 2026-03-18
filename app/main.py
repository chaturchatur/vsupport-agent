from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import NormalizePhoneRequest, NormalizePhoneResponse
from app.services.phone import normalize_phone

app = FastAPI(title="Vsupport Agent", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/normalize-phone", response_model=NormalizePhoneResponse)
def normalize_phone_endpoint(req: NormalizePhoneRequest):
    normalized, valid = normalize_phone(req.phone_number, req.default_region)
    return NormalizePhoneResponse(original=req.phone_number, normalized=normalized, valid=valid)
