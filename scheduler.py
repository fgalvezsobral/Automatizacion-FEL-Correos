import schedule
import time
from datetime import datetime
import logging
import os
import uvicorn
import requests
from app.core.notifications import NotificationManager

# Obtener el directorio del proyecto
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configurar logging
logging.basicConfig(
    filename=os.path.join(PROJECT_DIR, 'scheduler.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

notification_manager = NotificationManager()

def ejecutar_proceso():
    try:
        logging.info(f"Iniciando proceso de facturación en {datetime.now()}")
        
        # Hacer una petición POST al endpoint
        response = requests.post('http://localhost:8000/process')
        
        if response.status_code == 200:
            resultado = response.json()
            logging.info(f"Proceso completado exitosamente: {resultado}")
        else:
            error_msg = f"Error en el proceso: {response.text}"
            logging.error(error_msg)
            notification_manager.send_error_alert(
                error_message=error_msg,
                context={
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
    except Exception as e:
        error_msg = f"Error ejecutando el proceso: {str(e)}"
        logging.error(error_msg)
        notification_manager.send_error_alert(
            error_message=error_msg,
            context={"timestamp": datetime.now().isoformat()}
        )

def enviar_reporte_diario():
    """Función para enviar el reporte diario"""
    try:
        logging.info("Generando y enviando reporte diario")
        notification_manager.send_daily_report(to_email=os.getenv('ALERT_EMAIL'))
        logging.info("Reporte diario enviado exitosamente")
    except Exception as e:
        error_msg = f"Error enviando reporte diario: {str(e)}"
        logging.error(error_msg)
        notification_manager.send_error_alert(error_message=error_msg)

def main():
    # Programar las ejecuciones del proceso principal
    schedule.every().day.at("08:00").do(ejecutar_proceso)
    schedule.every().day.at("11:00").do(ejecutar_proceso)
    schedule.every().day.at("14:00").do(ejecutar_proceso)
    schedule.every().day.at("16:00").do(ejecutar_proceso)
    schedule.every().day.at("21:00").do(ejecutar_proceso)
    
    # Programar el envío del reporte diario (por ejemplo, a las 23:00)
    schedule.every().day.at("23:00").do(enviar_reporte_diario)
    
    logging.info("Programador iniciado. Horarios configurados.")
    print("Programador iniciado. Presiona Ctrl+C para detener.")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    try:
        # Iniciar el servidor FastAPI en segundo plano
        import threading
        def run_server():
            uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_level="info")
        
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Esperar un momento para que el servidor inicie
        time.sleep(5)
        
        # Iniciar el scheduler
        main()
    except KeyboardInterrupt:
        logging.info("Programador detenido por el usuario")
        print("\nProgramador detenido por el usuario")
    except Exception as e:
        logging.error(f"Error en el programador: {str(e)}")