from src.api_transcoder.services.base_service import BaseService
from src.api_transcoder.models import TranscodingJob as Job
from src.api_transcoder.schema import JobCreateSchema, JobUpdateSchema


class JobService(BaseService[Job, JobCreateSchema, JobUpdateSchema]):
    def __init__(self):
        super().__init__(Job)

    def create(self, db, *, obj_in):
        return super().create(db, obj_in=obj_in)