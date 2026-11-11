from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["pages"])


# ========== PÁGINAS GENERALES ==========
@router.get("/index", include_in_schema=False)
async def landing():
    return FileResponse("templates/index.html")


@router.get("/login", include_in_schema=False)
async def login_page():
    return FileResponse("templates/login.html")


@router.get("/panel", include_in_schema=False)
async def panel_page():
    return FileResponse("templates/panel.html")


@router.get("/usuarios", include_in_schema=False)
async def usuarios_page():
    return FileResponse("templates/usuarios.html")


@router.get("/portafolio", include_in_schema=False)
async def portafolio_page():
    return FileResponse("templates/portafolio.html")


# ========== INVENTARIO (sin Depends) ==========
@router.get("/inventario", include_in_schema=False)
def page_productos():
    return FileResponse("templates/inventario/productos.html")


@router.get("/inventario/nuevo", include_in_schema=False)
def page_producto_nuevo():
    return FileResponse("templates/inventario/producto_form.html")


@router.get("/inventario/entradas", include_in_schema=False)
def page_entradas():
    return FileResponse("templates/inventario/entradas.html")






@router.get("/inventario/entradas/nueva", include_in_schema=False)
def page_entrada_nueva():
    return FileResponse("templates/inventario/entrada_form.html")


@router.get("/inventario/stock", include_in_schema=False)
def page_stock():
    return FileResponse("templates/inventario/stock.html")


@router.get("/transferencias", include_in_schema=False)
def page_transferencias():
    return FileResponse("templates/inventario/transferencias.html")


# ========== INVENTARIO (ruta dinámica al final) ==========
@router.get("/inventario/{producto_id}/editar", include_in_schema=False)
def page_producto_editar(producto_id: int):
    return FileResponse("templates/inventario/producto_form.html")


# ========== PROVEEDORES ==========
@router.get("/proveedores", include_in_schema=False)
def page_proveedores():
    return FileResponse("templates/proveedores/lista.html")


@router.get("/proveedores/nuevo", include_in_schema=False)
def page_proveedor_nuevo():
    return FileResponse("templates/proveedores/form.html")


@router.get("/proveedores/{proveedor_id}/editar", include_in_schema=False)
def page_proveedor_editar(proveedor_id: int):
    return FileResponse("templates/proveedores/form.html")


#POS
# ========== POS LOCATIONS ==========
@router.get("/locations", include_in_schema=False)
def page_pos_locations():
    return FileResponse("templates/pos/locations.html")