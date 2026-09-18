# seed.py
"""
Script para poblar la base de datos con datos de prueba.
Ejecutar: python seed.py
"""
from database.database import SessionLocal, engine
from models import (
    User, Category, Product, Supplier, PurchaseEntry, PurchaseItem,
    WarehouseStock, POSLocation, POSStock, CashRegister, Sale, SaleItem
)
from models.user_models import UserRole
from routers.auth import get_password_hash
from datetime import datetime, timedelta
import random

def create_users(db):
    """Crear usuarios con diferentes roles"""
    password = "Admin123!"
    users = [
        User(
            username="admin",
            full_name="Administrador",
            email="admin@test.com",
            hashed_password=get_password_hash(password),
            role=UserRole.ADMIN,
            is_active=True
        ),
        
        User(
            username="warehouse",
            full_name="Gerente de Almacén",
            email="warehouse@test.com",
            hashed_password=get_password_hash(password),
            role=UserRole.WAREHOUSE_MANAGER,
            is_active=True
        ),
        User(
            username="cajero1",
            full_name="Cajero Principal",
            email="cajero1@test.com",
            hashed_password=get_password_hash(password),
            role=UserRole.CASHIER,
            is_active=True,
            pos_location_id=1  # Asignar al POS que crearemos después
        )
        
    ]
    db.add_all(users)
    db.commit()
    for u in users:
        db.refresh(u)
    return users

def create_categories(db):
    """Crear categorías de productos"""
    categories = [
        Category(name="Electrónicos", description="Productos electrónicos y gadgets"),
        Category(name="Ropa", description="Prendas de vestir"),
        Category(name="Alimentos", description="Productos alimenticios"),
        Category(name="Servicios", description="Servicios profesionales"),
    ]
    db.add_all(categories)
    db.commit()
    for c in categories:
        db.refresh(c)
    return categories

def create_products(db, categories):
    """Crear productos (físicos y servicios)"""
    products = [
        # Productos físicos (con inventario)
        Product(
            name="Laptop HP",
            description="Laptop HP 14 pulgadas, 8GB RAM, 256GB SSD",
            sku="LAP-001",
            price=850.00,
            cost=650.00,
            min_stock=5,
            category_id=categories[0].id,
            has_inventory=True
        ),
        Product(
            name="Mouse Inalámbrico",
            description="Mouse Bluetooth, batería recargable",
            sku="MOU-002",
            price=25.00,
            cost=15.00,
            min_stock=10,
            category_id=categories[0].id,
            has_inventory=True
        ),
        Product(
            name="Camisa Formal",
            description="Camisa de vestir, manga larga, talla M",
            sku="CAM-003",
            price=45.00,
            cost=30.00,
            min_stock=8,
            category_id=categories[1].id,
            has_inventory=True
        ),
        Product(
            name="Arroz 1kg",
            description="Arroz blanco de grano largo, 1kg",
            sku="ARR-004",
            price=1.50,
            cost=1.00,
            min_stock=20,
            category_id=categories[2].id,
            has_inventory=True
        ),
        # Servicios (sin inventario)
        Product(
            name="Mantenimiento de PC",
            description="Servicio de limpieza y mantenimiento de computadoras",
            sku="SVC-005",
            price=50.00,
            cost=0,
            min_stock=0,
            category_id=categories[3].id,
            has_inventory=False
        ),
        Product(
            name="Asesoría Contable",
            description="Asesoría y consultoría contable por hora",
            sku="SVC-006",
            price=80.00,
            cost=0,
            min_stock=0,
            category_id=categories[3].id,
            has_inventory=False
        ),
    ]
    db.add_all(products)
    db.commit()
    for p in products:
        db.refresh(p)
    return products

def create_suppliers(db):
    """Crear proveedores"""
    suppliers = [
        Supplier(
            name="Distribuidora Electrónica S.A.",
            code="DISELEC",
            contract_number="CT-001",
            document_type="invoice",
            contact_phone="555-0001",
            contact_email="ventas@distroelec.com",
            address="Av. Principal 123"
        ),
        Supplier(
            name="Textiles del Sur",
            code="TEXSUR",
            contract_number="CT-002",
            document_type="invoice",
            contact_phone="555-0002",
            contact_email="info@textilesur.com",
            address="Calle Comercio 456"
        ),
        Supplier(
            name="Alimentos El Buen Sabor",
            code="BUENSABOR",
            contract_number="CT-003",
            document_type="invoice",
            contact_phone="555-0003",
            contact_email="pedidos@buensabor.com",
            address="Mercado Central, Local 12"
        ),
    ]
    db.add_all(suppliers)
    db.commit()
    for s in suppliers:
        db.refresh(s)
    return suppliers

