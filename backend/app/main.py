from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.rate_limit import limiter
from app.reporting.api import router as report_generation_router
from app.routers import admin, audit, auth, doctors, ecg, legal_consents, organisations, patients, public, reports, usage, users

app = FastAPI(
    title="CardioNexus Clinical Precision Platform API",
    description="Backend for the CardioNexus (Neuro Cardiac Electrophysiology Platform) frontend.",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(organisations.router)
app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(ecg.router)
app.include_router(reports.router)
app.include_router(report_generation_router)
app.include_router(audit.router)
app.include_router(legal_consents.router)
app.include_router(usage.router)
app.include_router(admin.router)
app.include_router(public.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "service": "ncep-backend"}
