from fastapi import APIRouter,Response, Depends
import uuid
from src.schema import VideoUploadedResponse, VideoCreateSchema
from src.models import VideoStatus
from src.services.storage_service import generate_object_name, get_presigned_url
from src.services.video_service import video_task_service
from src.database import get_db



router = APIRouter()


@router.post("/upload-video",response_model=VideoUploadedResponse)
async def upload_video(filename: str,db=Depends(get_db)):

    # Check the extension of the file.
    if not filename.endswith(('.mp4', '.avi', '.mov')):
        return Response(content="Unsupported file type",status_code=400)
    


    # Generate a unique object name for the video
    object_name = generate_object_name()
    presigned_url = get_presigned_url(object_name)


    video_obj = VideoCreateSchema(
        id=uuid.uuid4(),
        original_filename=filename,
        s3_bucket="videos",
        presigned_url=object_name,
        status=VideoStatus.WAITING_UPLOAD.value
    )
    video_task_service.create(db,obj_in=video_obj)


    return VideoUploadedResponse( 
        video_id=video_obj.id,
        upload_url = presigned_url,
        message="Video uploaded successfully"
    )

