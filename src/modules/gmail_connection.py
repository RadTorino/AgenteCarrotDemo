import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from urllib.parse import quote
from src.schemas.schemas import NotificacionSchema
from src.modules.file_mapping_service import FileMappingService
from src.utils.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

file_mapper = FileMappingService()

class EmailConfig:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = 587
        self.sender_email = settings.SENDER_EMAIL
        self.sender_password = settings.SENDER_PASSWORD
        
        # Different department emails based on notification type
        self.department_emails = {
            "nuevo_cliente_mayorista": settings.SALES_EMAIL,
            "potencial_proveedor": settings.PROCUREMENT_EMAIL,
            "potencial_empleado": settings.HR_EMAIL,
            "pedidos_pendientes": settings.ORDERS_EMAIL,
            "facturacion": settings.BILLING_EMAIL,
            "reclamos": settings.SUPPORT_EMAIL
        }

class EmailTemplates:
    @staticmethod
    def new_wholesale_client(data: Dict[str, Any]) -> tuple:
        subject = "Nuevo Cliente Mayorista"
        body = f"""
        Se ha contactado un nuevo cliente mayorista:
        
        CUIT: {data.get('cuit', 'N/A')}
        Razón Social: {data.get('razon_social', 'N/A')}
        Dirección: {data.get('direccion', 'N/A')}
        Localidad: {data.get('localidad', 'N/A')}
        Teléfono: {data.get('telefono_contacto', 'N/A')}
        """
        return subject, body

    @staticmethod
    def potential_supplier(data: Dict[str, Any], file_url: Optional[str]) -> tuple:
        subject = "Nuevo Proveedor Potencial"
        encoded_url = quote(file_url, safe=':/') if file_url else 'No adjunto'
        body = f"""
        Se ha contactado un nuevo proveedor potencial:
        
        Producto/Servicio: {data.get('producto_servicio', 'N/A')}
        Información de Contacto: {data.get('info_contacto', 'N/A')}
        Documento de Presentación: {encoded_url}
        Telefono: {data.get('telefono_contacto', 'N/A')},
        Descripción Adicional: {data.get('descripcion_adicional', 'N/A')}
        """
        return subject, body

    @staticmethod
    def job_candidate(data: Dict[str, Any], file_url: Optional[str]) -> tuple:
        subject = "Nuevo CV Recibido"
        encoded_url = quote(file_url, safe=':/') if file_url else 'No adjunto'
        body = f"""
        Se ha recibido un nuevo CV:

        Descripción: {data.get('descripcion_adicional', 'N/A')}
        
        URL del CV: {encoded_url}
        """
        return subject, body

    @staticmethod
    def customer_complaint(data: Dict[str, Any], user_id: Optional[str], file_url: Optional[str]) -> tuple:
        subject = "Nuevo Reclamo"
        encoded_url = quote(file_url, safe=':/') if file_url else 'No adjunta'
        body = f"""
        Se ha registrado un nuevo reclamo:
        
        Cliente ID: {user_id if user_id else 'No registrado'}
        Descripción: {data.get('info', 'N/A')}
        Número de Pedido: {data.get('numero_pedido', 'N/A')}
        Nombre de Contacto: {data.get('nombre_contacto', 'N/A')}
        Teléfono: {data.get('telefono_contacto', 'N/A')}
        Imagen adjunta: {encoded_url}
        """
        return subject, body

class EmailHandler:
    def __init__(self):
        self.config = EmailConfig()
        self.templates = EmailTemplates()

    def _send_email(self, subject: str, body: str, to_email: str) -> bool:
        try:
            message = MIMEMultipart()
            message["From"] = self.config.sender_email
            message["To"] = to_email
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.sender_email, self.config.sender_password)
                server.send_message(message)
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

async def send_notification(notification: NotificacionSchema) -> bool:
    try:
        email_handler = EmailHandler()
        
        # Map notification types to template methods
        template_map = {
            "nuevo_cliente_mayorista": email_handler.templates.new_wholesale_client,
            "potencial_proveedor": email_handler.templates.potential_supplier,
            "potencial_empleado": email_handler.templates.job_candidate,
            "reclamos":   email_handler.templates.customer_complaint,
        }

        if notification.type not in template_map:
            raise ValueError(f"Unsupported notification type: {notification.type}")

        # Get the appropriate email template
        match notification.type:
            case "nuevo_cliente_mayorista":
                subject, body = template_map[notification.type](notification.data)
            case "reclamos":
                subject, body = template_map[notification.type](notification.data, notification.user_id, notification.file_url)
            case _:
                subject, body = template_map[notification.type](notification.data, notification.file_url)
        
        # Get the appropriate department email
        to_email = email_handler.config.department_emails.get(notification.type)
        if not to_email:
            raise ValueError(f"No email configured for notification type: {notification.type}")

        success = email_handler._send_email(
            subject=subject,
            body=body,
            to_email=to_email
        )

        if success:
            logger.info(f"Email sent successfully - Type: {notification.type}")
        else:
            logger.error(f"Failed to send email - Type: {notification.type}")

        return success

    except Exception as e:
        logger.error(f"Error processing notification: {e}")
        return False