def create_purchase_entries(db, suppliers, products):
    """Crear entradas de compra con items y actualizar stock"""
    entries = []
    
    # Entrada 1: Electrónicos
    entry1 = PurchaseEntry(
        supplier_id=suppliers[0].id,
        document_number="FAC-001",
        document_date=datetime.now() - timedelta(days=5),
        total_amount=0,
        paid_amount=500,
        status="paid",
        notes="Compra de laptops y mouse"
    )
    db.add(entry1)
    db.flush()
    
    items1 = [
        PurchaseItem(
            purchase_entry_id=entry1.id,
            product_id=products[0].id,  # Laptop
            quantity=10,
            unit_price=650.00,
            discount=0,
            subtotal=6500.00
        ),
        PurchaseItem(
            purchase_entry_id=entry1.id,
            product_id=products[1].id,  # Mouse
            quantity=30,
            unit_price=15.00,
            discount=0,
            subtotal=450.00
        ),
    ]
    db.add_all(items1)
    entry1.total_amount = sum(item.subtotal for item in items1)
    entries.append(entry1)
    
    # Entrada 2: Ropa
    entry2 = PurchaseEntry(
        supplier_id=suppliers[1].id,
        document_number="CON-002",
        document_date=datetime.now() - timedelta(days=3),
        total_amount=0,
        paid_amount=200,
        status="partial",
        notes="Compra de camisas"
    )
    db.add(entry2)
    db.flush()
    
    items2 = [
        PurchaseItem(
            purchase_entry_id=entry2.id,
            product_id=products[2].id,  # Camisa
            quantity=20,
            unit_price=30.00,
            discount=0,
            subtotal=600.00
        ),
    ]
    db.add_all(items2)
    entry2.total_amount = sum(item.subtotal for item in items2)
    entries.append(entry2)
    
    # Entrada 3: Alimentos
    entry3 = PurchaseEntry(
        supplier_id=suppliers[2].id,
        document_number="FAC-003",
        document_date=datetime.now() - timedelta(days=2),
        total_amount=0,
        paid_amount=0,
        status="pending",
        notes="Compra de arroz"
    )
    db.add(entry3)
    db.flush()
    
    items3 = [
        PurchaseItem(
            purchase_entry_id=entry3.id,
            product_id=products[3].id,  # Arroz
            quantity=50,
            unit_price=1.00,
            discount=0,
            subtotal=50.00
        ),
    ]
    db.add_all(items3)
    entry3.total_amount = sum(item.subtotal for item in items3)
    entries.append(entry3)
    
    db.commit()
    
    # Actualizar stock en Warehouse
    for entry in entries:
        for item in entry.items:
            warehouse = db.query(WarehouseStock).filter(
                WarehouseStock.product_id == item.product_id
            ).first()
            if warehouse:
                warehouse.quantity += item.quantity
            else:
                # Si no existe, crear stock inicial
                warehouse = WarehouseStock(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    min_stock=10
                )
                db.add(warehouse)
    db.commit()
    
    return entries

def create_pos_locations(db):
    """Crear puntos de venta"""
    locations = [
        POSLocation(name="Sucursal Centro", address="Av. Libertador 1000", is_active=True),
        POSLocation(name="Sucursal Norte", address="Calle Norte 456", is_active=True),
    ]
    db.add_all(locations)
    db.commit()
    for loc in locations:
        db.refresh(loc)
    return locations

def create_pos_stock(db, products, pos_locations):
    """Inicializar stock en POS con cantidades"""
    # Asignar stock inicial a cada POS (por simplicidad, mismo stock)
    stocks = []
    for pos in pos_locations:
        for product in products:
            if product.has_inventory:
                # Stock inicial aleatorio entre 5 y 20
                qty = random.randint(5, 20)
                stock = POSStock(
                    product_id=product.id,
                    pos_location_id=pos.id,
                    quantity=qty
                )
                stocks.append(stock)
    db.add_all(stocks)
    db.commit()
    return stocks

def create_cash_registers(db, pos_locations):
    """Crear cajas registradoras para cada POS"""
    registers = []
    for pos in pos_locations:
        reg = CashRegister(
            pos_location_id=pos.id,
            current_balance=500.00  # saldo inicial
        )
        registers.append(reg)
    db.add_all(registers)
    db.commit()
    return registers

