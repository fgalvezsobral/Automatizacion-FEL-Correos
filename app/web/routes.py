from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from datetime import datetime, timedelta
import json
from ..config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    settings = get_settings()
    fecha_fin = datetime.now().date()
    fecha_inicio = fecha_fin - timedelta(days=30)
     
    # Obtener datos
    facturas = []
    total_monto = 0
    clientes = set()
    
    # Recorrer directorios de clientes
    for client_dir in os.listdir(settings.PROCESSED_DATA_PATH):
        client_path = os.path.join(settings.PROCESSED_DATA_PATH, client_dir)
        if os.path.isdir(client_path):
            # Procesar facturas del cliente
            for filename in os.listdir(client_path):
                if filename.endswith('.json'):
                    with open(os.path.join(client_path, filename), 'r') as f:
                        factura = json.load(f)
                        fecha = datetime.fromisoformat(factura['fecha_emision']).date()
                        
                        if fecha_inicio <= fecha <= fecha_fin and float(factura['total']) > 0:
                            facturas.append(factura)
                            total_monto += float(factura['total'])
                            clientes.add(factura['receptor']['nit'])
    
    # Ordenar facturas por fecha
    facturas.sort(key=lambda x: x['fecha_emision'], reverse=True)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_facturas": len(facturas),
        "total_monto": total_monto,
        "total_clientes": len(clientes),
        "facturas": facturas[:10],  # Mostrar solo las 10 más recientes
        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
        "fecha_fin": fecha_fin.strftime("%Y-%m-%d")
    })

@router.get("/factura/{serie}/{numero}", response_class=HTMLResponse)
async def factura_detalle(request: Request, serie: str, numero: str):
    settings = get_settings()
    
    # Buscar la factura en los archivos
    for client_dir in os.listdir(settings.PROCESSED_DATA_PATH):
        client_path = os.path.join(settings.PROCESSED_DATA_PATH, client_dir)
        if os.path.isdir(client_path):
            for filename in os.listdir(client_path):
                if filename.startswith(f"{serie}_{numero}_") and filename.endswith('.json'):
                    with open(os.path.join(client_path, filename), 'r') as f:
                        factura = json.load(f)
                        return templates.TemplateResponse(
                            "factura_detalle.html",
                            {"request": request, "factura": factura}
                        )
    
    # Si no se encuentra la factura
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "mensaje": "Factura no encontrada"}
    )

def format_number(value):
    """Formato para números con separador de miles y dos decimales"""
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return value

def format_date(value):
    """Formato para fechas en español"""
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        return value.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return value

# Registrar los filtros
templates.env.filters["format_number"] = format_number
templates.env.filters["format_date"] = format_date