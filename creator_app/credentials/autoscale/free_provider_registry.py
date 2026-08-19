"""Free Provider Registry — รวม AI/API provider ฟรีทั้งหมด.

จัดเก็บข้อมูล provider ฟรี + วิธีสร้าง key + quota + endpoint
เป็น central reference สำหรับระบบ auto-provision
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FreeProvider:
    """ข้อมูล provider ฟรีหนึ่งราย."""

    name: str
    display_name: str
    category: str  # llm, email, search, storage, automation, etc.
    signup_url: str
    api_endpoint: str
    free_quota: str
    rate_limit: str = ""
    strengths: tuple[str, ...] = ()
    key_env_var: str = ""
    auto_provisionable: bool = False
    api_key_format: str = ""  # regex-like pattern for validation
    notes: str = ""


# ═══════════════════════════════════════════════════════
# รายการ Provider ฟรี ทั้งหมด
# ═══════════════════════════════════════════════════════

FREE_PROVIDERS: list[FreeProvider] = [
    # ─── LLM / AI Models (ฟรี) ────────────────────────
    FreeProvider(
        name="openrouter_free",
        display_name="OpenRouter (Free Models)",
        category="llm",
        signup_url="https://openrouter.ai/keys",
        api_endpoint="https://openrouter.ai/api/v1",
        free_quota="ฟรี — models :free (Llama, Mistral, Gemma, Qwen)",
        rate_limit="20 req/min",
        strengths=("multi-model", "no credit card", "many free models"),
        key_env_var="OPENROUTER_API_KEY",
        api_key_format="sk-or-v1-",
    ),
    FreeProvider(
        name="groq_free",
        display_name="Groq (Free Tier)",
        category="llm",
        signup_url="https://console.groq.com/keys",
        api_endpoint="https://api.groq.com/openai/v1",
        free_quota="ฟรี — Llama 3, Mixtral, Gemma (เร็วมาก ~42ms)",
        rate_limit="30 req/min",
        strengths=("fastest", "free", "no credit card"),
        key_env_var="GROQ_API_KEY",
        api_key_format="gsk_",
    ),
    FreeProvider(
        name="google_ai_studio",
        display_name="Google AI Studio (Gemini)",
        category="llm",
        signup_url="https://aistudio.google.com/apikey",
        api_endpoint="https://generativelanguage.googleapis.com/v1beta",
        free_quota="ฟรี — Gemini 1.5 Flash/Pro (15 req/min, 1M tokens/day)",
        rate_limit="15 req/min",
        strengths=("very capable", "multimodal", "free generous quota"),
        key_env_var="GOOGLE_AI_STUDIO_KEY",
        api_key_format="AIza",
    ),
    FreeProvider(
        name="huggingface_free",
        display_name="Hugging Face Inference API",
        category="llm",
        signup_url="https://huggingface.co/settings/tokens",
        api_endpoint="https://api-inference.huggingface.co/models",
        free_quota="ฟรี — ทุก model, rate-limited",
        rate_limit="varies by model",
        strengths=("all open-source models", "no credit card"),
        key_env_var="HF_TOKEN",
        api_key_format="hf_",
    ),
    FreeProvider(
        name="ollama_local",
        display_name="Ollama (Local / ฟรี 100%)",
        category="llm",
        signup_url="https://ollama.ai/download",
        api_endpoint="http://localhost:11434/v1",
        free_quota="ฟรี 100% — รันในเครื่อง ไม่จำกัด",
        rate_limit="ไม่จำกัด (ขึ้นกับ hardware)",
        strengths=("offline", "unlimited", "private", "no api key needed"),
        key_env_var="OLLAMA_BASE_URL",
        notes="ติดตั้ง ollama แล้วรัน: ollama pull llama3",
    ),
    FreeProvider(
        name="together_free",
        display_name="Together AI (Free Credits)",
        category="llm",
        signup_url="https://api.together.xyz/settings/api-keys",
        api_endpoint="https://api.together.xyz/v1",
        free_quota="ฟรี $1 credit สำหรับ signup ใหม่",
        rate_limit="varies",
        strengths=("many open-source models", "free credits"),
        key_env_var="TOGETHER_API_KEY",
        api_key_format="",
    ),
    FreeProvider(
        name="deepseek_free",
        display_name="DeepSeek (Free API)",
        category="llm",
        signup_url="https://platform.deepseek.com/api_keys",
        api_endpoint="https://api.deepseek.com",
        free_quota="ฟรี — DeepSeek-V3, DeepSeek-Coder",
        rate_limit="varies",
        strengths=("coding", "reasoning", "very cheap"),
        key_env_var="DEEPSEEK_API_KEY",
        api_key_format="sk-",
    ),

    # ─── Email / Communication (ฟรี) ───────────────────
    FreeProvider(
        name="gmail_oauth",
        display_name="Gmail (OAuth2)",
        category="email",
        signup_url="https://console.cloud.google.com/apis/credentials",
        api_endpoint="https://gmail.googleapis.com/gmail/v1",
        free_quota="ฟรี — 250 คำขอ/วัน",
        rate_limit="250 req/day",
        strengths=("read/send email", "labels", "attachments"),
        key_env_var="GOOGLE_REFRESH_TOKEN",
        notes="สร้าง OAuth2 credentials ใน Google Cloud Console",
    ),
    FreeProvider(
        name="telegram_bot",
        display_name="Telegram Bot API",
        category="communication",
        signup_url="https://t.me/BotFather",
        api_endpoint="https://api.telegram.org",
        free_quota="ฟรี 100% — ไม่จำกัด",
        rate_limit="30 msg/sec",
        strengths=("send/receive messages", "inline keyboard", "webhook"),
        key_env_var="TELEGRAM_BOT_TOKEN",
        api_key_format=":",
    ),

    # ─── Search / Data (ฟรี) ──────────────────────────
    FreeProvider(
        name="serper",
        display_name="Serper.dev (Google Search)",
        category="search",
        signup_url="https://serper.dev/api-keys",
        api_endpoint="https://google.serper.dev/search",
        free_quota="ฟรี 2,500 queries (ครั้งเดียว)",
        rate_limit="100 req/day",
        strengths=("google search results", "news", "images"),
        key_env_var="SERPER_API_KEY",
    ),
    FreeProvider(
        name="tavily",
        display_name="Tavily (AI Search)",
        category="search",
        signup_url="https://tavily.com/#api",
        api_endpoint="https://api.tavily.com/search",
        free_quota="ฟรี 1,000 queries/เดือน",
        rate_limit="200 req/day",
        strengths=("optimized for AI", "structured results"),
        key_env_var="TAVILY_API_KEY",
    ),
    FreeProvider(
        name="jina",
        display_name="Jina AI (Reader/Embedding)",
        category="search",
        signup_url="https://jina.ai/api-key/",
        api_endpoint="https://r.jina.ai",
        free_quota="ฟรี 1M tokens",
        rate_limit="varies",
        strengths=("web reader", "embeddings", "reranker"),
        key_env_var="JINA_API_KEY",
    ),

    # ─── Storage / Database (ฟรี) ──────────────────────
    FreeProvider(
        name="supabase_free",
        display_name="Supabase (Free PostgreSQL)",
        category="database",
        signup_url="https://supabase.com/dashboard/project/new",
        api_endpoint="https://api.supabase.com",
        free_quota="ฟรี — 500MB database, 1GB storage, 50K MAU",
        rate_limit="varies",
        strengths=("postgres", "auth", "realtime", "edge functions"),
        key_env_var="SUPABASE_URL",
    ),
    FreeProvider(
        name="neon_free",
        display_name="Neon PostgreSQL (Free Tier)",
        category="database",
        signup_url="https://console.neon.tech",
        api_endpoint="https://console.neon.tech",
        free_quota="ฟรี — 0.5GB storage, 24/7 compute (inactive after 5min)",
        rate_limit="varies",
        strengths=("serverless postgres", "branching", "auto-suspend"),
        key_env_var="DATABASE_URL",
    ),
    FreeProvider(
        name="cloudflare_r2",
        display_name="Cloudflare R2 (Free Storage)",
        category="storage",
        signup_url="https://dash.cloudflare.com/sign-up",
        api_endpoint="https://<account_id>.r2.cloudflarestorage.com",
        free_quota="ฟรี — 10GB storage, 10M reads, 1M writes/เดือน",
        rate_limit="varies",
        strengths=("S3-compatible", "no egress fees"),
        key_env_var="R2_ACCOUNT_ID",
    ),

    # ─── Deployment (ฟรี) ─────────────────────────────
    FreeProvider(
        name="vercel_free",
        display_name="Vercel (Free Hosting)",
        category="deployment",
        signup_url="https://vercel.com/signup",
        api_endpoint="https://api.vercel.com",
        free_quota="ฟรี — 100GB bandwidth, serverless functions",
        rate_limit="varies",
        strengths=("nextjs", "edge functions", "analytics"),
        key_env_var="VERCEL_TOKEN",
    ),
    FreeProvider(
        name="render_free",
        display_name="Render (Free Web Services)",
        category="deployment",
        signup_url="https://dashboard.render.com/register",
        api_endpoint="https://api.render.com",
        free_quota="ฟรี — web services spin down after 15min inactivity",
        rate_limit="varies",
        strengths=("docker", "postgres", "redis"),
        key_env_var="RENDER_API_KEY",
    ),

    # ─── Automation / Integration (ฟรี) ────────────────
    FreeProvider(
        name="composio_free",
        display_name="Composio (App Integration)",
        category="automation",
        signup_url="https://app.composio.dev",
        api_endpoint="https://api.composio.dev",
        free_quota="ฟรี — connect multiple apps",
        rate_limit="varies",
        strengths=("connect 200+ apps", "tool calling"),
        key_env_var="COMPOSIO_API_KEY",
    ),

    # ─── Design (ฟรี) ─────────────────────────────────
    FreeProvider(
        name="canva_free",
        display_name="Canva (Free Design API)",
        category="design",
        signup_url="https://www.canva.com/developers/",
        api_endpoint="https://api.canva.com/rest/v1",
        free_quota="ฟรี — basic templates",
        rate_limit="varies",
        strengths=("templates", "design generation"),
        key_env_var="CANVA_API_KEY",
    ),

    # ─── Payment (ไม่ฟรีแต่ sandbox ฟรี) ──────────────
    FreeProvider(
        name="stripe_test",
        display_name="Stripe (Test Mode)",
        category="payment",
        signup_url="https://dashboard.stripe.com/register",
        api_endpoint="https://api.stripe.com/v1",
        free_quota="ฟรี — test mode ไม่คิดเงิน",
        rate_limit="100 req/sec",
        strengths=("payments", "subscriptions", "billing"),
        key_env_var="STRIPE_SECRET_KEY",
        api_key_format="sk_test_",
        notes="ใช้ sk_test_ เท่านั้น ไม่ใช่ sk_live_",
    ),
]


class FreeProviderRegistry:
    """คลัง provider ฟรีทั้งหมด.

    วิธีใช้:
        registry = FreeProviderRegistry()

        # ค้นหา provider ตาม category
        llm_providers = registry.by_category("llm")
        print(f"มี LLM ฟรี {len(llm_providers)} ราย")

        # สร้าง setup guide
        guide = registry.setup_guide("llm")
        print(guide)

        # ดูทั้งหมด
        all_free = registry.summary()
    """

    def __init__(self) -> None:
        self._providers = {p.name: p for p in FREE_PROVIDERS}

    def by_category(self, category: str) -> list[FreeProvider]:
        """ค้นหา provider ตาม category."""
        return [p for p in FREE_PROVIDERS if p.category == category]

    def by_name(self, name: str) -> FreeProvider | None:
        """ค้นหา provider ตามชื่อ."""
        return self._providers.get(name)

    def search(self, keyword: str) -> list[FreeProvider]:
        """ค้นหา provider ด้วย keyword."""
        keyword_lower = keyword.lower()
        return [
            p for p in FREE_PROVIDERS
            if keyword_lower in p.name.lower()
            or keyword_lower in p.display_name.lower()
            or keyword_lower in p.category.lower()
            or any(keyword_lower in s for s in p.strengths)
        ]

    def categories(self) -> list[str]:
        """ดู category ทั้งหมด."""
        return sorted(set(p.category for p in FREE_PROVIDERS))

    def setup_guide(self, category: str) -> str:
        """สร้าง setup guide สำหรับ category."""
        providers = self.by_category(category)
        if not providers:
            return f"ไม่พบ provider สำหรับ category: {category}"

        lines = [f"📋 Setup Guide: {category.upper()} (ฟรี)", "=" * 50]
        for i, p in enumerate(providers, 1):
            lines.append(f"\n{i}. {p.display_name}")
            lines.append(f"   🌐 สมัคร: {p.signup_url}")
            lines.append(f"   🔗 Endpoint: {p.api_endpoint}")
            lines.append(f"   📊 Quota: {p.free_quota}")
            if p.rate_limit:
                lines.append(f"   ⚡ Rate: {p.rate_limit}")
            if p.key_env_var:
                lines.append(f"   🔑 Env: {p.key_env_var}")
            if p.notes:
                lines.append(f"   📝 {p.notes}")
        return "\n".join(lines)

    def full_setup_guide(self) -> str:
        """สร้าง setup guide ครบทุก category."""
        lines = ["🚀 FREE API KEY SETUP GUIDE", "=" * 60]
        lines.append("รวมทุก provider ฟรีที่ใช้ได้ทันที\n")

        for category in self.categories():
            lines.append(self.setup_guide(category))
            lines.append("")

        lines.append("=" * 60)
        lines.append(f"📦 รวมทั้งหมด: {len(FREE_PROVIDERS)} providers")
        lines.append("💡 เริ่มจาก LLM ก่อน → แล้วค่อยเพิ่ม email, search, etc.")
        return "\n".join(lines)

    def summary(self) -> dict:
        """สรุป provider ทั้งหมด."""
        by_cat: dict[str, int] = {}
        for p in FREE_PROVIDERS:
            by_cat[p.category] = by_cat.get(p.category, 0) + 1
        return {
            "total": len(FREE_PROVIDERS),
            "by_category": by_cat,
            "categories": self.categories(),
        }
