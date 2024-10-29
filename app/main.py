from fastapi import FastAPI, HTTPException
from typing import List, Optional
import logging
from datetime import datetime
import os
from app.core.email_processor import EmailProcessor
from app.core.xml_processor import XMLProcessor
from app.models.schemas import ClienteResumen, FacturaResumen, Factura
from app.config import get_settings, create_required_directories
import json
from decimal import Decimal
from fastapi.staticfiles import StaticFiles
from .web import routes as web_routes

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SAT Factura Processor",
    description="API para procesamiento de facturas electrónicas del SAT",
    version="1.0.0"
)

# Montar archivos estáticos y rutas web
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web_routes.router)

settings = get_settings()

def process_new_invoices():
    """Procesa nuevos correos y sus facturas"""
    email_processor = EmailProcessor()
    xml_processor = XMLProcessor()
    processed_count = 0
    
    try:
        # Conectar al servidor de correo
        email_processor.connect()
        logger.info("Conectado al servidor de correo exitosamente")
        
        # Obtener mensajes no leídos
        messages = email_processor.get_unread_messages()
        logger.info(f"Se encontraron {len(messages)} mensajes nuevos")
        
        for message in messages:
            try:
                logger.info(f"Procesando mensaje con URL XML: {message.get('xml_url')}")
                # Descargar XML
                xml_path = email_processor.download_xml(
                    message['xml_url'], 
                    message['client']['nit']
                )
                
                if xml_path:
                    # Procesar XML
                    factura = xml_processor.process_xml(xml_path)
                    if factura:
                        processed_count += 1
                        # Marcar correo como leído
                        email_processor.mark_as_read(message['uid'])
                        logger.info(f"Factura procesada exitosamente: {factura.serie}-{factura.numero}")
                    
            except Exception as e:
                logger.error(f"Error procesando mensaje: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error en el proceso: {str(e)}")
        raise
        
    finally:
        email_processor.disconnect()
        
    return processed_count

@app.post("/process")
async def trigger_processing():
    """Endpoint para iniciar el procesamiento de nuevas facturas"""
    try:
        processed_count = process_new_invoices()
        return {"message": f"Proceso completado. {processed_count} facturas procesadas"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/facturas/cliente/{nit}")
async def get_client_invoices(
    nit: str,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
) -> ClienteResumen:
    """Obtiene todas las facturas de un cliente específico"""
    try:
        client_dir = os.path.join(settings.PROCESSED_DATA_PATH, nit)
        if not os.path.exists(client_dir):
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
            
        facturas = []
        suma_total = Decimal('0')
        nombre_cliente = ""
        
        # Convertir fechas si se proporcionaron
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d") if fecha_inicio else None
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d") if fecha_fin else None
        
        # Leer todos los archivos JSON del cliente
        for filename in os.listdir(client_dir):
            if filename.endswith('.json'):
                with open(os.path.join(client_dir, filename), 'r') as f:
                    factura_data = json.load(f)
                    
                    # Convertir la fecha de la factura
                    fecha_factura = datetime.fromisoformat(factura_data['fecha_emision'])
                    
                    # Aplicar filtro de fechas si se especificaron
                    if fecha_inicio_dt and fecha_factura < fecha_inicio_dt:
                        continue
                    if fecha_fin_dt and fecha_factura > fecha_fin_dt:
                        continue
                    
                    # Guardar el nombre del cliente
                    if not nombre_cliente:
                        nombre_cliente = factura_data['receptor']['nombre']
                    
                    # Crear resumen de factura
                    factura_resumen = FacturaResumen(
                        numero_autorizacion=factura_data['numero_autorizacion'],
                        fecha_emision=fecha_factura,
                        emisor_nombre=factura_data['emisor']['nombre'],
                        emisor_nit=factura_data['emisor']['nit'],
                        total=Decimal(factura_data['total'])
                    )
                    
                    facturas.append(factura_resumen)
                    suma_total += Decimal(factura_data['total'])
        
        return ClienteResumen(
            nit=nit,
            nombre=nombre_cliente,
            total_facturas=len(facturas),
            suma_total=suma_total,
            facturas=sorted(facturas, key=lambda x: x.fecha_emision, reverse=True)
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo facturas del cliente {nit}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/facturas/{serie}/{numero}")
async def get_invoice_detail(serie: str, numero: str) -> Factura:
    """Obtiene el detalle completo de una factura específica"""
    try:
        # Buscar en todos los directorios de clientes
        for client_dir in os.listdir(settings.PROCESSED_DATA_PATH):
            client_path = os.path.join(settings.PROCESSED_DATA_PATH, client_dir)
            if os.path.isdir(client_path):
                # Buscar el archivo de la factura
                for filename in os.listdir(client_path):
                    if filename.startswith(f"{serie}_{numero}_") and filename.endswith('.json'):
                        with open(os.path.join(client_path, filename), 'r') as f:
                            return Factura.model_validate(json.load(f))
                            
        raise HTTPException(status_code=404, detail="Factura no encontrada")
        
    except Exception as e:
        logger.error(f"Error obteniendo factura {serie}-{numero}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Endpoint para verificar el estado del servicio"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Crear directorios necesarios al iniciar la aplicación
create_required_directories()