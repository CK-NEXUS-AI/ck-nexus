"""Email Connector — เชื่อม Gmail + Hotmail อัตโนมัติ."""
import json
from pathlib import Path

class EmailConnector:
    def __init__(self):
        self.gmail_creds = Path.home() / ".config/google-oauth/credentials.json"
        self.outlook_creds = Path.home() / ".config/microsoft-oauth/credentials.json"
    
    def get_gmail_status(self):
        if not self.gmail_creds.exists():
            return {"status": "not_configured", "message": "Need OAuth setup"}
        creds = json.loads(self.gmail_creds.read_text())
        if creds.get("installed", {}).get("client_id", "").startswith("YOUR"):
            return {"status": "template_only", "message": "Need real credentials"}
        return {"status": "ready", "message": "Gmail configured"}
    
    def get_outlook_status(self):
        if not self.outlook_creds.exists():
            return {"status": "not_configured", "message": "Need OAuth setup"}
        creds = json.loads(self.outlook_creds.read_text())
        if creds.get("web", {}).get("client_id", "").startswith("YOUR"):
            return {"status": "template_only", "message": "Need real credentials"}
        return {"status": "ready", "message": "Outlook configured"}
    
    def status(self):
        return {
            "gmail": self.get_gmail_status(),
            "outlook": self.get_outlook_status(),
        }
