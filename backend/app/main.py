from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import api_keys, auth, breakfast, checkins, guests, housekeeping, reservations, rooms, self_checkin, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Grand Hilai Check-in System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(guests.router, prefix="/api/guests", tags=["Guests"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["Rooms"])
app.include_router(reservations.router, prefix="/api/reservations", tags=["Reservations"])
app.include_router(checkins.router, prefix="/api", tags=["Check-in/Check-out"])
app.include_router(breakfast.router, prefix="/api/breakfast", tags=["Breakfast"])
app.include_router(self_checkin.router, prefix="/api/self-checkin", tags=["Self Check-in"])
app.include_router(api_keys.router, prefix="/api/api-keys", tags=["API Keys"])
app.include_router(housekeeping.router, prefix="/api/housekeeping", tags=["Housekeeping"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
