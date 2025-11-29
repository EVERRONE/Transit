from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="TransIt API",
    description="API for TransIt Document Translation SaaS",
    version="0.1.0"
)

# Configure CORS
origins = [
    "http://localhost:3000",  # Next.js frontend
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from transit.api.endpoints import translation, payment

app.include_router(translation.router, prefix="/api/v1/translation", tags=["translation"])
app.include_router(payment.router, prefix="/api/v1/payment", tags=["payment"])

@app.get("/")
async def root():
    return {"message": "TransIt API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
