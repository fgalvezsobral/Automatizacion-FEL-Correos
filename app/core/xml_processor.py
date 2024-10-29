import xmltodict
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import os
from decimal import Decimal
from ..models.schemas import Factura, Emisor, Receptor, Item
from ..config import get_settings

class XMLProcessor:
    def __init__(self):
        self.settings = get_settings()
        self.namespaces = {
            'dte': 'http://www.sat.gob.gt/dte/fel/0.2.0',
            'ds': 'http://www.w3.org/2000/09/xmldsig#'
        }

    def process_xml(self, xml_path: str) -> Optional[Factura]:
        """Procesa un archivo XML y retorna un objeto Factura"""
        try:
            # Primera intentamos con UTF-8
            try:
                with open(xml_path, 'r', encoding='utf-8') as file:
                    xml_content = file.read()
            except UnicodeDecodeError:
                # Si falla UTF-8, intentamos con latin-1 (ISO-8859-1)
                try:
                    with open(xml_path, 'r', encoding='latin-1') as file:
                        xml_content = file.read()
                except UnicodeDecodeError:
                    # Si aún falla, leemos en modo binario y decodificamos con detección
                    with open(xml_path, 'rb') as file:
                        raw_content = file.read()
                        # Intentar detectar la codificación
                        if raw_content.startswith(b'\xef\xbb\xbf'):  # UTF-8 con BOM
                            xml_content = raw_content.decode('utf-8-sig')
                        elif raw_content.startswith(b'\xff\xfe'):    # UTF-16 LE
                            xml_content = raw_content.decode('utf-16')
                        else:
                            # Intentar decodificar con utf-8 ignorando errores
                            xml_content = raw_content.decode('utf-8', errors='replace')
            
            # Limpiar caracteres no válidos en XML
            xml_content = self._clean_xml_content(xml_content)
                
            # Convertir XML a diccionario
            data = xmltodict.parse(xml_content)
            
            # Resto del código igual...
            dte_data = data.get('dte:GTDocumento', {})
            sat_data = dte_data.get('dte:SAT', {})
            dte = sat_data.get('dte:DTE', {})
            datos_emision = dte.get('dte:DatosEmision', {})
            
            if not datos_emision:
                raise ValueError("No se encontraron los datos de emisión en el XML")

            # Extraer datos de certificación
            certificacion = dte.get('dte:Certificacion', {})
            
            # Crear objeto Factura
            factura = self._create_factura(datos_emision, certificacion, xml_path)
            
            # Guardar datos procesados
            self._save_processed_data(factura)
            
            return factura
                
        except Exception as e:
            print(f"Error procesando XML {xml_path}: {str(e)}")
            return None

    def _clean_xml_content(self, content: str) -> str:
        """Limpia caracteres no válidos en XML"""
        # Reemplazar caracteres de control excepto los permitidos en XML
        allowed = '\n\r\t'  # Caracteres de control permitidos
        return ''.join(char for char in content if char >= '\x20' or char in allowed)

    def _create_factura(self, datos_emision: Dict, certificacion: Dict, xml_path: str) -> Factura:
        """Crea un objeto Factura a partir de los datos del XML"""
        datos_generales = datos_emision.get('dte:DatosGenerales', {})
        
        # Crear objeto Emisor
        emisor_data = datos_emision.get('dte:Emisor', {})
        emisor = Emisor(
            nit=emisor_data.get('@NITEmisor', ''),
            nombre=emisor_data.get('@NombreEmisor', ''),
            nombre_comercial=emisor_data.get('@NombreComercial', ''),
            codigo_establecimiento=emisor_data.get('@CodigoEstablecimiento', ''),
            direccion=self._get_direccion(emisor_data.get('dte:DireccionEmisor', {}))
        )

        # Crear objeto Receptor
        receptor_data = datos_emision.get('dte:Receptor', {})
        receptor = Receptor(
            nit=receptor_data.get('@IDReceptor', ''),
            nombre=receptor_data.get('@NombreReceptor', ''),
            direccion=self._get_direccion(receptor_data.get('dte:DireccionReceptor', {}))
        )

        # Procesar items
        items = self._process_items(datos_emision.get('dte:Items', {}).get('dte:Item', []))

        # Obtener totales
        totales = datos_emision.get('dte:Totales', {})
        total_impuestos = totales.get('dte:TotalImpuestos', {})
        iva = total_impuestos.get('dte:TotalImpuesto', {}).get('@TotalMontoImpuesto', '0')
        
        # Obtener información de autorización
        autorizacion = certificacion.get('dte:NumeroAutorizacion', {})

        return Factura(
            numero_autorizacion=autorizacion.get('#text', ''),
            serie=autorizacion.get('@Serie', ''),
            numero=autorizacion.get('@Numero', ''),
            fecha_emision=datetime.fromisoformat(datos_generales.get('@FechaHoraEmision', '').replace('T', ' ').split('.')[0]),
            tipo_documento=datos_generales.get('@Tipo', ''),
            emisor=emisor,
            receptor=receptor,
            items=items,
            total=Decimal(totales.get('dte:GranTotal', '0')),
            iva=Decimal(iva),
            xml_path=xml_path,
            moneda=datos_generales.get('@CodigoMoneda', 'GTQ'),
            certificador_nombre=certificacion.get('dte:NombreCertificador', ''),
            certificador_nit=certificacion.get('dte:NITCertificador', '')
        )

    def _get_direccion(self, direccion_data: Dict) -> str:
        """Construye la dirección completa desde los componentes del XML"""
        if not direccion_data:
            return ""
            
        componentes = [
            direccion_data.get('dte:Direccion', ''),
            direccion_data.get('dte:Municipio', ''),
            direccion_data.get('dte:Departamento', ''),
            direccion_data.get('dte:Pais', '')
        ]
        
        return ", ".join(filter(None, componentes))

    def _process_items(self, items_data: list) -> List[Item]:
        """Procesa los items de la factura"""
        if not isinstance(items_data, list):
            items_data = [items_data]
            
        items = []
        for item in items_data:
            impuestos = item.get('dte:Impuestos', {}).get('dte:Impuesto', {})
            items.append(Item(
                numero_linea=int(item.get('@NumeroLinea', 0)),
                bien_servicio=item.get('@BienOServicio', ''),
                cantidad=Decimal(item.get('dte:Cantidad', '0')),
                unidad_medida=item.get('dte:UnidadMedida', ''),
                descripcion=item.get('dte:Descripcion', ''),
                precio_unitario=Decimal(item.get('dte:PrecioUnitario', '0')),
                precio=Decimal(item.get('dte:Precio', '0')),
                descuento=Decimal(item.get('dte:Descuento', '0')),
                total=Decimal(item.get('dte:Total', '0')),
                impuestos={
                    'nombre': impuestos.get('dte:NombreCorto', ''),
                    'codigo': impuestos.get('dte:CodigoUnidadGravable', ''),
                    'monto_gravable': Decimal(impuestos.get('dte:MontoGravable', '0')),
                    'monto_impuesto': Decimal(impuestos.get('dte:MontoImpuesto', '0'))
                }
            ))
        return items

    def _save_processed_data(self, factura: Factura) -> None:
        """Guarda los datos procesados en formato JSON"""
        try:
            # Crear directorio para el cliente si no existe
            client_dir = os.path.join(self.settings.PROCESSED_DATA_PATH, factura.receptor.nit)
            os.makedirs(client_dir, exist_ok=True)
            
            # Generar nombre de archivo usando la serie y número de la factura
            filename = f"{factura.serie}_{factura.numero}_{datetime.now().strftime('%Y%m%d')}.json"
            filepath = os.path.join(client_dir, filename)
            
            # Convertir a diccionario usando el método model_dump de Pydantic
            factura_dict = factura.model_dump()
            
            # Asegurar que la fecha de emisión sea string en formato ISO
            if isinstance(factura_dict.get('fecha_emision'), datetime):
                factura_dict['fecha_emision'] = factura_dict['fecha_emision'].isoformat()
            
            # Convertir otros tipos especiales (Decimal) a str
            self._convert_decimal_to_str(factura_dict)
            
            # Verificar el JSON antes de guardarlo
            try:
                # Intentar serializar para verificar que no hay errores
                json.dumps(factura_dict, ensure_ascii=False)
            except TypeError as e:
                print(f"Error en la serialización JSON: {str(e)}")
                # Imprimir los valores problemáticos
                for k, v in factura_dict.items():
                    print(f"{k}: {type(v)} = {v}")
                raise
            
            # Guardar como JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(factura_dict, f, ensure_ascii=False, indent=2)
                
            print(f"Archivo JSON guardado exitosamente: {filepath}")
                    
        except Exception as e:
            print(f"Error guardando datos procesados: {str(e)}")
            raise  # Re-lanzar la excepción para manejo superior

    def _convert_decimal_to_str(self, data: Any) -> None:
        """Convierte valores Decimal y datetime a str para serialización JSON"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, Decimal):
                    data[key] = str(value)
                elif isinstance(value, datetime):
                    data[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    self._convert_decimal_to_str(value)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                if isinstance(value, Decimal):
                    data[i] = str(value)
                elif isinstance(value, datetime):
                    data[i] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    self._convert_decimal_to_str(value)