from typing import Generic, Type, TypeVar
from pydantic import BaseModel
from sqlalchemy.orm import Session


ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        Generic service with default methods to Create and Update.
 
        **Parameters**

        * `model`: A SQLAlchemy model class
        """
        self.model = model

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: ModelType, obj_in: UpdateSchemaType
    ) -> ModelType:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_all(
        self, db: Session
    ) -> ModelType | None:
        return db.query(self.model)
    
    def get(
        self, db: Session, id
    ) -> ModelType | None:
        return db.query(self.model).filter(self.model.id == id).first()
    

    def delete(
        self, db: Session, *, id
    ) -> None:
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit(
    )