def create_sample_sales(db, pos_locations, products, users):
    """Crear ventas de ejemplo (completadas y canceladas)"""
    sales = []
    
    # Ventas completadas
    for i in range(5):
        pos = random.choice(pos_locations)
        cashier = random.choice([u for u in users if u.role == UserRole.CASHIER])
        # Seleccionar 2-3 productos aleatorios
        selected_products = random.sample([p for p in products if p.has_inventory], k=random.randint(1, 3))
        total = 0
        items_data = []
        for prod in selected_products:
            qty = random.randint(1, 3)
            subtotal = prod.price * qty
            total += subtotal
            items_data.append({
                "product_id": prod.id,
                "quantity": qty,
                "unit_price": prod.price,
                "subtotal": subtotal
            })
        
        cash_received = total + random.uniform(0, 5)
        change = cash_received - total
        
        # Crear venta
        sale = Sale(
            pos_location_id=pos.id,
            cashier_id=cashier.id,
            total_amount=total,
            cash_received=round(cash_received, 2),
            change=round(change, 2),
            status="completed",
            sale_date=datetime.now() - timedelta(days=random.randint(0, 2))
        )
        db.add(sale)
        db.flush()
        
        # Crear items de venta
        for item_data in items_data:
            item = SaleItem(
                sale_id=sale.id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                subtotal=item_data["subtotal"]
            )
            db.add(item)
            # Actualizar stock en POS
            pos_stock = db.query(POSStock).filter(
                POSStock.pos_location_id == pos.id,
                POSStock.product_id == item_data["product_id"]
            ).first()
            if pos_stock:
                pos_stock.quantity -= item_data["quantity"]
        
        sales.append(sale)
    
    # Una venta cancelada
    pos = pos_locations[0]
    cashier = [u for u in users if u.role == UserRole.CASHIER][0]
    canceller = [u for u in users if u.role == UserRole.ADMIN][0]
    
    cancel_sale = Sale(
        pos_location_id=pos.id,
        cashier_id=cashier.id,
        total_amount=100.00,
        cash_received=100.00,
        change=0,
        status="cancelled",
        cancelled_by=canceller.id,
        cancelled_at=datetime.now() - timedelta(hours=1),
        cancellation_reason="Producto equivocado",
        sale_date=datetime.now() - timedelta(days=1)
    )
    db.add(cancel_sale)
    db.flush()
    
    # Items para la venta cancelada (no afectan stock porque se revierten)
    cancel_items = [
        SaleItem(
            sale_id=cancel_sale.id,
            product_id=products[0].id,  # Laptop
            quantity=1,
            unit_price=100.00,
            subtotal=100.00
        )
    ]
    db.add_all(cancel_items)
    sales.append(cancel_sale)
    
    db.commit()
    return sales

def main():
    db = SessionLocal()
    try:
        print("🌱 Poblando base de datos con datos de prueba...")
        
        # Limpiar datos existentes
        clean_tables(db)
        
        # 1. Usuarios
        print("👤 Creando usuarios...")
        #users = create_users(db)
        
        # 2. Categorías
        print("📂 Creando categorías...")
        categories = create_categories(db)
        
        # 3. Productos
        print("📦 Creando productos...")
        products = create_products(db, categories)
        
        # 4. Proveedores
        print("🏢 Creando proveedores...")
        suppliers = create_suppliers(db)
        
        # 5. Entradas de compra y stock en warehouse
        print("📥 Creando entradas de compra y stock en warehouse...")
        create_purchase_entries(db, suppliers, products)
        
        # 6. Puntos de venta
        print("🏪 Creando puntos de venta...")
        pos_locations = create_pos_locations(db)
        
        # 7. Stock en POS
        print("📊 Inicializando stock en POS...")
        create_pos_stock(db, products, pos_locations)
        
        # 8. Cajas registradoras
        print("💰 Creando cajas registradoras...")
        create_cash_registers(db, pos_locations)
        
        # 9. Ventas de ejemplo
        print("🧾 Creando ventas de ejemplo...")
        create_sample_sales(db, pos_locations, products, users)
        
        db.commit()
        print("✅ ¡Base de datos poblada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def clean_tables(db):
    """Eliminar datos existentes en orden inverso a las dependencias"""
    # Eliminar en orden: primero las tablas hijas, luego las padres
    db.execute("DELETE FROM sale_items")
    db.execute("DELETE FROM sales")
    db.execute("DELETE FROM pos_stock")
    db.execute("DELETE FROM cash_registers")
    db.execute("DELETE FROM transfer_to_pos")
    db.execute("DELETE FROM purchase_items")
    db.execute("DELETE FROM purchase_entries")
    db.execute("DELETE FROM warehouse_stock")
    db.execute("DELETE FROM products")
    db.execute("DELETE FROM categories")
    db.execute("DELETE FROM suppliers")
    db.execute("DELETE FROM pos_locations")
    db.execute("DELETE FROM users")
    db.commit()
    print("🧹 Datos existentes eliminados")





if __name__ == "__main__":
    
    
    main()