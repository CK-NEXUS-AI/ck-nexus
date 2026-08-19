"""Ideas Expanded — แนวคิดขยายสำหรับ AI Agent ที่ทำได้จริง.

ครอบคลุม 12 หมวดหมู่ ที่ยังไม่ได้รวมใน solutions.py:
1. Free AI APIs & Models
2. Data Extraction & Scraping
3. Automation & Workflow
4. Database & Storage ฟรี
5. Deployment & Hosting ฟรี
6. Browser Automation ขั้นสูง
7. Content Creation (Image/Audio/Video)
8. Local AI Models (ไม่ต้องอินเทอร์เน็ต)
9. Multi-Agent Coordination
10. Security & Privacy Tools
11. Monitoring & Observability
12. Email & Communication ขั้นสูง
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Tool:
    """เครื่องมือหนึ่งตัว."""
    category: str
    name: str
    url: str
    free_tier: str
    features: tuple[str, ...] = ()
    use_case: str = ""
    requires_key: bool = False


IDEAS: list[Tool] = [
    # ═══ 1. FREE AI APIs & MODELS ═══
    Tool("ai", "Groq", "https://groq.com/", "ไม่จำกัด — เร็วสุด 42ms",
         ("fastest_inference", "openai_compatible"), "LLM ฟรีที่เร็วที่สุดในโลก", True),
    Tool("ai", "Google AI Studio", "https://aistudio.google.com/", "ไม่จำกัด — Gemini Flash",
         ("multimodal", "vision", "code_execution"), "LLM ฟรี + วิเคราะห์ภาพ", True),
    Tool("ai", "OpenRouter Free", "https://openrouter.ai/", "รวมหลายโมเดลฟรี",
         ("multi_model", "openai_compatible"), "ทางเลือกหลายโมเดลในที่เดียว", True),
    Tool("ai", "HuggingFace Inference", "https://huggingface.co/inference-api", "ไม่จำกัด — หลายร้อยโมเดล",
         ("code_generation", "embeddings", "summarization"), "โมเดล code + text + embeddings", True),
    Tool("ai", "Cerebras Inference", "https://cerebras.ai/", "ไม่จำกัด — เร็วมาก",
         ("fastest_inference", "openai_compatible"), "LLM เร็วเป็นอันดับ 2", True),
    Tool("ai", "SambaNova Free", "https://sambanova.ai/", "ไม่จำกัด — Llama 3",
         ("fast_inference", "enterprise_grade"), "LLM ระดับ enterprise ฟรี", True),
    Tool("ai", "Together AI Free", "https://together.ai/", "$1 credit ฟรี",
         ("fine_tuning", "openai_compatible"), "fine-tune โมเดลฟรี", True),
    Tool("ai", "Codeium", "https://codeium.com/", "ไม่จำกัด — VS Code/JetBrains",
         ("code_completion", "chat", "multi_language"), " autocomplete โค้ดฟรี", False),
    Tool("ai", "Tabby", "https://tabby.tabbyml.com/", "Self-hosted ฟรี 100%",
         ("self_hosted", "code_completion"), "LLM โค้ดที่รันในเครื่อง", False),

    # ═══ 2. DATA EXTRACTION & SCRAPING ═══
    Tool("scraping", "Crawl4AI", "https://github.com/unclecode/crawl4ai", "Open Source ฟรี",
         ("llm_friendly", "multi_source", "dynamic_js"), "ดึงเว็บ → ส่ง LLM วิเคราะห์", False),
    Tool("scraping", "Firecrawl", "https://firecrawl.dev/", "500 pages/เดือน ฟรี",
         ("screenshot", "structured_data", "metadata"), "ดึงเว็บ → ได้ structured data", True),
    Tool("scraping", "Spider Cloud", "https://spider.cloud/", "1,000 pages ฟรี",
         ("cloud_browser", "anti_bot", "auto_retry"), "ดึงเว็บที่บล็อกบอท", True),
    Tool("scraping", "ScraperAPI", "https://scraperapi.com/", "5,000 requests ฟรี",
         ("proxy_rotation", "js_rendering", "captcha"), "ดึงเว็บผ่าน proxy อัตโนมัติ", True),
    Tool("scraping", "ZenRows", "https://zenrows.com/", "1,000 requests ฟรี",
         ("anti_bot", "js_rendering", "auto_proxy"), "ดึงเว็บที่มี Cloudflare", True),
    Tool("scraping", "Exa AI", "https://exa.ai/", "1,000 requests/เดือน ฟรี",
         ("semantic_search", "contents_api"), "ค้นหา semantic → ดึงเนื้อหา", True),
    Tool("scraping", "Tavily", "https://tavily.com/", "1,000 requests/เดือน ฟรี",
         ("ai_optimized", "clean_content"), "ค้นหาสำหรับ AI โดยเฉพาะ", True),
    Tool("scraping", "Apify", "https://apify.com/", "49 computations/เดือน ฟรี",
         ("pre_built_actors", "web_scraping"), "actor สำเร็จรูป → ดึงข้อมูลหลายเว็บ", True),

    # ═══ 3. AUTOMATION & WORKFLOW ═══
    Tool("automation", "n8n Self-hosted", "https://n8n.io/", "Self-hosted ฟรี 100%",
         ("visual_workflow", "800+_integrations"), "workflow ลากวาง → เชื่อม 800+ แอป", False),
    Tool("automation", "Activepieces", "https://activepieces.com/", "Self-hosted ฟรี 100%",
         ("open_source", "ai_pieces"), "automation ฟรี + เชื่อม AI", False),
    Tool("automation", "Windmill", "https://windmill.dev/", "Self-hosted ฟรี 100%",
         ("scripts_as_apps", "flows"), "script กลายเป็น app อัตโนมัติ", False),
    Tool("automation", "Inngest", "https://www.inngest.com/", "1M steps/เดือน ฟรี",
         ("serverless", "cron", "fan_out"), "task หลายพันพร้อมกัน", True),
    Tool("automation", "Composio", "https://composio.dev/", "3 accounts ฟรี",
         ("200+_integrations", "managed_auth"), "เชื่อม AI กับ 200+ แอป", True),
    Tool("automation", "Temporal", "https://temporal.io/", "Self-hosted ฟรี 100%",
         ("durable_workflow", "retry", "saga"), "workflow ทนทาน → ไม่หายแม้ล่ม", False),

    # ═══ 4. DATABASE & STORAGE ฟรี ═══
    Tool("database", "Neon Postgres", "https://neon.tech/", "0.5 GB ฟรี",
         ("serverless", "branching", "auto_scale"), "Postgres ฟรี + auto-scale", False),
    Tool("database", "Supabase Free", "https://supabase.com/", "500 MB + 50K MAU ฟรี",
         ("auth", "realtime", "edge_functions"), "Firebase ทางเลือกที่ open-source", False),
    Tool("database", "PlanetScale Free", "https://planetscale.com/", "5 GB ฟรี",
         ("mysql", "branching", "auto_scale"), "MySQL ฟรี + branching", False),
    Tool("database", "Turso", "https://turso.tech/", "500 databases ฟรี",
         ("sqlite_edge", "embedded_replica"), "SQLite กระจาย → edge ready", False),
    Tool("database", "Upstash Redis", "https://upstash.com/", "10K commands/วัน ฟรี",
         ("serverless_redis", "rate_limiting"), "Redis ฟรี → cache + queue", False),
    Tool("database", "Cloudflare R2", "https://www.cloudflare.com/r2/", "10 GB ฟรี ไม่มี egress fee",
         ("s3_compatible", "no_egress_fee"), "เก็บไฟล์ฟรี → ไม่เสียค่าส่งออก", False),
    Tool("database", "Vercel Blob", "https://vercel.com/", "100 GB ฟรี",
         ("edge_storage", "cdn"), "เก็บไฟล์ edge → เร็ว + CDN", False),
    Tool("database", "GitHub Gist", "https://gist.github.com/", "ไม่จำกัด ฟรี",
         ("versioned", "public_private"), "เก็บ code/config ฟรี + version", False),
    Tool("database", "JSON Bin", "https://jsonbin.io/", "10K requests/เดือน ฟรี",
         ("rest_api", "versioning"), "JSON storage ฟรี via API", False),

    # ═══ 5. DEPLOYMENT & HOSTING ฟรี ═══
    Tool("deployment", "Vercel", "https://vercel.com/", "ไม่จำกัด สำหรับ hobby",
         ("serverless", "edge", "analytics"), "Deploy Next.js/React ฟรี", False),
    Tool("deployment", "Netlify", "https://www.netlify.com/", "100 GB bandwidth ฟรี",
         ("serverless", "forms", "identity"), "Deploy static + serverless ฟรี", False),
    Tool("deployment", "Cloudflare Pages", "https://pages.cloudflare.com/", "ไม่จำกัด ฟรี",
         ("edge", "unlimited_bandwidth"), "Deploy ฟรี + bandwidth ไม่จำกัด", False),
    Tool("deployment", "Railway Free", "https://railway.com/", "$5 credit/เดือน ฟรี",
         ("docker", "databases", "cron"), "Deploy Docker + DB ฟรี", True),
    Tool("deployment", "Fly.io Free", "https://fly.io/", "3 shared VMs ฟรี",
         ("docker", "edge", "wireguard"), "Deploy Docker → edge ทั่วโลก", False),
    Tool("deployment", "Render Free", "https://render.com/", "Web Service ฟรี",
         ("docker", "postgres", "cron"), "Deploy + DB + cron ฟรี", False),
    Tool("deployment", "Koyeb Free", "https://www.koyeb.com/", "1 Micro ฟรี",
         ("serverless", "edge", "gpu"), "Deploy ฟรี + GPU option", False),
    Tool("deployment", "Deno Deploy", "https://deno.com/deploy", "ไม่จำกัด สำหรับ hobby",
         ("serverless", "edge", "typescript"), "Deploy Deno/TypeScript ฟรี", False),

    # ═══ 6. BROWSER AUTOMATION ขั้นสูง ═══
    Tool("browser", "Playwright", "https://playwright.dev/", "Open Source ฟรี",
         ("multi_browser", "auto_wait", "network"), "browser automation ที่ดีที่สุด", False),
    Tool("browser", "Browserless", "https://www.browserless.io/", "100 sessions ฟรี",
         ("headless_chrome", "pdf_generation", "screenshot"), "headless browser ผ่าน API", True),
    Tool("browser", "Puppeteer", "https://pptr.dev/", "Open Source ฟรี",
         ("chrome_automation", "screenshot", "pdf"), "Chrome automation ฟรี", False),
    Tool("browser", "Helium", "https://github.com/mherrmann/helium", "Open Source ฟรี",
         ("selenium_simplified", "readable"), "Selenium ที่อ่านง่าย → เขียน bot ง่าย", False),
    Tool("browser", "DrissionPage", "https://github.com/g1879/DrissionPage", "Open Source ฟรี",
         ("no_webdriver", "bypass_detection"), "Chrome ไม่ผ่าน webdriver → หลบ detection", False),

    # ═══ 7. CONTENT CREATION ═══
    Tool("content", "Stable Diffusion XL", "https://stability.ai/", "Self-hosted ฟรี",
         ("image_generation", "inpainting"), "สร้างภาพ AI ฟรีในเครื่อง", False),
    Tool("content", "Bark (Suno)", "https://github.com/suno-ai/bark", "Self-hosted ฟรี",
         ("text_to_speech", "sound_effects"), "สร้างเสียง + เสียงเอฟเฟกต์", False),
    Tool("content", "Whisper (OpenAI)", "https://github.com/openai/whisper", "Self-hosted ฟรี",
         ("speech_to_text", "multilingual"), "แปลงเสียงเป็นข้อความ 99+ ภาษา", False),
    Tool("content", "Coqui TTS", "https://github.com/coqui-ai/TTS", "Self-hosted ฟรี",
         ("voice_cloning", "multilingual"), "clone เสียง → สร้างเสียงใหม่", False),
    Tool("content", "FFmpeg", "https://ffmpeg.org/", "Open Source ฟรี",
         ("video_editing", "transcoding"), "ตัดต่อ/แปลงวิดีโอ + เสียง", False),
    Tool("content", "ImageMagick", "https://imagemagick.org/", "Open Source ฟรี",
         ("image_processing", "batch_edit"), "จัดการภาพ batch → resize/crop/convert", False),

    # ═══ 8. LOCAL AI MODELS ═══
    Tool("local_ai", "Ollama", "https://ollama.com/", "Self-hosted ฟรี 100%",
         ("llama3", "codellama", "mistral", "qwen"), "LLM ในเครื่อง → ไม่ต้องเน็ต", False),
    Tool("local_ai", "LM Studio", "https://lmstudio.ai/", "Self-hosted ฟรี 100%",
         ("gui", "multi_model", "openai_compatible"), "LLM มี GUI → drag-drop model", False),
    Tool("local_ai", "Jan", "https://jan.ai/", "Self-hosted ฟรี 100%",
         ("gui", "offline", "extensions"), "LLM offline แบบ ChatGPT", False),
    Tool("local_ai", "GPT4All", "https://gpt4all.io/", "Self-hosted ฟรี 100%",
         ("gui", "cpu_only", "privacy"), "LLM รันบน CPU ได้ → ไม่ต้อง GPU", False),
    Tool("local_ai", "llama.cpp", "https://github.com/ggerganov/llama.cpp", "Open Source ฟรี",
         ("cpu_inference", "quantized", "metal"), "LLM เร็ว → รันบน CPU/Mac", False),
    Tool("local_ai", "vLLM", "https://github.com/vllm-project/vllm", "Open Source ฟรี",
         ("high_throughput", "gpu_optimized"), "LLM server เร็ว → หลาย request พร้อมกัน", False),
    Tool("local_ai", "MLX (Apple)", "https://github.com/ml-explore/mlx", "Open Source ฟรี",
         ("apple_silicon", "optimized"), "LLM บน Apple Silicon → เร็วสุด", False),

    # ═══ 9. MULTI-AGENT COORDINATION ═══
    Tool("multi_agent", "LangGraph", "https://github.com/langchain-ai/langgraph", "Open Source ฟรี",
         ("state_graph", "persistence", "human_in_loop"), "สร้าง agent workflow → state machine", False),
    Tool("multi_agent", "CrewAI", "https://github.com/crewAIInc/crewAI", "Open Source ฟรี",
         ("role_based", "memory", "delegation"), "สร้างทีม AI → แบ่งงาน + จำบทบาท", False),
    Tool("multi_agent", "AutoGen", "https://github.com/microsoft/autogen", "Open Source ฟรี",
         ("multi_agent_chat", "code_execution", "reflection"), "หลาย agent คุยกัน → แก้ปัญหา", False),
    Tool("multi_agent", "Swarm", "https://github.com/openai/swarm", "Open Source ฟรี",
         ("lightweight", "handoff", "routine"), "agent เปลี่ยนบทบาท → ส่งต่องาน", False),
    Tool("multi_agent", "OpenClaw", "https://github.com/openclaw", "Open Source ฟรี",
         ("local_first", "skill_discovery", "multi_model"), "agent ที่เรียนรู้ skill ใหม่เอง", False),

    # ═══ 10. SECURITY & PRIVACY ═══
    Tool("security", "Bandit", "https://bandit.readthedocs.io/", "Open Source ฟรี",
         ("python_security", "ast_analysis"), "สแกนโค้ด Python → หาช่องโหว่", False),
    Tool("security", "Semgrep", "https://semgrep.dev/", "Community ฟรี",
         ("multi_language", "custom_rules"), "สแกนโค้ดหลายภาษา → custom pattern", False),
    Tool("security", "Gitleaks", "https://github.com/gitleaks/gitleaks", "Open Source ฟรี",
         ("secret_detection", "git_history"), "ตรวจ secret ใน git → ป้องกัน leak", False),
    Tool("security", "Trivy", "https://trivy.dev/", "Open Source ฟรี",
         ("container_scan", "vuln_db"), "สแกน Docker image → หา vulnerability", False),
    Tool("security", "Vault (HashiCorp)", "https://www.vaultproject.io/", "Self-hosted ฟรี",
         ("secret_management", "dynamic_secrets"), "เก็บ secret แบบ enterprise → dynamic key", False),

    # ═══ 11. MONITORING & OBSERVABILITY ═══
    Tool("monitoring", "Uptime Kuma", "https://uptime.kuma.me/", "Self-hosted ฟรี",
         ("status_page", "notification", "multi_protocol"), "monitoring ฟรี → แจ้งเตือน 100+ ช่องทาง", False),
    Tool("monitoring", "Grafana + Prometheus", "https://grafana.com/", "Self-hosted ฟรี",
         ("dashboard", "alerting", "metrics"), "dashboard + metrics ฟรี", False),
    Tool("monitoring", "Better Uptime", "https://betterstack.com/", "10 monitors ฟรี",
         ("status_page", "incident"), "monitoring + status page สวย", True),
    Tool("monitoring", "Sentry Free", "https://sentry.io/", "5K errors/เดือน ฟรี",
         ("error_tracking", "performance"), "track error + performance ฟรี", True),
    Tool("monitoring", "Logtail (BetterStack)", "https://logtail.com/", "1 GB/เดือน ฟรี",
         ("structured_logs", "search"), "log management ฟรี", True),

    # ═══ 12. EMAIL & COMMUNICATION ขั้นสูง ═══
    Tool("email", "Resend Free", "https://resend.com/", "3K emails/เดือน ฟรี",
         ("transactional", "react_email"), "ส่ง email ฟรี → ออกแบบสวย", True),
    Tool("email", "SendGrid Free", "https://sendgrid.com/", "100 emails/วัน ฟรี",
         ("marketing", "transactional", "analytics"), "ส่ง email + track ฟรี", True),
    Tool("email", "Mailgun Free", "https://www.mailgun.com/", "1K emails/เดือน ฟรี",
         ("validation", "routing"), "ส่ง email + ตรวจ validity", True),
    Tool("email", "Postmark Free", "https://postmarkapp.com/", "100 emails/เดือน ฟรี",
         ("transactional", "fast_delivery"), "transactional email เร็ว + น่าเชื่อถือ", True),
    Tool("email", "EmailOctopus Free", "https://emailoctopus.com/", "500 subscribers ฟรี",
         ("marketing", "automation"), "email marketing ฟรี 500 คน", True),

    # ═══ 13. ANYCLAW ECOSYSTEM ═══
    Tool("anyclaw", "fastclaw-ai/anyclaw", "https://github.com/fastclaw-ai/anyclaw", "Open Source ฟรี",
         ("universal_tool_adapter", "mcp_server", "cli"), "เปลี่ยน API/เว็บ/สคริปต์เป็นเครื่องมือ AI", False),
    Tool("anyclaw", "paean-ai/anyclaw", "https://github.com/paean-ai/anyclaw", "Open Source ฟรี",
         ("web_frontend", "cloud_relay", "no_port_forwarding"), "Web Frontend เชื่อม Local AI ผ่าน Cloud", False),
    Tool("anyclaw", "AnyCrawl MCP Server", "https://anycrawl.dev/", "1,500 credits ฟรี",
         ("web_scraping", "crawl", "serp"), "MCP Server สำหรับ Web Scraping", True),
    Tool("anyclaw", "OpenClaw Skills Directory", "https://openclaw.ai/", "ฟรี — 5,798+ สกิล",
         ("skill_discovery", "automation", "community"), "คลังสกิลชุมชน 5,798+ ตัว", False),
    Tool("anyclaw", "AnyClaw Android App", "https://openclaw.ai/", "ฟรี — 5-in-1 AI Coding",
         ("multi_agent_routing", "no_root", "foreground_service"), "5 AI Coding Agents ในแอป Android", False),
    Tool("anyclaw", "KeyID.ai", "https://keyid.ai/", "1,000 accounts ฟรี",
         ("email_infrastructure", "phone_number", "verification"), "AI Agent มี email + phone + verification ใน API เดียว", True),
    Tool("anyclaw", "@chronary/agent-init", "https://github.com/chronary", "Open Source ฟรี",
         ("agent_bootstrap", "account_creation"), "Bootstrap สำหรับ AI agents บน Chronary", False),
    Tool("anyclaw", "freeAgentIdentity", "https://github.com/freeAgentIdentity", "Open Source ฟรี",
         ("multi_threaded", "chatgpt_accounts"), "Multi-threaded auto-register ChatGPT free accounts", False),
    Tool("anyclaw", "turb-gpt-free-register", "https://github.com/turb-gpt", "Open Source ฟรี",
         ("playwright", "cloakbrowser", "registration"), "ChatGPT/OpenAI account registration อัตโนมัติ", False),

]


def get_by_category(category: str) -> list[Tool]:
    """ดึงเครื่องมือตามหมวดหมู่."""
    return [t for t in IDEAS if t.category == category]


def get_free_no_key() -> list[Tool]:
    """ดึงเครื่องมือที่ฟรีและไม่ต้องใช้ key."""
    return [t for t in IDEAS if not t.requires_key]


def get_all_categories() -> dict[str, int]:
    """นับจำนวนเครื่องมือในแต่ละหมวด."""
    cats: dict[str, int] = {}
    for t in IDEAS:
        cats[t.category] = cats.get(t.category, 0) + 1
    return cats


def full_report() -> str:
    """รายงานทั้งหมด."""
    cats = {
        "ai": "🤖 Free AI APIs & Models",
        "scraping": "🌐 Data Extraction & Scraping",
        "automation": "⚙️ Automation & Workflow",
        "database": "💾 Database & Storage ฟรี",
        "deployment": "🚀 Deployment & Hosting ฟรี",
        "browser": "🖥️ Browser Automation ขั้นสูง",
        "content": "🎨 Content Creation",
        "local_ai": "🏠 Local AI Models",
        "multi_agent": "👥 Multi-Agent Coordination",
        "security": "🛡️ Security & Privacy",
        "monitoring": "📊 Monitoring & Observability",
        "email": "📧 Email & Communication ขั้นสูง",
    "anyclaw": "🐾 AnyClaw Ecosystem",
    "advanced_ai": "🧠 Advanced AI Capabilities",
    }
    lines = [
        "╔══════════════════════════════════════════════════════════════╗",
        "║  💡 Ideas Expanded — แนวคิดขยายสำหรับ AI Agent                ║",
        "╚══════════════════════════════════════════════════════════════╝",
        "",
        f"📊 รวม {len(IDEAS)} เครื่องมือ ใน {len(cats)} หมวดหมู่",
        f"🆓 ฟรีไม่ต้อง Key: {len(get_free_no_key())} เครื่องมือ",
        "",
    ]
    for cat_key, cat_label in cats.items():
        tools = get_by_category(cat_key)
        lines.append(f"{cat_label} ({len(tools)} ตัว)")
        lines.append("─" * 55)
        for t in tools:
            free_tag = "🆓" if not t.requires_key else "🔑"
            lines.append(f"  {free_tag} {t.name}")
            lines.append(f"     {t.free_tier}")
            if t.use_case:
                lines.append(f"     → {t.use_case}")
        lines.append("")
    return "\n".join(lines)




if __name__ == "__main__":
    print(full_report())
