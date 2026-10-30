import requests
from bs4 import BeautifulSoup
import pandas as pd

def obtener_tasas_eltoque():
    # URL de la página (VERIFICA LA URL ACTUAL)
    url = "https://eltoque.com/es"  # URL de ejemplo
    
    # Headers para simular navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # 1. Obtener HTML
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Verificar errores
        
        # 2. Parsear HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. Encontrar los datos (ESTOS SELECTORES SON EJEMPLOS)
        # Debes inspeccionar la página real para ajustarlos
        
        # Ejemplo: buscar tablas
        tablas = soup.find_all('table')
        
        tasas = []
        
        # 4. Extraer datos (adaptar según estructura real)
        for tabla in tablas:
            filas = tabla.find_all('tr')
            for fila in filas[1:]:  # Saltar encabezado
                celdas = fila.find_all('td')
                if len(celdas) >= 3:
                    tasa = {
                        'moneda': celdas[0].text.strip(),
                        'compra': celdas[1].text.strip(),
                        'venta': celdas[2].text.strip(),
                        'fecha': 'fecha_extraída'  # Extraer de algún lugar
                    }
                    tasas.append(tasa)
        
        # 5. Convertir a DataFrame
        df = pd.DataFrame(tasas)
        return df
        
    except Exception as e:
        print(f"Error: {e}")
        return None

# Ejecutar
if __name__ == "__main__":
    tasas = obtener_tasas_eltoque()
    if tasas is not None:
        print(tasas.to_string())
        # Guardar en CSV
        tasas.to_csv('tasas_eltoque.csv', index=False)