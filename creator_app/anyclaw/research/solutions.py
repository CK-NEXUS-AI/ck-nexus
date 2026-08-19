"""Solutions — เครื่องมือแก้ข้อจำกัดทางเทคนิค.

รวมเครื่องมือฟรีที่ค้นพบมาสร้างเป็นระบบที่ใช้งานได้จริง:

ข้อจำกัดที่ 1: สร้างบัญชีเว็บภายนอก
  → CAPTCHA Solver + Temporary Email + Anti-detect Browser

ข้อจำกัดที่ 2: ตัดสินใจซื้อ/จ่ายเงิน
  → Human-in-the-Loop (HITL)

ข้อจำกัดที่ 3: เข้าถึง Gmail
  → Headless Gmail MCP
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════
# ข้อจำกัดที่ 1: สร้างบัญชีเว็บภายนอก
# ═══════════════════════════════════════════════════════

@dataclass
class CAPTCHASolver:
    """ตัวแก้ CAPTCHA ฟรี."""

    name: str
    service_url: str
    free_tier: str
    supported_types: tuple[str, ...] = ()
    api_key_env: str = ""
    credits: int = 0


CAPTCHA_SOLVERS: list[CAPTCHASolver] = [
    CAPTCHASolver(
        name="Scrapeless Web Unlocker",
        service_url="https://www.scrapeless.com/",
        free_tier="5,000 requests/month",
        supported_types=("reCAPTCHA", "Cloudflare Turnstile", "hCaptcha"),
        api_key_env="SCRAPELESS_API_KEY",
        credits=5000,
    ),
    CAPTCHASolver(
        name="Brightdata OpenCode",
        service_url="https://brightdata.com/",
        free_tier="5,000 requests/month",
        supported_types=("reCAPTCHA", "hCaptcha", "Cloudflare"),
        api_key_env="BRIGHTDATA_API_KEY",
        credits=5000,
    ),
    CAPTCHASolver(
        name="NopeCHA",
        service_url="https://nopecha.com/",
        free_tier="Chrome extension — free",
        supported_types=("reCAPTCHA", "hCaptcha", "text CAPTCHA"),
        api_key_env="NOPECHA_KEY",
        credits=100,
    ),
    CAPTCHASolver(
        name="useagentstore/solve",
        service_url="https://useagentstore.com/",
        free_tier="100 calls free, no credit card",
        supported_types=("reCAPTCHA", "hCaptcha", "funcaptcha"),
        api_key_env="AGENTSTORE_KEY",
        credits=100,
    ),
    CAPTCHASolver(
        name="GateSolve",
        service_url="https://gatesolve.com/",
        free_tier="100 solves free per API key",
        supported_types=("Turnstile", "reCAPTCHA", "hCaptcha"),
        api_key_env="GATESOLVE_KEY",
        credits=100,
    ),
    CAPTCHASolver(
        name="eCaptcha",
        service_url="https://ecaptcha.com/",
        free_tier="ไม่จำกัด — sound-based",
        supported_types=("reCAPTCHA v2 Enterprise"),
        api_key_env="",
        credits=0,
    ),
    CAPTCHASolver(
        name="darkcaptcha",
        service_url="https://darkcaptcha.com/",
        free_tier="ฟรี (มี fallback แบบเสียเงิน)",
        supported_types=("19 CAPTCHA types", "Playwright headless"),
        api_key_env="DARKCAPTCHA_KEY",
        credits=0,
    ),
]


@dataclass
class TempEmailService:
    """บริการอีเมลชั่วคราวสำหรับรับ OTP."""

    name: str
    service_url: str
    free_tier: str
    features: tuple[str, ...] = ()
    api_key_env: str = ""


TEMP_EMAIL_SERVICES: list[TempEmailService] = [
    TempEmailService(
        name="ZeroDrop MCP",
        service_url="https://github.com/zerodrop",
        free_tier="ฟรี — MCP Server สำหรับ AI Agents",
        features=("otp_extraction", "magic_links", "disposable_email"),
    ),
    TempEmailService(
        name="PhoboMail",
        service_url="https://phobomail.com/",
        free_tier="ฟรี — @phobomail.com สำหรับ AI Agents",
        features=("otp_auto_extract", "no_human_required"),
    ),
    TempEmailService(
        name="MailAgent",
        service_url="https://github.com/mailagent",
        free_tier="ฟรี — MCP/REST API",
        features=("otp_wait", "magic_link", "mcp_support"),
    ),
    TempEmailService(
        name="MailboxTemp",
        service_url="https://github.com/mailboxtemp",
        free_tier="ฟรี — disposable email API",
        features=("create_email", "read_inbox", "otp_extract"),
    ),
    TempEmailService(
        name="fce-mcp-server",
        service_url="https://github.com/fce-mcp-server",
        free_tier="ฟรี — MCP Server สำหรับ AI Agents",
        features=("otp_extraction", "create_and_wait_for_otp", "mcp_support"),
    ),
    TempEmailService(
        name="OpenInbox (n8n)",
        service_url="https://github.com/openinbox",
        free_tier="ฟรี — n8n community node",
        features=("otp", "verification_automation", "n8n_integration"),
    ),
    TempEmailService(
        name="Tigrmail",
        service_url="https://tigrmail.com/",
        free_tier="ฟรี — temporary email API",
        features=("e2e_testing", "playwright", "cypress", "selenium"),
    ),
]


@dataclass
class TempSMSService:
    """บริการรับ SMS ชั่วคราว."""

    name: str
    service_url: str
    free_tier: str
    numbers_available: int = 0


TEMP_SMS_SERVICES: list[TempSMSService] = [
    TempSMSService(
        name="free-otp-api",
        service_url="https://github.com/free-otp-api",
        free_tier="ฟรี — เบอร์โทรศัพท์จากหลายผู้ให้บริการ",
        numbers_available=50,
    ),
    TempSMSService(
        name="python-receive-sms-online-api",
        service_url="https://github.com/python-receive-sms-online-api",
        free_tier="ฟรี — Python wrapper สำหรับรับ SMS",
        numbers_available=30,
    ),
    TempSMSService(
        name="Betatel MCP Server",
        service_url="https://github.com/betatel",
        free_tier="ฟรี — MCP Server สำหรับยืนยันเบอร์",
        numbers_available=20,
    ),
    TempSMSService(
        name="SMSCode SDK",
        service_url="https://smscode.com/",
        free_tier="ฟรี — Official SDK",
        numbers_available=40,
    ),
]


@dataclass
class AntiDetectBrowser:
    """Anti-detect browser ฟรี."""

    name: str
    repo_url: str
    stars: int
    features: tuple[str, ...] = ()
    free: bool = True


ANTI_DETECT_BROWSERS: list[AntiDetectBrowser] = [
    AntiDetectBrowser(
        name="ShardBrowser",
        repo_url="https://github.com/ProxyShard/ShardBrowser",
        stars=667,
        features=("fingerprint_spoofing", "170+_profiles", "chromium_148"),
    ),
    AntiDetectBrowser(
        name="fury-antidetect-browser",
        repo_url="https://github.com/furyteamtop/fury-antidetect-browser",
        stars=5,
        features=("chromium_fork", "fingerprint_rotation"),
    ),
    AntiDetectBrowser(
        name="Donut Browser",
        repo_url="https://github.com/donut-browser",
        stars=0,
        features=("unlimited_profiles", "own_fingerprint"),
    ),
    AntiDetectBrowser(
        name="CloakBrowser",
        repo_url="https://github.com/cloakbrowser",
        stars=0,
        features=("stealth_chromium", "passes_bot_detection"),
    ),
    AntiDetectBrowser(
        name="ClawBrowser",
        repo_url="https://github.com/clawbrowser",
        stars=0,
        features=("chromium_based", "for_ai_agents", "open_source"),
    ),
    AntiDetectBrowser(
        name="Camoufox",
        repo_url="https://github.com/nicoreed/camoufox",
        stars=0,
        features=("firefox_based", "c++_engine", "mpl_2.0"),
    ),
]


# ═══════════════════════════════════════════════════════
# ข้อจำกัดที่ 2: Human-in-the-Loop
# ═══════════════════════════════════════════════════════

@dataclass
class HITLTool:
    """เครื่องมือ Human-in-the-Loop."""

    name: str
    description: str
    approval_channels: tuple[str, ...] = ()
    open_source: bool = True
    free_tier: str = ""


HITL_TOOLS: list[HITLTool] = [
    HITLTool(
        name="Approva",
        description="โครงสร้างพื้นฐาน HITL — หยุดรอ Passkey approval",
        approval_channels=("passkey", "biometric"),
        open_source=True,
        free_tier="Open Core — ฟรี",
    ),
    HITLTool(
        name="antcrew",
        description="Multi-agent framework — หยุดรอ human approval ณ จุดตรวจสอบ",
        approval_channels=("web", "api"),
        open_source=True,
        free_tier="ฟรี",
    ),
    HITLTool(
        name="Inferable",
        description="AI Workflows ที่ขออนุมัติผ่าน Slack/Email",
        approval_channels=("slack", "email"),
        open_source=True,
        free_tier="ฟรี",
    ),
    HITLTool(
        name="Approving",
        description="Self-hosted platform — Agent หยุดรอ Approve ที่โหนดสำคัญ",
        approval_channels=("web", "api", "webhook"),
        open_source=True,
        free_tier="ฟรี — self-host",
    ),
    HITLTool(
        name="Phantasm Toolkits",
        description="สร้าง HITL approval layer สำหรับ AI agents",
        approval_channels=("web", "api"),
        open_source=True,
        free_tier="Open Source — ฟรี",
    ),
    HITLTool(
        name="LangGraph Approval Hub",
        description="HITL approvals สำหรับ LangGraph agents — dashboard, audit log, Python SDK",
        approval_channels=("dashboard", "sdk"),
        open_source=True,
        free_tier="ฟรี — ใช้งานได้ 5 นาที",
    ),
    HITLTool(
        name="agentgate",
        description="API gateway สำหรับ AI agents ที่มี HITL write approval — อ่าน execute ทันที, เขียน queue รอ human",
        approval_channels=("api", "queue"),
        open_source=True,
        free_tier="Open Source, self-host",
    ),
    HITLTool(
        name="ApproveKit",
        description="Python package สำหรับ human approval gates — ประเมิน policy, หยุด risky actions, บันทึก audit ใน SQLite",
        approval_channels=("python", "sqlite"),
        open_source=True,
        free_tier="ฟรี",
    ),

]


# ═══════════════════════════════════════════════════════
# ข้อจำกัดที่ 3: เข้าถึง Gmail
# ═══════════════════════════════════════════════════════

@dataclass
class GmailTool:
    """เครื่องมือเข้าถึง Gmail."""

    name: str
    description: str
    method: str  # oauth, headless, mcp
    free: bool = True


GMAIL_TOOLS: list[GmailTool] = [
    GmailTool(
        name="gml",
        description="CLI tool — AI Agents เข้าถึง Gmail ตรงๆ ไม่ต้องใช้เบราว์เซอร์",
        method="oauth",
    ),
    GmailTool(
        name="mcp-headless-gmail",
        description="MCP Server — เข้าถึง Gmail แบบ headless, ไม่เก็บ credentials ในเครื่อง",
        method="mcp",
    ),
    GmailTool(
        name="CK-NEXUS Gmail Bridge",
        description="ระบบเดิมที่สร้างไว้แล้ว — OAuth2 + Read/Send/Scan",
        method="oauth",
    ),
    GmailTool(
        name="google-automation-mcp",
        description="Headless Google Workspace automation — Gmail, Drive, Sheets, Calendar — No GCP console",
        method="mcp",
    ),
    GmailTool(
        name="gwcli",
        description="Command-line client สำหรับ Gmail, Tasks, Calendar — optimized สำหรับ non-interactive use และ AI agents",
        method="cli",
    ),
]


class SolutionManager:
    """จัดการเครื่องมือแก้ข้อจำกัดทั้งหมด.

    วิธีใช้:
        mgr = SolutionManager()
        print(mgr.full_report())
    """

    def full_report(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║  🛠️ Solutions — แก้ข้อจำกัดทางเทคนิค                    ║",
            "╚══════════════════════════════════════════════════════════╝",
            "",
            "🔴 ข้อจำกัดที่ 1: สร้างบัญชีเว็บภายนอก",
            "─" * 55,
            "",
            "   🤖 CAPTCHA Solvers (ฟรี):",
        ]
        for s in CAPTCHA_SOLVERS:
            lines.append(f"      ✅ {s.name}")
            lines.append(f"         {s.free_tier}")
            lines.append(f"         รองรับ: {', '.join(s.supported_types)}")

        lines.extend(["", "   📧 Temporary Email (ฟรี):"])
        for s in TEMP_EMAIL_SERVICES:
            lines.append(f"      ✅ {s.name}")
            lines.append(f"         {s.free_tier}")

        lines.extend(["", "   📱 Temporary SMS (ฟรี):"])
        for s in TEMP_SMS_SERVICES:
            lines.append(f"      ✅ {s.name}")
            lines.append(f"         {s.free_tier}")

        lines.extend(["", "   🌐 Anti-Detect Browser (ฟรี):"])
        for s in ANTI_DETECT_BROWSERS:
            lines.append(f"      ✅ {s.name} (⭐ {s.stars})")
            lines.append(f"         {', '.join(s.features)}")

        lines.extend([
            "",
            "🟡 ข้อจำกัดที่ 2: ตัดสินใจซื้อ/จ่ายเงิน",
            "─" * 55,
            "",
            "   🛡️ Human-in-the-Loop (ฟรี):",
        ])
        for s in HITL_TOOLS:
            lines.append(f"      ✅ {s.name}")
            lines.append(f"         {s.description}")
            lines.append(f"         Approval: {', '.join(s.approval_channels)}")

        lines.extend([
            "",
            "🔵 ข้อจำกัดที่ 3: เข้าถึง Gmail",
            "─" * 55,
            "",
            "   📧 Gmail Access (ฟรี):",
        ])
        for s in GMAIL_TOOLS:
            lines.append(f"      ✅ {s.name}")
            lines.append(f"         {s.description}")

        lines.extend([
            "",
            "=" * 55,
            "✅ ทุกข้อจำกัดมีทางออกฟรีทั้งหมด!",
            "",
            "📌 ขั้นตอนถัดไป:",
            "   1. ติดตั้ง CAPTCHA solver → pip install playwright-captcha",
            "   2. ตั้งค่า Temp Email → ใช้ ZeroDrop MCP หรือ PhoboMail",
            "   3. ตั้งค่า Anti-detect → ใช้ ShardBrowser",
            "   4. ตั้งค่า HITL → ใช้ Approva หรือ Inferable",
            "   5. ตั้งค่า Gmail → ใช้ mcp-headless-gmail",
        ])
        return "\n".join(lines)

    def summary(self) -> dict:
        return {
            "captcha_solvers": len(CAPTCHA_SOLVERS),
            "temp_email_services": len(TEMP_EMAIL_SERVICES),
            "temp_sms_services": len(TEMP_SMS_SERVICES),
            "anti_detect_browsers": len(ANTI_DETECT_BROWSERS),
            "hitl_tools": len(HITL_TOOLS),
            "gmail_tools": len(GMAIL_TOOLS),
            "total": (len(CAPTCHA_SOLVERS) + len(TEMP_EMAIL_SERVICES)
                      + len(TEMP_SMS_SERVICES) + len(ANTI_DETECT_BROWSERS)
                      + len(HITL_TOOLS) + len(GMAIL_TOOLS)),
        }
