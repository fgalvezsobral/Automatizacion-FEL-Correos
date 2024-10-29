from imapclient import IMAPClient
import email
from email.header import decode_header
from datetime import datetime
import re
import os
from typing import Optional, Tuple, List
import requests
from ..config import get_settings
from ..models.schemas import Factura

class EmailProcessor:
    def __init__(self):
        self.settings = get_settings()
        self.client = None

    def connect(self) -> None:
        """Establece conexión con el servidor IMAP de Zoho"""
        try:
            self.client = IMAPClient(self.settings.ZOHO_IMAP_SERVER, port=self.settings.ZOHO_IMAP_PORT, use_uid=True)
            self.client.login(self.settings.ZOHO_EMAIL, self.settings.ZOHO_PASSWORD)
            self.client.select_folder(self.settings.ZOHO_FOLDER)
        except Exception as e:
            raise ConnectionError(f"Error al conectar con Zoho Mail: {str(e)}")

    def disconnect(self) -> None:
        """Cierra la conexión con el servidor IMAP"""
        if self.client:
            try:
                self.client.logout()
            except:
                pass

    def get_unread_messages(self) -> List[dict]:
        """Obtiene todos los mensajes no leídos de la carpeta configurada"""
        messages = []
        try:
            print(f"Buscando en carpeta: {self.settings.ZOHO_FOLDER}")
            
            # Obtener flags de algunos mensajes recientes
            recent_messages = self.client.search(['ALL'])[-5:]  # últimos 5 mensajes
            for uid in recent_messages:
                flags = self.client.get_flags([uid])
                print(f"Mensaje {uid} - Flags: {flags}")
            
            # Buscar mensajes no leídos
            messages_uids = self.client.search(['UNSEEN'])
            print(f"UIDs encontrados sin leer: {messages_uids}")
            
            # Listar todos los mensajes
            all_messages = self.client.search(['ALL'])
            print(f"Total de mensajes en la carpeta: {len(all_messages)}")
            
            for uid in messages_uids:
                email_data = self.client.fetch([uid], ['BODY[]', 'FLAGS'])
                email_body = email_data[uid][b'BODY[]']
                email_message = email.message_from_bytes(email_body)
                
                processed_email = self._process_email(email_message)
                if processed_email:
                    processed_email['uid'] = uid
                    messages.append(processed_email)
                    
        except Exception as e:
            print(f"Error detallado: {str(e)}")
            raise Exception(f"Error al obtener mensajes: {str(e)}")
            
        return messages

    def _extract_client_info(self, body: str) -> Optional[Tuple[str, str]]:
        """Extrae el NIT y nombre del cliente del cuerpo del correo"""
        try:
            # Patrones actualizados según el formato real del correo SAT
            nit_pattern = r'NIT:\s*(\w+)'
            name_pattern = r'Estimado \(a\) Contribuyente:\s*([^\n]+)'
            
            nit_match = re.search(nit_pattern, body)
            name_match = re.search(name_pattern, body)
            
            if nit_match and name_match:
                return nit_match.group(1), name_match.group(1).strip()
            return None
        except Exception as e:
            print(f"Error extrayendo información del cliente: {str(e)}")
            return None

    def _extract_invoice_info(self, body: str) -> Optional[dict]:
        """Extrae la información de la factura del cuerpo del correo"""
        try:
            patterns = {
                'numero_autorizacion': r'Número Autorización\s*</td><td[^>]*>([^<]+)',
                'serie': r'Serie\s*</td><td[^>]*>([^<]+)',
                'numero': r'Número\s*</td><td[^>]*>([^<]+)',
                'emisor': r'Emisor\s*</td><td[^>]*>([^<]+)',
                'establecimiento': r'Establecimiento\s*</td><td[^>]*>([^<]+)',
                'fecha_emision': r'Fecha de emisión\s*</td><td[^>]*>([^<]+)',
                'monto': r'Monto\s*</td><td[^>]*>GTQ - ([^<]+)'
            }
            
            invoice_info = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, body)
                if match:
                    invoice_info[key] = match.group(1).strip()
                
            if invoice_info:
                # Procesar el emisor para separar NIT y nombre
                if 'emisor' in invoice_info:
                    emisor_parts = invoice_info['emisor'].split('-', 1)
                    invoice_info['emisor_nit'] = emisor_parts[0].strip()
                    invoice_info['emisor_nombre'] = emisor_parts[1].strip() if len(emisor_parts) > 1 else ''
                
                return invoice_info
            return None
        except Exception as e:
            print(f"Error extrayendo información de la factura: {str(e)}")
            return None

    def _extract_xml_url(self, body: str) -> Optional[str]:
        """Extrae la URL del XML del cuerpo del correo"""
        try:
            # Buscamos primero el texto que precede al link
            xml_pattern = r'href=[\'"]([^\'"]+descargaXml/[^\'"]+)[\'"]'
            match = re.search(xml_pattern, body)
            if match:
                return match.group(1)
            
            # Log para depuración
            print("Contenido relevante del correo:")
            xml_section = body[body.find("XML"):body.find("XML")+200]
            print(xml_section)
            
            return None
        except Exception as e:
            print(f"Error extrayendo URL del XML: {str(e)}")
            return None

    def _process_email(self, email_message: email.message.Message) -> Optional[dict]:
        """Procesa un mensaje de correo individual"""
        try:
            body = self._get_email_body(email_message)
            print("Procesando correo con asunto:", email_message.get('subject', 'Sin asunto'))
            
            # Imprimir primeras líneas del cuerpo para debug
            print("Primeras líneas del correo:")
            print(body[:200])
            
            # Extraer toda la información necesaria
            client_info = self._extract_client_info(body)
            print("Info del cliente:", client_info)
            
            invoice_info = self._extract_invoice_info(body)
            print("Info de la factura:", invoice_info)
            
            xml_url = self._extract_xml_url(body)
            print("URL del XML:", xml_url)
            
            if client_info and invoice_info and xml_url:
                return {
                    'client': {
                        'nit': client_info[0],
                        'nombre': client_info[1]
                    },
                    'invoice': invoice_info,
                    'xml_url': xml_url
                }
            else:
                print("Falta información requerida:")
                print(f"- Cliente: {'SI' if client_info else 'NO'}")
                print(f"- Factura: {'SI' if invoice_info else 'NO'}")
                print(f"- XML URL: {'SI' if xml_url else 'NO'}")
            
        except Exception as e:
            print(f"Error procesando email: {str(e)}")
        return None

    def _get_email_body(self, email_message: email.message.Message) -> str:
        """Extrae el cuerpo del mensaje"""
        try:
            if email_message.is_multipart():
                print("Mensaje multipart")
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    print(f"Encontrada parte con content type: {content_type}")
                    if content_type == "text/plain" or content_type == "text/html":
                        try:
                            return part.get_payload(decode=True).decode()
                        except Exception as e:
                            print(f"Error decodificando parte: {str(e)}")
                return ""
            else:
                print("Mensaje no multipart")
                return email_message.get_payload(decode=True).decode()
        except Exception as e:
            print(f"Error obteniendo cuerpo del email: {str(e)}")
            return ""

    def download_xml(self, url: str, client_nit: str) -> Optional[str]:
        """Descarga el archivo XML y lo guarda en el directorio correspondiente"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Crear directorio para el cliente si no existe
            client_dir = os.path.join(self.settings.XML_STORAGE_PATH, client_nit)
            os.makedirs(client_dir, exist_ok=True)
            
            # Generar nombre de archivo único
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"factura_{timestamp}.xml"
            filepath = os.path.join(client_dir, filename)
            
            # Guardar el archivo
            with open(filepath, 'wb') as f:
                f.write(response.content)
                
            return filepath
        except Exception as e:
            print(f"Error descargando XML: {str(e)}")
            return None

    def mark_as_read(self, uid: int) -> None:
        """Marca un mensaje como leído"""
        try:
            self.client.add_flags([uid], ['\Seen'])
        except Exception as e:
            print(f"Error marcando mensaje como leído: {str(e)}")