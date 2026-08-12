// static/js/api.js

const API_BASE = ''; // Relativo

async function apiRequest(endpoint, method = 'GET', body = null, isFormData = false) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
    };
    
    let options = { method, headers };
    
    if (body) {
        if (isFormData) {
            options.body = body;
        } else {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
    }
    
    const response = await fetch(url, options);
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error ${response.status}`);
    }
    return response.json();
}