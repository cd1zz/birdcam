# services/azure_email_provider.py
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import requests
from msal import ConfidentialClientApplication
from utils.capture_logger import logger

class AzureEmailProvider:
    """Azure Graph API email provider using MSAL for authentication"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, 
                 sender_email: Optional[str] = None, use_shared_mailbox: bool = False):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.sender_email = sender_email
        self.use_shared_mailbox = use_shared_mailbox
        
        # Initialize MSAL app
        self.app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}"
        )
        
        # Cache for access token
        self._token_cache = None
        self._token_expiry = None
        
        # Graph API endpoint
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
    
    def _get_access_token(self) -> Optional[str]:
        """Get access token with caching"""
        # Check if we have a valid cached token
        if self._token_cache and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._token_cache
        
        # Request new token
        try:
            # Use application permissions (Mail.Send)
            result = self.app.acquire_token_silent(
                scopes=["https://graph.microsoft.com/.default"],
                account=None
            )
            
            if not result:
                result = self.app.acquire_token_for_client(
                    scopes=["https://graph.microsoft.com/.default"]
                )
            
            if "access_token" in result:
                self._token_cache = result["access_token"]
                # Token typically expires in 1 hour, cache for 55 minutes
                self._token_expiry = datetime.utcnow() + timedelta(minutes=55)
                logger.info("[AZURE] Successfully acquired access token")
                return self._token_cache
            else:
                logger.error(f"[AZURE] Failed to acquire token: {result.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"[AZURE] Error acquiring token: {e}")
            return None
    
    def send_email(self, to: str, subject: str, body: str, html: Optional[str] = None,
                   cc: Optional[list] = None, bcc: Optional[list] = None,
                   attachments: Optional[list] = None) -> bool:
        """Send email using Microsoft Graph API"""
        token = self._get_access_token()
        if not token:
            logger.error("[AZURE] No access token available")
            return False
        
        # Prepare email message
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if html else "Text",
                    "content": html if html else body
                },
                "toRecipients": [{"emailAddress": {"address": to}}]
            },
            "saveToSentItems": True
        }
        
        # Add CC recipients
        if cc:
            message["message"]["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc
            ]
        
        # Add BCC recipients
        if bcc:
            message["message"]["bccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in bcc
            ]
        
        # Add attachments if provided
        if attachments:
            message["message"]["attachments"] = attachments
        
        # Determine endpoint based on sender configuration
        if self.sender_email:
            if self.use_shared_mailbox:
                # Send from shared mailbox
                endpoint = f"{self.graph_endpoint}/users/{self.sender_email}/sendMail"
            else:
                # Send as specific user
                endpoint = f"{self.graph_endpoint}/users/{self.sender_email}/sendMail"
        else:
            # Send as authenticated app (requires specific mailbox permissions)
            endpoint = f"{self.graph_endpoint}/me/sendMail"
        
        # Send the email
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=message,
                timeout=30
            )
            
            if response.status_code == 202:
                logger.info(f"[AZURE] Email sent successfully to {to}")
                return True
            else:
                logger.error(f"[AZURE] Failed to send email. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("[AZURE] Email send request timed out")
            return False
        except Exception as e:
            logger.error(f"[AZURE] Error sending email: {e}")
            return False
    
    def create_file_attachment(self, filename: str, content: bytes, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """Create a file attachment for Graph API"""
        import base64
        
        return {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": filename,
            "contentType": content_type,
            "contentBytes": base64.b64encode(content).decode('utf-8')
        }
    
    def validate_configuration(self) -> tuple[bool, str]:
        """Validate Azure AD configuration"""
        if not self.tenant_id:
            return False, "Azure tenant ID is required"
        
        if not self.client_id:
            return False, "Azure client ID is required"
        
        if not self.client_secret:
            return False, "Azure client secret is required"
        
        # Try to acquire token to validate credentials
        token = self._get_access_token()
        if not token:
            return False, "Failed to authenticate with Azure AD"
        
        return True, "Azure configuration is valid"