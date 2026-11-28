// ========== CONFIGURACIÓN GLOBAL ==========
const BASE_URL = window.location.origin;


const Sidebar = {
    // Items de navegación por rol
    items: {
        ADMIN: [
            { section: 'Principal', links: [
                { href: '/panel', icon: '🏠', label: 'Panel' },
                { href: '/inventario', icon: '📦', label: 'Productos' },
                { href: '/inventario/stock', icon: '📊', label: 'Stock Almacén' },
                { href: '/inventario/stock/consolidado', icon: '📈', label: 'Stock Consolidado' },
            ]},
            { section: 'Compras', links: [
                { href: '/inventario/entradas', icon: '📥', label: 'Entradas' },
                { href: '/proveedores', icon: '🏢', label: 'Proveedores' },
            ]},
            { section: 'Puntos de Venta', links: [
                { href: '/pos/locations', icon: '🏪', label: 'Gestionar POS' },
                { href: '/transferencias', icon: '🔄', label: 'Transferencias' },
                { href: '/cash/registers', icon: '💰', label: 'Cajas' },
                { href: '/cash/withdrawal-requests', icon: '💸', label: 'Retiros' },
            ]},
        ],
        WAREHOUSE_MANAGER: [
            { section: 'Almacén', links: [
                { href: '/panel', icon: '🏠', label: 'Panel' },
                { href: '/inventario', icon: '📦', label: 'Productos' },
                { href: '/inventario/stock', icon: '📊', label: 'Stock' },
                { href: '/inventario/entradas', icon: '📥', label: 'Entradas' },
                { href: '/proveedores', icon: '🏢', label: 'Proveedores' },
            ]},
            { section: 'Transferencias', links: [
                { href: '/transferencias', icon: '🔄', label: 'Transferencias' },
            ]},
            { section: 'Cajas', links: [
                { href: '/cash/registers', icon: '💰', label: 'Cajas' },
                { href: '/cash/withdrawal-requests', icon: '💸', label: 'Retiros' },
            ]},
        ],
        CASHIER: [
            { section: 'Mi Punto de Venta', links: [
                { href: '/pos/caja', icon: '💰', label: 'Caja' },
                { href: '/pos/historial', icon: '📋', label: 'Historial de Ventas' },
                { href: '/pos/transferencias', icon: '🔄', label: 'Transferencias pos' },   // <-- NUEVO
                { href: '/cash/withdrawal-requests', icon: '💸', label: 'Mis Retiros' },
            ]},
            /*{ section: 'Transferencias', links: [
                { href: '/pos/transferencias', icon: '🔄', label: 'Transferencias' },
            ]},*/
        ],
    },

    render(container, user) {
        const rol = (user.role || '').toUpperCase();
        const items = this.items[rol] || this.items.CASHIER;
        const currentPath = window.location.pathname;

        const navHTML = items.map(section => `
            <div class="nav-section">
                <div class="nav-section-title">${section.section}</div>
                ${section.links.map(link => {
                    const isActive = currentPath === link.href || currentPath.startsWith(link.href + '/');
                    return `
                        <a href="${link.href}" class="nav-item ${isActive ? 'active' : ''}">
                            <span class="icon">${link.icon}</span>
                            <span>${link.label}</span>
                        </a>
                    `;
                }).join('')}
            </div>
        `).join('');

        const rolLabel = { ADMIN: 'Admin', WAREHOUSE_MANAGER: 'Almacén', CASHIER: 'Cajero' }[rol] || rol;

        container.innerHTML = `
            <aside class="sidebar" id="sidebar">
                <div class="sidebar-brand">
                    <span class="logo-icon">🛒</span>
                    <span>MiPOS</span>
                </div>
                <nav class="sidebar-nav">${navHTML}</nav>
                <div class="sidebar-footer">
                    ${rolLabel} • v1.0
                </div>
            </aside>
        `;
    },

    renderTopbar(container, user, title, subtitle) {
        const rol = (user.role || '').toUpperCase();
        const roleClass = { ADMIN: 'admin', WAREHOUSE_MANAGER: 'warehouse', CASHIER: 'cashier' }[rol] || '';
        const roleLabel = { ADMIN: 'Admin', WAREHOUSE_MANAGER: 'Almacén', CASHIER: 'Cajero' }[rol] || rol;
        const inicial = (user.full_name || '?').charAt(0).toUpperCase();

        container.innerHTML = `
            <div class="topbar-left">
                <div>
                    <div class="page-title">${title}</div>
                    ${subtitle ? `<div class="page-subtitle">${subtitle}</div>` : ''}
                </div>
            </div>
            <div class="topbar-right">
                <div class="user-chip">
                    <div class="user-avatar">${inicial}</div>
                    <span>${user.full_name}</span>
                    <span class="role-badge ${roleClass}">${roleLabel}</span>
                </div>
                <button class="logout-btn" onclick="logout()">Salir</button>
            </div>
        `;
    },
};

// ========== AUTENTICACIÓN ==========
function getToken() {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');
    if (urlToken) { localStorage.setItem('token', urlToken); return urlToken; }
    return localStorage.getItem('token');
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

async function apiFetch(url, options = {}) {
    const headers = options.headers || {};
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) { logout(); throw new Error('Sesión expirada'); }
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        let msg = `Error ${res.status}`;
        if (typeof err.detail === 'string') msg = err.detail;
        else if (Array.isArray(err.detail)) msg = err.detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join(' | ');
        throw new Error(msg);
    }
    return res.json();
}

// ========== TOAST ==========
function showToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideIn .3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ========== INICIALIZACIÓN ==========
async function initLayout(pageTitle, pageSubtitle) {
    const token = getToken();
    if (!token) { window.location.href = '/login'; return null; }

    try {
        const user = await apiFetch('/users/me');
        
        const sidebarContainer = document.getElementById('sidebar-container');
        const topbarContainer = document.getElementById('topbar-container');

        if (sidebarContainer) Sidebar.render(sidebarContainer, user);
        if (topbarContainer) Sidebar.renderTopbar(topbarContainer, user, pageTitle, pageSubtitle);

        return user;

    } catch (e) {
        logout();
        return null;
    }
}

//export { initLayout };