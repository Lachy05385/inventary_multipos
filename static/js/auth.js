// static/js/auth.js

// ----- LOGIN -----
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const errorEl = document.getElementById('loginError');

    try {
        const data = await login(username, password);
        localStorage.setItem('access_token', data.access_token);
        // Redirigir al dashboard (o recargar)
        window.location.href = '/dashboard';  // Asumiendo que tenemos un dashboard después
    } catch (error) {
        errorEl.textContent = error.message;
    }
});

// ----- REGISTRO -----
document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    const errorEl = document.getElementById('registerError');

    try {
        // Simulación: deberías tener un endpoint /auth/register
        const response = await apiRequest('/auth/register', 'POST', {
            username,
            email,
            password
        });
        alert('Registro exitoso. Ahora puedes iniciar sesión.');
        bootstrap.Modal.getInstance(document.getElementById('registerModal')).hide();
    } catch (error) {
        errorEl.textContent = error.message;
    }
});

// Función de login (usando api.js)
async function login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await fetch('/auth/token', {
        method: 'POST',
        body: formData
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Error de autenticación');
    }
    return response.json();
}