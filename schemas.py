from pydantic import BaseModel, EmailStr
from typing import Optional, List
from models import RoleEnum

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum = RoleEnum.STUDENT

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: RoleEnum
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None

class ModuleCreate(BaseModel):
    title: str
    order_index: int = 1

class CourseOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    teacher_id: int
    class Config:
        from_attributes = True

# Add to schemas.py

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class RoleUpdate(BaseModel):
    role: RoleEnum