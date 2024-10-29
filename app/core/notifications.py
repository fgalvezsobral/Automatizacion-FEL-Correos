import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging
from typing import Dict, List
import os
import json
from ..config import get_settings

class NotificationManager:
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)

    def send_email(self, subject: str, body: str, to_email: str) -> bool:
        """Envía un email usando las configuraciones de Zoho"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.settings.NOTIFICATION_EMAIL
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'html'))

            with smtplib.SMTP(self.settings.SMTP_SERVER, self.settings.SMTP_PORT) as server:
                if self.settings.SMTP_USE_TLS:
                    server.starttls()
                server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                server.send_message(msg)
                self.logger.info(f"Email enviado exitosamente a {to_email}")

            return True
        except Exception as e:
            self.logger.error(f"Error enviando email: {str(e)}")
            return False

    def generate_daily_report(self) -> Dict:
        """Genera el reporte diario de facturas procesadas"""
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # Estadísticas por cliente
            client_stats = {}
            total_amount = 0
            
            # Recorrer directorios de clientes
            processed_path = self.settings.PROCESSED_DATA_PATH
            self.logger.info(f"Revisando directorio: {processed_path}")
            
            if not os.path.exists(processed_path):
                self.logger.warning(f"El directorio {processed_path} no existe")
                return {
                    'fecha': yesterday.strftime('%Y-%m-%d'),
                    'estadisticas_clientes': {},
                    'total_general': 0
                }

            for client_dir in os.listdir(processed_path):
                client_path = os.path.join(processed_path, client_dir)
                if os.path.isdir(client_path):
                    self.logger.info(f"Procesando cliente: {client_dir}")
                    client_invoices = 0
                    client_total = 0
                    
                    # Revisar facturas del cliente
                    for filename in os.listdir(client_path):
                        if filename.endswith('.json'):
                            file_path = os.path.join(client_path, filename)
                            self.logger.info(f"Leyendo archivo: {file_path}")
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    try:
                                        factura = json.loads(content)
                                        fecha_factura = datetime.fromisoformat(factura['fecha_emision']).date()
                                        
                                        if fecha_factura == yesterday:
                                            client_invoices += 1
                                            client_total += float(factura['total'])
                                    except json.JSONDecodeError as je:
                                        self.logger.error(f"Error en JSON {file_path}: {str(je)}")
                                        self.logger.error(f"Contenido problemático: {content[:200]}...")
                                        continue
                                    except KeyError as ke:
                                        self.logger.error(f"Falta campo requerido en {file_path}: {str(ke)}")
                                        continue
                            except Exception as e:
                                self.logger.error(f"Error leyendo archivo {file_path}: {str(e)}")
                                continue
                    
                    if client_invoices > 0:
                        client_stats[client_dir] = {
                            'facturas_procesadas': client_invoices,
                            'total_facturado': client_total,
                            'nombre_cliente': self._get_client_name(client_dir)
                        }
                        total_amount += client_total

            self.logger.info(f"Reporte generado: {len(client_stats)} clientes encontrados")
            return {
                'fecha': yesterday.strftime('%Y-%m-%d'),
                'estadisticas_clientes': client_stats,
                'total_general': total_amount
            }
        except Exception as e:
            self.logger.error(f"Error generando reporte diario: {str(e)}")
            raise

    def send_daily_report(self, to_email: str) -> None:
        """Envía el reporte diario por email"""
        try:
            report = self.generate_daily_report()
            
            if not report['estadisticas_clientes']:
                html_content = f"""
                <h2 style="color: #2C3E50;">Reporte Diario de Facturas Procesadas</h2>
                <p>Fecha: {report['fecha']}</p>
                <p style="color: #666;">No se encontraron facturas procesadas para la fecha indicada.</p>
                <hr style="border: 1px solid #eee;">
                <p style="color: #666; font-style: italic;">Este es un mensaje automático del sistema de procesamiento de facturas.</p>
                """
            else:
                html_content = f"""
                <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                    <h2 style="color: #2C3E50; margin-bottom: 20px;">Reporte Diario de Facturas Procesadas</h2>
                    <p style="font-size: 16px;"><strong>Fecha:</strong> {report['fecha']}</p>
                    
                    <h3 style="color: #2C3E50; margin-top: 30px;">Resumen por Cliente:</h3>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                        <thead>
                            <tr style="background-color: #34495E; color: white;">
                                <th style="padding: 12px 15px; text-align: left;">Cliente</th>
                                <th style="padding: 12px 15px; text-align: center;">Facturas Procesadas</th>
                                <th style="padding: 12px 15px; text-align: right;">Total Facturado (GTQ)</th>
                            </tr>
                        </thead>
                        <tbody>
                """

                # Para cada cliente
                for nit, stats in report['estadisticas_clientes'].items():
                    html_content += f"""
                            <tr>
                                <td style="padding: 12px 15px; border-bottom: 1px solid #ddd;">
                                    {stats['nombre_cliente']}<br>
                                    <span style="color: #666; font-size: 0.9em;">NIT: {nit}</span>
                                </td>
                                <td style="padding: 12px 15px; text-align: center; border-bottom: 1px solid #ddd;">
                                    {stats['facturas_procesadas']}
                                </td>
                                <td style="padding: 12px 15px; text-align: right; border-bottom: 1px solid #ddd;">
                                    {stats['total_facturado']:,.2f}
                                </td>
                            </tr>
                    """

                html_content += f"""
                        </tbody>
                        <tfoot>
                            <tr style="background-color: #f8f9fa; font-weight: bold;">
                                <td colspan="2" style="padding: 12px 15px; text-align: right;">Total General:</td>
                                <td style="padding: 12px 15px; text-align: right;">GTQ {report['total_general']:,.2f}</td>
                            </tr>
                        </tfoot>
                    </table>
                    
                    <p style="color: #666; font-style: italic; margin-top: 30px; text-align: center;">
                        Este es un mensaje automático del sistema de procesamiento de facturas.
                    </p>
                </div>
                """
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.send_email(
                subject=f"Reporte Diario de Facturas - {report['fecha']} ({timestamp})",
                body=html_content,
                to_email=to_email
            )
            self.logger.info(f"Reporte diario enviado exitosamente a {to_email}")
            
        except Exception as e:
            error_msg = f"Error enviando reporte diario: {str(e)}"
            self.logger.error(error_msg)
            self.send_error_alert(error_message=error_msg)
            raise

    def send_error_alert(self, error_message: str, context: Dict = None) -> None:
        """Envía una alerta por email cuando ocurre un error"""
        try:
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                <div style="background-color: #FFE8E8; border-left: 5px solid #FF0000; padding: 20px; margin-bottom: 25px;">
                    <h2 style="color: #CC0000; margin: 0;">⚠️ Alerta de Error en Procesamiento de Facturas</h2>
                </div>

                <div style="padding: 20px; border: 1px solid #EEE; border-radius: 5px;">
                    <p style="font-size: 16px;"><strong>Fecha y Hora:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    
                    <div style="background-color: #F9F9F9; padding: 15px; border-left: 5px solid #CC0000; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Error:</strong> {error_message}</p>
                    </div>
            """

            if context:
                html_content += """
                    <div style="margin-top: 25px;">
                        <h3 style="color: #333; border-bottom: 2px solid #EEE; padding-bottom: 10px;">Contexto adicional:</h3>
                        <dl style="margin: 15px 0;">
                """
                for key, value in context.items():
                    html_content += f"""
                            <dt style="font-weight: bold; color: #444; margin-top: 10px;">{key}:</dt>
                            <dd style="margin-left: 20px; color: #666;">{value}</dd>
                    """
                html_content += """
                        </dl>
                    </div>
                """

            html_content += """
                    <p style="color: #666; font-style: italic; margin-top: 30px; text-align: center; border-top: 1px solid #EEE; padding-top: 20px;">
                        Este es un mensaje automático del sistema de procesamiento de facturas.
                    </p>
                </div>
            </div>
            """
            
            self.send_email(
                subject="🚨 Alerta de Error - Procesamiento de Facturas",
                body=html_content,
                to_email=self.settings.ALERT_EMAIL
            )
            
        except Exception as e:
            self.logger.error(f"Error enviando alerta: {str(e)}")
            raise

    def _get_client_name(self, nit: str) -> str:
        """Obtiene el nombre del cliente basado en su NIT"""
        try:
            # Buscar en cualquier archivo JSON del cliente para obtener su nombre
            client_path = os.path.join(self.settings.PROCESSED_DATA_PATH, nit)
            if os.path.exists(client_path):
                for filename in os.listdir(client_path):
                    if filename.endswith('.json'):
                        with open(os.path.join(client_path, filename), 'r') as f:
                            data = json.load(f)
                            return data['receptor']['nombre']
            return nit  # Si no se encuentra el nombre, devolver el NIT
        except Exception as e:
            self.logger.error(f"Error obteniendo nombre del cliente: {str(e)}")
            return nit