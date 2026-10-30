import requests
from bs4 import BeautifulSoup
import time
import random

# Usa una lista de User-Agents reales y ve rotándolos
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
]

headers = {
    'User-Agent': random.choice(user_agents),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
    'Referer': 'https://eltoque.com/', # Simula que vienes de la propia web
    'DNT': '1', # Do Not Track
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

url = "https://eltoque.com/tasas-de-cambio" # Verifica que esta sea la URL correcta actual

try:
    response = requests.get(url, headers=headers, timeout=15) # Añade siempre un timeout
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    print("Conexión exitosa con headers de navegador.")
    # ... tu lógica de parseo aquí ...
except requests.exceptions.RequestException as e:
    print(f"Error con headers de navegador: {e}")