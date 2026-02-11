from fastapi import status, Request
from fastapi.responses import JSONResponse
from api_transcoder.exceptions.exceptions import (
    UnsupportedFileTypeError,
    OsException,
    ResourceNotFoundError,
    TranscodingError,
    StorageError
)
from api_transcoder.schema import ApiResponse
import logging

logger = logging.getLogger(__name__)


async def unsupported_file_type_handler(request: Request, exc: UnsupportedFileTypeError):
    logger.warning(f"Unsupported file type error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiResponse(
            success=False,
            message="Invalid file type",
            error="Supported formats: .mp4, .avi, .mov"
        ).model_dump()
    )


async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
    logger.warning(f"Resource not found: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ApiResponse(
            success=False,
            message="Resource not found",
            error=str(exc)
        ).model_dump()
    )


async def transcoding_error_handler(request: Request, exc: TranscodingError):
    logger.error(f"Transcoding error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse(
            success=False,
            message="Transcoding failed",
            error="Failed to transcode video. Please try again."
        ).model_dump()
    )


async def storage_error_handler(request: Request, exc: StorageError):
    logger.error(f"Storage error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ApiResponse(
            success=False,
            message="Storage service unavailable",
            error="Failed to access storage. Please try again."
        ).model_dump()
    )


async def os_exception_handler(request: Request, exc: OsException):
    logger.error(f"OS error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse(
            success=False,
            message="System error",
            error="An unexpected system error occurred."
        ).model_dump()
    )


async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiResponse(
            success=False,
            message="Invalid request",
            error=str(exc)
        ).model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse(
            success=False,
            message="Internal server error",
            error="An unexpected error occurred. Please try again."
        ).model_dump()
    )
