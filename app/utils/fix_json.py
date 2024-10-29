from app.config import get_settings
import os
import json
from datetime import datetime

def fix_json_files():
    """Script para corregir los archivos JSON existentes"""
    settings = get_settings()
    processed_path = settings.PROCESSED_DATA_PATH
    
    print("Iniciando corrección de archivos JSON...")
    
    for client_dir in os.listdir(processed_path):
        client_path = os.path.join(processed_path, client_dir)
        if os.path.isdir(client_path):
            print(f"\nProcesando cliente: {client_dir}")
            
            for filename in os.listdir(client_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(client_path, filename)
                    print(f"Procesando archivo: {filename}")
                    
                    try:
                        # Leer el archivo actual
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Si el archivo ya es válido, continuar
                        try:
                            json.loads(content)
                            print(f"✓ Archivo ya está correcto")
                            continue
                        except:
                            # Intentar reparar el archivo
                            print("Intentando reparar archivo...")
                            
                            # Reemplazar la línea problemática
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if '"fecha_emision":' in line and '...' in line:
                                    # Asumimos que es un archivo del 25 de octubre
                                    date_str = filename.split('_')[2].split('.')[0]
                                    year = date_str[:4]
                                    month = date_str[4:6]
                                    day = date_str[6:8]
                                    lines[i] = f'  "fecha_emision": "{year}-{month}-{day}T00:00:00",'
                            
                            # Reconstruir el archivo
                            fixed_content = '\n'.join(lines)
                            
                            # Verificar que es un JSON válido
                            data = json.loads(fixed_content)
                            
                            # Guardar el archivo corregido
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            
                            print(f"✓ Archivo corregido exitosamente")
                    
                    except Exception as e:
                        print(f"❌ Error procesando {filename}: {str(e)}")
                        # Mostrar el contenido problemático
                        print("Contenido problemático:")
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                print(f.read())
                        except:
                            print("No se pudo leer el contenido del archivo")
                        continue

if __name__ == "__main__":
    fix_json_files()