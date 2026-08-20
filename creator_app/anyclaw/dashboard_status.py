"""Status Dashboard — สถานะระบบครบวงจร."""
import json
from pathlib import Path

def get_full_status():
    status = {
        "system": "AnyClaw",
        "version": "2.0",
        "components": {},
    }
    
    # USB Hub
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from creator_app.anyclaw.core import AnyClawCore
        claw = AnyClawCore(mode="super")
        hub = claw.hub_status()
        status["components"]["usb_hub"] = {
            "ports": hub["total_slots"],
            "types": hub["by_type"],
            "calls": hub["stats"]["total_calls"],
        }
    except:
        status["components"]["usb_hub"] = {"status": "error"}
    
    # Email
    try:
        from creator_app.anyclaw.connectors.email_connector import EmailConnector
        ec = EmailConnector()
        status["components"]["email"] = ec.status()
    except:
        status["components"]["email"] = {"status": "error"}
    
    # Intelligence
    status["components"]["intelligence"] = {
        "reflexion": True,
        "computer_use": True,
        "background_executor": True,
        "mcp_hub": True,
    }
    
    return status
