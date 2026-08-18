"""CK-NEXUS Assistant Registry — 30 AI assistants from free-tier websites.

Each assistant wraps a real AI service with a unified interface.
Keys are stored via environment variables or the credential vault.
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from urllib.request import Request, urlopen


class AssistantCategory(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    MUSIC = "music"
    CODE = "code"
    WRITING = "writing"
    SEARCH = "search"
    DESIGN = "design"
    PRODUCTIVITY = "productivity"
    AVATAR = "avatar"


class AssistantTier(StrEnum):
    FREE = "free"
    FREEMIUM = "freemium"


@dataclass(frozen=True, slots=True)
class Assistant:
    name: str
    slug: str
    url: str
    api_url: str
    env_key: str
    category: AssistantCategory
    tier: AssistantTier
    description: str
    icon: str
    capabilities: tuple[str, ...] = ()
    needs_key: bool = True


ASSISTANTS: list[Assistant] = [
    # ── IMAGE ──
    Assistant(
        name="Raphael AI", slug="raphael", url="https://raphael.ai",
        api_url="https://raphael.ai/api/generate", env_key="RAPHAEL_API_KEY",
        category=AssistantCategory.IMAGE, tier=AssistantTier.FREE,
        description="Free unlimited AI image generation, quality rivals Midjourney",
        icon="🎨", capabilities=("image-generation", "unlimited"),
    ),
    Assistant(
        name="Krea AI", slug="krea", url="https://krea.ai",
        api_url="https://krea.ai/api/generate", env_key="KREA_API_KEY",
        category=AssistantCategory.IMAGE, tier=AssistantTier.FREE,
        description="Real-time AI image generation, draws as you go",
        icon="🖼️", capabilities=("image-generation", "realtime"),
    ),
    Assistant(
        name="Magnific AI", slug="magnific", url="https://magnific.ai",
        api_url="https://magnific.ai/api/upscale", env_key="MAGNIFIC_API_KEY",
        category=AssistantCategory.IMAGE, tier=AssistantTier.FREEMIUM,
        description="AI unlimited image upscaling, details auto-filled",
        icon="🔬", capabilities=("image-upscale", "detail-fill"),
    ),
    Assistant(
        name="Clipdrop", slug="clipdrop", url="https://clipdrop.co",
        api_url="https://clipdrop.co/api/v1", env_key="CLIPDROP_API_KEY",
        category=AssistantCategory.IMAGE, tier=AssistantTier.FREEMIUM,
        description="AI one-click background removal/lighting fix/erasure",
        icon="✂️", capabilities=("bg-remove", "relight", "erase"),
    ),
    Assistant(
        name="Remove.bg", slug="removebg", url="https://remove.bg",
        api_url="https://api.remove.bg/v1.0", env_key="REMOVEBG_API_KEY",
        category=AssistantCategory.IMAGE, tier=AssistantTier.FREEMIUM,
        description="One-click AI background removal, 1-second output",
        icon="🗑️", capabilities=("bg-remove",),
    ),
    Assistant(
        name="Cleanup.pictures", slug="cleanup", url="https://cleanup.pictures",
        api_url="https://cleanup.pictures/api", env_key="CLEANUP_API_KEY",
        category=AssistantCategory.IMAGE, tier=AssistantTier.FREEMIUM,
        description="AI erases any object from photos",
        icon="🧹", capabilities=("object-erase",),
    ),
    # ── VIDEO ──
    Assistant(
        name="RunwayML", slug="runway", url="https://runwayml.com",
        api_url="https://api.runwayml.com/v1", env_key="RUNWAY_API_KEY",
        category=AssistantCategory.VIDEO, tier=AssistantTier.FREEMIUM,
        description="AI video generation pioneer, free Gen-3 trial",
        icon="🎬", capabilities=("video-generation", "gen3"),
    ),
    Assistant(
        name="Kling AI", slug="kling", url="https://klingai.kuaishou.com",
        api_url="https://klingai.kuaishou.com/api", env_key="KLING_API_KEY",
        category=AssistantCategory.VIDEO, tier=AssistantTier.FREE,
        description="Kuaishou Keling AI, smoothest Chinese video generation",
        icon="🎥", capabilities=("video-generation", "smooth"),
    ),
    Assistant(
        name="Opus.pro", slug="opus", url="https://opus.pro",
        api_url="https://opus.pro/api", env_key="OPUS_API_KEY",
        category=AssistantCategory.VIDEO, tier=AssistantTier.FREEMIUM,
        description="AI short video editing, auto-finds highlight clips",
        icon="🎞️", capabilities=("video-edit", "highlights"),
    ),
    # ── AVATAR / TALKING HEAD ──
    Assistant(
        name="D-ID", slug="did", url="https://d-id.com",
        api_url="https://api.d-id.com", env_key="DID_API_KEY",
        category=AssistantCategory.AVATAR, tier=AssistantTier.FREEMIUM,
        description="One photo + one audio = talking digital human",
        icon="🧑", capabilities=("talking-head", "photo-to-video"),
    ),
    Assistant(
        name="SadTalker", slug="sadtalker", url="https://sadtalker.ai",
        api_url="https://sadtalker.ai/api", env_key="SADTALKER_API_KEY",
        category=AssistantCategory.AVATAR, tier=AssistantTier.FREE,
        description="Turns static photos into talking videos",
        icon="🗣️", capabilities=("talking-head", "photo-animate"),
    ),
    # ── VOICE ──
    Assistant(
        name="ElevenLabs", slug="elevenlabs", url="https://elevenlabs.io",
        api_url="https://api.elevenlabs.io/v1", env_key="ELEVENLABS_API_KEY",
        category=AssistantCategory.VOICE, tier=AssistantTier.FREEMIUM,
        description="AI voice cloning, mimics any voice in 5 seconds",
        icon="🎙️", capabilities=("tts", "voice-clone", "speech-to-speech"),
    ),
    # ── MUSIC ──
    Assistant(
        name="Suno", slug="suno", url="https://suno.com",
        api_url="https://api.suno.ai/v1", env_key="SUNO_API_KEY",
        category=AssistantCategory.MUSIC, tier=AssistantTier.FREEMIUM,
        description="Input lyrics to auto-generate full songs",
        icon="🎵", capabilities=("music-generation", "lyrics-to-song"),
    ),
    Assistant(
        name="Musiio", slug="musiio", url="https://musiio.com",
        api_url="https://api.musiio.com/v1", env_key="MUSIIO_API_KEY",
        category=AssistantCategory.MUSIC, tier=AssistantTier.FREEMIUM,
        description="AI music tagging + recommendations",
        icon="🎶", capabilities=("music-tag", "recommend"),
    ),
    # ── CODE ──
    Assistant(
        name="Cursor", slug="cursor", url="https://cursor.com",
        api_url="https://api.cursor.com/v1", env_key="CURSOR_API_KEY",
        category=AssistantCategory.CODE, tier=AssistantTier.FREEMIUM,
        description="AI code writing, free quota enough for daily use",
        icon="⌨️", capabilities=("code-generation", "code-edit"),
    ),
    Assistant(
        name="Bolt.new", slug="bolt", url="https://bolt.new",
        api_url="https://bolt.new/api", env_key="BOLT_API_KEY",
        category=AssistantCategory.CODE, tier=AssistantTier.FREEMIUM,
        description="Build websites by talking, zero code",
        icon="⚡", capabilities=("website-builder", "no-code"),
    ),
    Assistant(
        name="v0.app", slug="v0", url="https://v0.app",
        api_url="https://v0.dev/api", env_key="V0_API_KEY",
        category=AssistantCategory.CODE, tier=AssistantTier.FREEMIUM,
        description="Vercel AI frontend generator, description becomes page",
        icon="📐", capabilities=("frontend-gen", "ui-to-code"),
    ),
    Assistant(
        name="Replit", slug="replit", url="https://replit.com",
        api_url="https://api.replit.com/v1", env_key="REPLIT_API_KEY",
        category=AssistantCategory.CODE, tier=AssistantTier.FREEMIUM,
        description="Code in browser + AI assistance + one-click deploy",
        icon="🔄", capabilities=("code-gen", "deploy", "ai-assist"),
    ),
    # ── WRITING ──
    Assistant(
        name="Notion AI", slug="notion", url="https://notion.com/product/ai",
        api_url="https://api.notion.com/v1", env_key="NOTION_API_KEY",
        category=AssistantCategory.WRITING, tier=AssistantTier.FREEMIUM,
        description="Notion AI for writing, summarizing, translating",
        icon="📝", capabilities=("writing", "summarize", "translate"),
    ),
    Assistant(
        name="Jasper AI", slug="jasper", url="https://jasper.ai/free",
        api_url="https://api.jasper.ai/v1", env_key="JASPER_API_KEY",
        category=AssistantCategory.WRITING, tier=AssistantTier.FREEMIUM,
        description="AI writing assistant, free version enough for daily use",
        icon="✍️", capabilities=("copywriting", "blog", "ads"),
    ),
    # ── DESIGN ──
    Assistant(
        name="Napkin AI", slug="napkin", url="https://napkin.ai",
        api_url="https://napkin.ai/api", env_key="NAPKIN_API_KEY",
        category=AssistantCategory.DESIGN, tier=AssistantTier.FREEMIUM,
        description="Paste text to auto-generate infographics",
        icon="📊", capabilities=("infographic", "text-to-visual"),
    ),
    Assistant(
        name="Gamma App", slug="gamma", url="https://gamma.app",
        api_url="https://gamma.app/api", env_key="GAMMA_API_KEY",
        category=AssistantCategory.DESIGN, tier=AssistantTier.FREEMIUM,
        description="AI one-click PPT generation, say goodbye to PPT hell",
        icon="📽️", capabilities=("ppt-generation", "slides"),
    ),
    Assistant(
        name="Uizard", slug="uizard", url="https://uizard.io",
        api_url="https://uizard.io/api", env_key="UIZARD_API_KEY",
        category=AssistantCategory.DESIGN, tier=AssistantTier.FREEMIUM,
        description="Sketch a drawing, AI generates real webpage",
        icon="🎨", capabilities=("sketch-to-ui", "wireframe"),
    ),
    # ── SEARCH ──
    Assistant(
        name="Perplexity AI", slug="perplexity", url="https://perplexity.ai",
        api_url="https://api.perplexity.ai", env_key="PERPLEXITY_API_KEY",
        category=AssistantCategory.SEARCH, tier=AssistantTier.FREEMIUM,
        description="AI search engine, answers any question instantly + sources",
        icon="🔍", capabilities=("ai-search", "citations"),
    ),
    Assistant(
        name="Phind", slug="phind", url="https://phind.com",
        api_url="https://api.phind.com/v1", env_key="PHIND_API_KEY",
        category=AssistantCategory.SEARCH, tier=AssistantTier.FREEMIUM,
        description="Developer-exclusive AI search, code issues solved on search",
        icon="💡", capabilities=("dev-search", "code-solve"),
    ),
    # ── PRODUCTIVITY ──
    Assistant(
        name="Otter.ai", slug="otter", url="https://otter.ai",
        api_url="https://api.otter.ai/v1", env_key="OTTER_API_KEY",
        category=AssistantCategory.PRODUCTIVITY, tier=AssistantTier.FREEMIUM,
        description="Real-time meeting transcription, free 300 minutes monthly",
        icon="🦦", capabilities=("transcription", "meeting-notes"),
    ),
    # ── FACE / DEEPFAKE ──
    Assistant(
        name="Deepswap.ai", slug="deepswap", url="https://deepswap.ai",
        api_url="https://deepswap.ai/api", env_key="DEEPSWAP_API_KEY",
        category=AssistantCategory.VIDEO, tier=AssistantTier.FREEMIUM,
        description="AI face swap, 1-minute turnaround",
        icon="🎭", capabilities=("face-swap",),
    ),
    # ── AI CHAT (unified) ──
    Assistant(
        name="Poe", slug="poe", url="https://poe.com",
        api_url="https://api.poe.com/v1", env_key="POE_API_KEY",
        category=AssistantCategory.SEARCH, tier=AssistantTier.FREEMIUM,
        description="One site to use GPT-4o / Claude / Gemini",
        icon="🤖", capabilities=("multi-model", "chat"),
    ),
    Assistant(
        name="HuggingFace Spaces", slug="huggingface", url="https://huggingface.co/spaces",
        api_url="https://api-inference.huggingface.co", env_key="HUGGINGFACE_API_KEY",
        category=AssistantCategory.SEARCH, tier=AssistantTier.FREE,
        description="Open-source AI model free playground",
        icon="🤗", capabilities=("open-source", "playground"),
    ),
    Assistant(
        name="Claude AI", slug="claude", url="https://claude.ai",
        api_url="https://api.anthropic.com/v1", env_key="ANTHROPIC_API_KEY",
        category=AssistantCategory.SEARCH, tier=AssistantTier.FREEMIUM,
        description="Anthropic free AI assistant, top-tier long-text handling",
        icon="🏛️", capabilities=("chat", "long-text", "analysis"),
    ),
]


def list_assistants(category: str | None = None) -> list[dict[str, Any]]:
    result = ASSISTANTS
    if category:
        result = [a for a in result if a.category == category]
    return [
        {
            "name": a.name, "slug": a.slug, "url": a.url,
            "category": a.category, "tier": a.tier,
            "description": a.description, "icon": a.icon,
            "capabilities": list(a.capabilities),
            "has_key": bool(os.environ.get(a.env_key)),
            "env_key": a.env_key,
        }
        for a in result
    ]


def get_assistant(slug: str) -> Assistant | None:
    return next((a for a in ASSISTANTS if a.slug == slug), None)


def scan_assistants() -> list[dict[str, Any]]:
    results = []
    for a in ASSISTANTS:
        key = os.environ.get(a.env_key, "")
        results.append({
            "name": a.name, "slug": a.slug, "icon": a.icon,
            "category": a.category, "tier": a.tier,
            "has_key": bool(key),
            "key_preview": f"****{key[-4:]}" if len(key) > 8 else None,
            "env_key": a.env_key,
        })
    return results


def get_assistant_by_category(category: str) -> list[dict[str, Any]]:
    return list_assistants(category=category)


def get_categories() -> list[dict[str, Any]]:
    cats = {}
    for a in ASSISTANTS:
        if a.category not in cats:
            cats[a.category] = {"name": a.category, "count": 0, "icons": []}
        cats[a.category]["count"] += 1
        cats[a.category]["icons"].append(a.icon)
    return list(cats.values())
