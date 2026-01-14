from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api_transcoder.controllers.upload_controller import router as upload_controller
from api_transcoder.database import engine, Base
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown code 


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_controller, prefix="/api")






