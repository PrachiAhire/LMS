from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import models, schemas, auth
from database import engine, get_db
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="LMS Core API - V1")
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_frontend():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

# --- AUTH ROUTES ---
@app.post("/auth/register", response_model=schemas.UserOut)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = auth.hash_password(user_in.password)
    new_user = models.User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=hashed_pwd,
        role=user_in.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    token = auth.create_access_token(data={"sub": user.email, "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}

# --- COURSE & MODULE ROUTES (Teacher/Admin only) ---
@app.post("/courses/", response_model=schemas.CourseOut)
def create_course(
    course_in: schemas.CourseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.TEACHER, models.RoleEnum.ADMIN]))
):
    course = models.Course(**course_in.dict(), teacher_id=current_user.id)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@app.post("/courses/{course_id}/modules")
def add_module(
    course_id: int,
    module_in: schemas.ModuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.TEACHER, models.RoleEnum.ADMIN]))
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != models.RoleEnum.ADMIN and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this course")
    
    module = models.Module(**module_in.dict(), course_id=course_id)
    db.add(module)
    db.commit()
    return {"message": "Module added successfully", "module_id": module.id}

# --- ENROLLMENT ROUTES (Students/Admin only) ---
@app.post("/courses/{course_id}/enroll")
def enroll_in_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.STUDENT, models.RoleEnum.ADMIN]))
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    existing = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == current_user.id,
        models.Enrollment.course_id == course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")
    
    enrollment = models.Enrollment(student_id=current_user.id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    return {"message": f"Successfully enrolled in {course.title}"}
# --- VIEWING / GET ROUTES ---

@app.get("/courses/")
def list_all_courses(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(models.Course).offset(skip).limit(limit).all()

@app.get("/courses/{course_id}")
def get_course_details(course_id: int, db: Session = Depends(get_db)):
    """View a single course and all of its modules."""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    modules = db.query(models.Module).filter(models.Module.course_id == course_id).all()
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "teacher_id": course.teacher_id,
        "modules": modules
    }

@app.get("/my-enrollments")
def get_my_enrollments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.STUDENT]))
):
    """Students can view all courses they are currently enrolled in."""
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == current_user.id).all()
    enrolled_courses = [
        {"enrollment_id": e.id, "course_id": e.course_id, "course_title": e.course.title, "enrolled_at": e.enrolled_at}
        for e in enrollments
    ]
    return enrolled_courses

@app.get("/auth/me")
def get_my_profile(current_user: models.User = Depends(auth.get_current_user)):
    """Check currently logged in user details and role."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role
    }
@app.get("/courses/{course_id}/students")
def get_enrolled_students(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.TEACHER, models.RoleEnum.ADMIN]))
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != models.RoleEnum.ADMIN and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this course roster")

    enrollments = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id).all()
    return [{"student_id": e.student.id, "name": e.student.name, "email": e.student.email, "enrolled_at": e.enrolled_at} for e in enrollments]
# ==========================================
# 1. COURSE CRUD & ROSTER (TEACHER / ADMIN)
# ==========================================

@app.put("/courses/{course_id}", response_model=schemas.CourseOut)
def update_course(
    course_id: int,
    course_update: schemas.CourseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.TEACHER, models.RoleEnum.ADMIN]))
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Only course owner or admin can edit
    if current_user.role != models.RoleEnum.ADMIN and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this course")
    
    if course_update.title is not None:
        course.title = course_update.title
    if course_update.description is not None:
        course.description = course_update.description
        
    db.commit()
    db.refresh(course)
    return course


@app.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.TEACHER, models.RoleEnum.ADMIN]))
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Only course owner or admin can delete
    if current_user.role != models.RoleEnum.ADMIN and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this course")
    
    db.delete(course)
    db.commit()
    return {"message": f"Course '{course.title}' deleted successfully"}


@app.get("/courses/{course_id}/students")
def get_enrolled_students(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.TEACHER, models.RoleEnum.ADMIN]))
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != models.RoleEnum.ADMIN and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this course roster")

    enrollments = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id).all()
    return [
        {
            "student_id": e.student.id,
            "name": e.student.name,
            "email": e.student.email,
            "enrolled_at": e.enrolled_at
        }
        for e in enrollments
    ]


# ==========================================
# 2. STUDENT UNENROLLMENT
# ==========================================

@app.delete("/courses/{course_id}/unenroll")
def unenroll_from_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.STUDENT, models.RoleEnum.ADMIN]))
):
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.course_id == course_id,
        models.Enrollment.student_id == current_user.id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment record not found")
    
    db.delete(enrollment)
    db.commit()
    return {"message": "Successfully unenrolled from course"}


# ==========================================
# 3. ADMIN MANAGEMENT ROUTES (ADMIN ONLY)
# ==========================================

@app.get("/admin/users", response_model=list[schemas.UserOut])
def list_all_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN]))
):
    """Admin-only view of all accounts in the database."""
    return db.query(models.User).all()


@app.patch("/admin/users/{user_id}/role", response_model=schemas.UserOut)
def change_user_role(
    user_id: int,
    role_in: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN]))
):
    """Admin can promote or demote user roles."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = role_in.role
    db.commit()
    db.refresh(user)
    return user


@app.delete("/admin/users/{user_id}")
def delete_user_account(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN]))
):
    """Admin can delete any user account."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Admins cannot delete their own account")
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"message": f"User '{user.name}' ({user.email}) deleted successfully"}

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse("templates/index.html")

