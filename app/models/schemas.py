from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from decimal import Decimal

class Emisor(BaseModel):
    nit: str
    nombre: str
    nombre_comercial: Optional[str] = None
    codigo_establecimiento: Optional[str] = None
    direccion: Optional[str] = None

class Receptor(BaseModel):
    nit: str
    nombre: str
    direccion: Optional[str] = None

class Item(BaseModel):
    numero_linea: int
    bien_servicio: str
    cantidad: Decimal
    unidad_medida: str
    descripcion: str
    precio_unitario: Decimal
    precio: Decimal
    descuento: Decimal
    total: Decimal
    impuestos: Dict[str, Any]

class Factura(BaseModel):
    numero_autorizacion: str
    serie: str
    numero: str
    fecha_emision: datetime
    tipo_documento: str
    emisor: Emisor
    receptor: Receptor
    items: List[Item]
    total: Decimal
    iva: Decimal
    moneda: str = "GTQ"
    xml_path: str
    certificador_nombre: Optional[str] = None
    certificador_nit: Optional[str] = None
    fecha_procesamiento: datetime = Field(default_factory=datetime.now)

class FacturaResumen(BaseModel):
    numero_autorizacion: str
    fecha_emision: datetime
    emisor_nombre: str
    emisor_nit: str
    total: Decimal
    
class ClienteResumen(BaseModel):
    nit: str
    nombre: str
    total_facturas: int
    suma_total: Decimal
    facturas: List[FacturaResumen]