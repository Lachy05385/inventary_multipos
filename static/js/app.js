// js/app.js
function initApp() {
  const app = document.getElementById('app');
  
  if (!isAuthenticated()) {
    renderLogin();
    return;
  }

  // Si está autenticado, mostrar dashboard con sidebar
  renderDashboard();
}

function renderLogin() {
  document.getElementById('app').innerHTML = `
    <div class="login-container">
      <h2>Iniciar Sesión</h2>
      <form id="login-form">
        <input type="text" id="username" placeholder="Usuario" required>
        <input type="password" id="password" placeholder="Contraseña" required>
        <button type="submit">Entrar</button>
        <div id="login-error" class="error"></div>
      </form>
    </div>
  `;
  document.getElementById('login-form').addEventListener('submit', handleLogin);
}

function renderDashboard() {
  // Aquí construimos la estructura con sidebar y contenido
  document.getElementById('app').innerHTML = `
    <div class="sidebar">
      <h2>📦 Sistema</h2>
      <ul>
        <li data-view="dashboard" class="active">Dashboard</li>
        <li data-view="categories">Categorías</li>
        <li data-view="products">Productos</li>
        <li data-view="suppliers">Proveedores</li>
        <li data-view="pos">Punto de Venta</li>
        <li data-view="cash">Caja</li>
        <li data-view="logout" style="color: #e74c3c;">Cerrar Sesión</li>
      </ul>
    </div>
    <div class="main">
      <div id="view-container">
        <!-- Las vistas se cargarán aquí -->
      </div>
    </div>
  `;

  // Eventos de navegación
  document.querySelectorAll('.sidebar ul li').forEach(item => {
    item.addEventListener('click', (e) => {
      const view = item.dataset.view;
      if (view === 'logout') {
        logout();
        return;
      }
      // Marcar activo
      document.querySelectorAll('.sidebar ul li').forEach(li => li.classList.remove('active'));
      item.classList.add('active');
      navigateTo(view);
    });
  });

  // Cargar vista inicial (dashboard)
  navigateTo('dashboard');
}

function navigateTo(view) {
  const container = document.getElementById('view-container');
  // Aquí cargamos dinámicamente el contenido de cada vista
  // Por ahora, solo un placeholder
  container.innerHTML = `<h1>Vista: ${view}</h1><p>Contenido en construcción...</p>`;
}

// Iniciar la aplicación
document.addEventListener('DOMContentLoaded', initApp);