import sys
import os

# Agregar el directorio actual al path para importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import SessionLocal, engine, Base
from models.user_models import User, UserRole
from models.inventory_models import POSLocation
from models.cash_models import CashRegister
from routers.auth import get_password_hash

def initialize_database():
    """
    Script de inicialización para crear:
    1. Tablas de la base de datos
    2. Usuario administrador por defecto
    3. Punto de venta principal
    """
    print("Inicializando base de datos...")
    
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas de la base de datos creadas")
    
    db = SessionLocal()
    try:
        # Crear usuario admin si no existe
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin:
            # Usar contraseña más corta y segura
            password = "Admin123!"  # Contraseña más corta
            admin_user = User(
                username="admin",
                email="admin@inventario.com",
                hashed_password=get_password_hash(password),
                full_name="Administrador Principal",
                role=UserRole.ADMIN
            )
            db.add(admin_user)
            db.commit()
            print("✅ Usuario administrador creado")
            print("   Usuario: admin")
            print("   Contraseña: Admin123!")
            print("   Email: admin@inventario.com")
        else:
            print("✅ Usuario administrador ya existe")
        
        # Crear punto de venta principal si no existe
        main_pos = db.query(POSLocation).filter(POSLocation.name == "Punto de Venta Principal").first()
        if not main_pos:
            main_pos = POSLocation(
                name="Punto de Venta Principal",
                address="Ubicación principal del negocio"
            )
            db.add(main_pos)
            db.commit()
            db.refresh(main_pos)
            
            # Crear caja registradora para el punto de venta principal
            cash_register = CashRegister(pos_location_id=main_pos.id)
            db.add(cash_register)
            db.commit()
            print("✅ Punto de venta principal creado")
            
            # Crear usuario cajero de ejemplo
            cashier_password = "Cajero123!"
            cashier_user = User(
                username="cajero",
                email="cajero@inventario.com",
                hashed_password=get_password_hash(cashier_password),
                full_name="Cajero Principal",
                role=UserRole.CASHIER,
                pos_location_id=main_pos.id
            )
            db.add(cashier_user)
            db.commit()
            print("✅ Usuario cajero creado")
            print("   Usuario: cajero")
            print("   Contraseña: Cajero123!")
            
        else:
            print("✅ Punto de venta principal ya existe")
            
        # Crear usuario almacén de ejemplo
        warehouse_manager = db.query(User).filter(User.username == "almacen").first()
        if not warehouse_manager:
            warehouse_password = "Almacen123!"
            warehouse_user = User(
                username="almacen",
                email="almacen@inventario.com",
                hashed_password=get_password_hash(warehouse_password),
                full_name="Gerente de Almacén",
                role=UserRole.WAREHOUSE_MANAGER
            )
            db.add(warehouse_user)
            db.commit()
            print("✅ Usuario almacén creado")
            print("   Usuario: almacen")
            print("   Contraseña: Almacen123!")
        
        print("\n🎉 Inicialización completada exitosamente!")
        print("\n📋 Usuarios creados:")
        print("   - admin / Admin123! (Administrador)")
        print("   - almacen / Almacen123! (Gerente de Almacén)")
        print("   - cajero / Cajero123! (Cajero)")
        print("\n🚀 Para iniciar el servidor ejecuta: uvicorn main:app --reload")
        
    except Exception as e:
        print(f"❌ Error durante la inicialización: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    initialize_database()