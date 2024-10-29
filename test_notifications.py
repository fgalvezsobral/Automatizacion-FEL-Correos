from app.core.notifications import NotificationManager
from datetime import datetime
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)

def test_notifications():
    try:
        print("Iniciando pruebas de notificaciones...")
        notification_manager = NotificationManager()
        
        print("\n1. Probando alerta de error...")
        notification_manager.send_error_alert(
            "Este es un error de prueba - Ignorar",
            {"timestamp": datetime.now().isoformat()}
        )
        print("✓ Alerta de error enviada")
        
        print("\n2. Probando reporte diario...")
        notification_manager.send_daily_report(
            to_email=notification_manager.settings.ALERT_EMAIL
        )
        print("✓ Reporte diario enviado")
        
        print("\n✓ Pruebas completadas exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {str(e)}")
        raise

if __name__ == "__main__":
    test_notifications()