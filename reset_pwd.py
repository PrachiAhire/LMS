from database import SessionLocal
import models
import auth

db = SessionLocal()

# List all users in the database so you can see the exact email
users = db.query(models.User).all()
print("\n--- FOUND USERS IN DATABASE ---")
for u in users:
    print(f"ID: {u.id} | Email: {u.email} | Role: {u.role}")

if users:
    # Update password for the first user or target email
    target_user = users[0]
    target_user.hashed_password = auth.hash_password("password123")
    db.commit()
    print(f"\n Password for '{target_user.email}' has been reset to: password123")
else:
    print("\nNo users found in database.")

db.close()