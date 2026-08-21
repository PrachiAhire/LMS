from database import SessionLocal, engine, Base
import models
import auth

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

def update_or_create_user(role, role_enum):
    print(f"\n--- Set Details for {role.upper()} ---")
    name = input(f"Enter {role} Name: ").strip()
    email = input(f"Enter {role} Email: ").strip().lower()
    password = input(f"Enter {role} Password: ").strip()

    if not email or not password:
        print(f"Skipping {role} (email and password cannot be empty).")
        return

    # Check if a user with this email already exists
    user = db.query(models.User).filter(models.User.email == email).first()
    hashed_pwd = auth.hash_password(password)

    if user:
        user.name = name or user.name
        user.hashed_password = hashed_pwd
        user.role = role_enum
        print(f" Updated existing account: {email}")
    else:
        new_user = models.User(
            name=name or f"Default {role}",
            email=email,
            hashed_password=hashed_pwd,
            role=role_enum
        )
        db.add(new_user)
        print(f" Created new {role} account: {email}")

print("========================================")
print("     CUSTOM USER CREDENTIALS SETUP      ")
print("========================================")

# Prompt for each role
update_or_create_user("Admin", models.RoleEnum.ADMIN)
update_or_create_user("Teacher", models.RoleEnum.TEACHER)
update_or_create_user("Student", models.RoleEnum.STUDENT)

db.commit()
db.close()

print("\n All custom credentials saved to the database successfully!")