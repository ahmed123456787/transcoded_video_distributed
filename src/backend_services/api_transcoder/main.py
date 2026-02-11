from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api_transcoder.controllers.upload_controller import router as upload_controller
from api_transcoder.database import engine, Base
from api_transcoder.exceptions.handlers import (
    unsupported_file_type_handler,
    resource_not_found_handler,
    transcoding_error_handler,
    storage_error_handler,
    os_exception_handler,
    general_exception_handler,
    value_error_handler
)
from api_transcoder.exceptions.exceptions import (
    UnsupportedFileTypeError,
    ResourceNotFoundError,
    TranscodingError,
    StorageError,
    OsException
)
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

# Register exception handlers
app.add_exception_handler(UnsupportedFileTypeError, unsupported_file_type_handler)
app.add_exception_handler(ResourceNotFoundError, resource_not_found_handler)
app.add_exception_handler(TranscodingError, transcoding_error_handler)
app.add_exception_handler(StorageError, storage_error_handler)
app.add_exception_handler(OsException, os_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.include_router(upload_controller, prefix="/api")






