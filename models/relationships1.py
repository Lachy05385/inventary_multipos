"""
Relaciones corregidas - Importar después de crear todos los modelos
"""
from sqlalchemy.orm import relationship

def setup_relationships():
    """Configurar todas las relaciones después de importar modelos"""
    from models.user_models import User
    from models.inventory_models import Product, WarehouseStock, POSLocation, POSStock, TransferToPOS
    from models.cash_models import Sale, SaleItem, CashRegister, CashWithdrawal, CashWithdrawalRequest
    
    # Configurar relaciones para User
    User.pos_location = relationship("POSLocation", back_populates="cashiers")
    User.sales = relationship("Sale", back_populates="cashier")
    User.cash_withdrawals = relationship("CashWithdrawal", back_populates="user")
    
    # Configurar relaciones para Product
    Product.warehouse_stock = relationship("WarehouseStock", back_populates="product", uselist=False)
    Product.pos_stocks = relationship("POSStock", back_populates="product")
    Product.sale_items = relationship("SaleItem", back_populates="product")
    
    # Configurar relaciones para WarehouseStock
    WarehouseStock.product = relationship("Product", back_populates="warehouse_stock")
    WarehouseStock.transfers_to_pos = relationship("TransferToPOS", back_populates="warehouse_stock")
    
    # Configurar relaciones para POSLocation
    POSLocation.cashiers = relationship("User", back_populates="pos_location")
    POSLocation.pos_stocks = relationship("POSStock", back_populates="pos_location")
    POSLocation.sales = relationship("Sale", back_populates="pos_location")
    POSLocation.cash_registers = relationship("CashRegister", back_populates="pos_location")
    
    # Configurar relaciones para POSStock
    POSStock.product = relationship("Product", back_populates="pos_stocks")
    POSStock.pos_location = relationship("POSLocation", back_populates="pos_stocks")
    
    # Configurar relaciones para TransferToPOS
    TransferToPOS.warehouse_stock = relationship("WarehouseStock", back_populates="transfers_to_pos")
    TransferToPOS.pos_location = relationship("POSLocation")
    TransferToPOS.product = relationship("Product")
    
    # Configurar relaciones para Sale
    Sale.pos_location = relationship("POSLocation", back_populates="sales")
    Sale.cashier = relationship("User", back_populates="sales")
    Sale.sale_items = relationship("SaleItem", back_populates="sale")
    
    # Configurar relaciones para SaleItem
    SaleItem.sale = relationship("Sale", back_populates="sale_items")
    SaleItem.product = relationship("Product", back_populates="sale_items")
    
    # Configurar relaciones para CashRegister
    CashRegister.pos_location = relationship("POSLocation", back_populates="cash_registers")
    CashRegister.withdrawals = relationship("CashWithdrawal", back_populates="cash_register")
    
    # Configurar relaciones para CashWithdrawal
    CashWithdrawal.cash_register = relationship("CashRegister", back_populates="withdrawals")
    CashWithdrawal.user = relationship("User", back_populates="cash_withdrawals")
    
    # Configurar relaciones para CashWithdrawalRequest
    CashWithdrawalRequest.pos_location = relationship("POSLocation")
    CashWithdrawalRequest.cashier = relationship("User", foreign_keys=[CashWithdrawalRequest.cashier_id])
    CashWithdrawalRequest.authorizer = relationship("User", foreign_keys=[CashWithdrawalRequest.authorizer_id])