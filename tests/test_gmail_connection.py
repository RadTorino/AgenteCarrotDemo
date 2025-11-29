import pytest
from unittest.mock import MagicMock, patch
import smtplib
from src.schemas.schemas import NotificacionSchema
from src.modules.gmail_connection import send_notification, EmailTemplates

# Pytest marker for async functions
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_smtp(mocker):
    """
    Fixture to mock the smtplib.SMTP class.
    This prevents actual emails from being sent during tests.
    It returns the mock instance for asserting calls.
    """
    # Patch the SMTP class in the smtplib module
    with patch("smtplib.SMTP") as mock_smtp_class:
        # When smtplib.SMTP is called, it returns a mock instance.
        # We configure this instance to also work as a context manager.
        mock_instance = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_instance
        yield mock_instance

@pytest.fixture(autouse=True)
def mock_settings(mocker):
    """
    Fixture to automatically mock all required settings.
    This ensures that no real credentials or emails are used.
    """
    mocker.patch("src.modules.gmail_connection.settings.SENDER_EMAIL", "test_sender@example.com")
    mocker.patch("src.modules.gmail_connection.settings.SENDER_PASSWORD", "test_password")
    mocker.patch("src.modules.gmail_connection.settings.SALES_EMAIL", "sales@example.com")
    mocker.patch("src.modules.gmail_connection.settings.PROCUREMENT_EMAIL", "procurement@example.com")
    mocker.patch("src.modules.gmail_connection.settings.HR_EMAIL", "hr@example.com")
    mocker.patch("src.modules.gmail_connection.settings.SUPPORT_EMAIL", "support@example.com")

async def test_send_notification_new_wholesale_client(mock_smtp):
    """
    Tests the email notification for a 'new_wholesale_client'.
    Verifies that the correct template, recipient, and email content are used.
    """
    # 1. Arrange: Create the notification data
    notification = NotificacionSchema(
        type="nuevo_cliente_mayorista",
        data={
            "cuit": "30-12345678-9",
            "razon_social": "Test Corp",
            "direccion": "123 Main St",
            "localidad": "Anytown",
            "telefono_contacto": "555-1234"
        }
    )

    # 2. Act: Call the function to send the notification
    success = await send_notification(notification)

    # 3. Assert: Verify the outcome
    assert success is True
    mock_smtp.send_message.assert_called_once()
    
    #Verify the email content
    sent_message = mock_smtp.send_message.call_args[0][0]
    assert sent_message["To"] == "sales@example.com"
    assert sent_message["Subject"] == "Nuevo Cliente Mayorista"
    
    # Decode the payload from base64 bytes into a string
    email_body = sent_message.get_payload()[0].get_payload(decode=True).decode('utf-8')
    assert "CUIT: 30-12345678-9" in email_body

async def test_send_notification_potential_supplier(mock_smtp):
    """
    Tests the email notification for a 'potencial_proveedor'.
    Verifies that the correct template is used, including the file URL.
    """
    # 1. Arrange
    notification = NotificacionSchema(
        type="potencial_proveedor",
        file_url="http://example.com/supplier_doc.pdf",
        data={
            "producto_servicio": "Office Supplies",
            "info_contacto": "supplier@supply.com",
            "telefono_contacto": "555-5678"
        }
    )

    # 2. Act
    success = await send_notification(notification)

    # 3. Assert
    assert success is True
    mock_smtp.send_message.assert_called_once()
    sent_message = mock_smtp.send_message.call_args[0][0]
    assert sent_message["To"] == "procurement@example.com"
    assert sent_message["Subject"] == "Nuevo Proveedor Potencial"
    
    # Decode the payload from base64 bytes into a string
    email_body = sent_message.get_payload()[0].get_payload(decode=True).decode('utf-8')
    assert "Documento de Presentación: http://example.com/supplier_doc.pdf" in email_body

async def test_send_notification_job_candidate(mock_smtp):
    """
    Tests the email notification for a 'potencial_empleado'.
    Verifies that the correct template is used for sending a CV.
    """
    # 1. Arrange
    notification = NotificacionSchema(
        type="potencial_empleado",
        file_url="http://example.com/cv.pdf",
        data={} # Data might be empty for this type
    )

    # 2. Act
    success = await send_notification(notification)

    # 3. Assert
    assert success is True
    mock_smtp.send_message.assert_called_once()
    sent_message = mock_smtp.send_message.call_args[0][0]
    assert sent_message["To"] == "hr@example.com"
    assert sent_message["Subject"] == "Nuevo CV Recibido"

    # Decode the payload from base64 bytes into a string
    email_body = sent_message.get_payload()[0].get_payload(decode=True).decode('utf-8')
    assert "URL del CV: http://example.com/cv.pdf" in email_body

async def test_send_notification_customer_complaint(mock_smtp):
    """
    Tests the email notification for a 'reclamos'.
    Verifies that the complaint template is used with all relevant data.
    """
    # 1. Arrange
    notification = NotificacionSchema(
        type="reclamos",
        user_id="user-abc-123",
        file_url="http://example.com/broken_item.jpg",
        data={
            "info": "The product arrived damaged.",
            "numero_pedido": "ORDER-987",
            "nombre_contacto": "Jane Doe",
            "telefono_contacto": "555-8765"
        }
    )

    # 2. Act
    success = await send_notification(notification)

    # 3. Assert
    assert success is True
    mock_smtp.send_message.assert_called_once()
    sent_message = mock_smtp.send_message.call_args[0][0]
    assert sent_message["To"] == "support@example.com"
    assert sent_message["Subject"] == "Nuevo Reclamo"

    # Decode the payload from base64 bytes into a string
    email_body = sent_message.get_payload()[0].get_payload(decode=True).decode('utf-8')
    assert "Cliente ID: user-abc-123" in email_body
    assert "Imagen adjunta: http://example.com/broken_item.jpg" in email_body

async def test_send_notification_unsupported_type(mock_smtp, caplog):
    """
    Tests that the function handles an unsupported notification type gracefully.
    It should log an error and return False without sending an email.
    """
    # 1. Arrange
    notification = NotificacionSchema(type="unsupported_type", data={})

    # 2. Act
    success = await send_notification(notification)

    # 3. Assert
    assert success is False
    # Ensure no email was sent
    mock_smtp.send_message.assert_not_called()
    # Check that an error was logged
    assert "Unsupported notification type: unsupported_type" in caplog.text

async def test_send_notification_smtp_error(mock_smtp, caplog):
    """
    Tests that the function handles an SMTP error during email sending.
    It should log the error and return False.
    """
    # 1. Arrange: Configure the mock to raise an exception
    mock_smtp.send_message.side_effect = smtplib.SMTPException("Test SMTP Error")
    notification = NotificacionSchema(type="reclamos", data={}, user_id="test", file_url="test")

    # 2. Act
    success = await send_notification(notification)

    # 3. Assert
    assert success is False
    # Check that an error was logged
    assert "Failed to send email - Type: reclamos" in caplog.text
    assert "Error sending email: Test SMTP Error" in caplog.text