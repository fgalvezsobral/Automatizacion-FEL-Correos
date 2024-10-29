# fix_json_v2.py
from app.config import get_settings
import os
import json
from datetime import datetime

def fix_broken_json():
    """Script para reconstruir archivos JSON incompletos"""
    settings = get_settings()
    processed_path = settings.PROCESSED_DATA_PATH
    
    print("Iniciando reconstrucción de archivos JSON...")
    
    template = {
        "numero_autorizacion": "",
        "serie": "",
        "numero": "",
        "fecha_emision": "",
        "tipo_documento": "FACT",
        "emisor": {
            "nit": "",
            "nombre": "",
            "direccion": ""
        },
        "receptor": {
            "nit": "1720495K",
            "nombre": "FERNANDO GALVEZ",
            "direccion": ""
        },
        "items": [],
        "total": "0",
        "iva": "0",
        "moneda": "GTQ"
    }
    
    for client_dir in os.listdir(processed_path):
        client_path = os.path.join(processed_path, client_dir)
        if os.path.isdir(client_path):
            print(f"\nProcesando cliente: {client_dir}")
            
            for filename in os.listdir(client_path):
                if not filename.endswith('.json'):
                    continue
                    
                file_path = os.path.join(client_path, filename)
                print(f"Procesando archivo: {filename}")
                
                try:
                    # Intentar leer como JSON válido primero
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                        print(f"✓ Archivo ya está correcto")
                        continue
                except:
                    print("Archivo dañado, intentando reconstruir...")
                    
                    try:
                        # Leer el contenido actual
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Extraer la información disponible
                        lines = content.split('\n')
                        new_json = template.copy()
                        
                        for line in lines:
                            line = line.strip()
                            if '"numero_autorizacion":' in line:
                                new_json["numero_autorizacion"] = line.split('"')[3]
                            elif '"serie":' in line:
                                new_json["serie"] = line.split('"')[3]
                            elif '"numero":' in line:
                                new_json["numero"] = line.split('"')[3]
                        
                        # Agregar la fecha basada en el nombre del archivo
                        date_str = filename.split('_')[2].split('.')[0]
                        year = date_str[:4]
                        month = date_str[4:6]
                        day = date_str[6:8]
                        new_json["fecha_emision"] = f"{year}-{month}-{day}T00:00:00"
                        
                        # Guardar el archivo reconstruido
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(new_json, f, ensure_ascii=False, indent=2)
                        
                        print(f"✓ Archivo reconstruido exitosamente")
                        
                    except Exception as e:
                        print(f"❌ Error reconstruyendo {filename}: {str(e)}")

if __name__ == "__main__":
    fix_broken_json()