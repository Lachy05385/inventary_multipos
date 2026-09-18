# test_hash.py
from database.database import SessionLocal
from models.user_models import User
from routers.auth import verify_password

db = SessionLocal()
user = db.query(User).filter(User.username == "admin").first()
if user:
    print(f"Usuario: {user.username}")
    print(f"Hash almacenado: {user.hashed_password}")
    
    # Probar con la contraseña
    password = "Admin123!"
    result = verify_password(password, user.hashed_password)
    print(f"Contraseña '{password}' es correcta: {result}")
else:
    print("Usuario admin no encontrado")
db.close()