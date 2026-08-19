"""Agent Registry — จัดการ AI Agents ทั้งหมดในเครื่อง.

ตรวจจับ + ลงทะเบียน + เรียกใช้ agents ที่มีอยู่:
- Codex CLI
- Claude Code
- Ollama (Local LLM)
- OpenClaw
- Gemini CLI
- Godcoder
- code-buddy
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class AgentInfo:
    """ข้อมูล agent หนึ่งตัว."""

    name: str
    display_name: str
    command: str
    available: bool = False
    version: str = ""
    path: str = ""
    capabilities: tuple[str, ...] = ()
    category: str = "coding"  # coding, llm, bridge, messaging


class AgentRegistry:
    """จัดการ AI Agents ทั้งหมดในเครื่อง.

    วิธีใช้:
        registry = AgentRegistry()
        registry.scan()

        available = registry.get_available()
        for agent in available:
            print(f"  ✅ {agent.display_name} — {agent.command}")

        # เรียกใช้ agent
        result = registry.run("ollama", "สร้าง API")
    """

    KNOWN_AGENTS: list[dict] = [
        {
            "name": "codex",
            "display_name": "Codex CLI (OpenAI)",
            "command": "codex",
            "category": "coding",
            "capabilities": ("code", "git", "shell", "debug", "deploy"),
        },
        {
            "name": "claude_code",
            "display_name": "Claude Code (Anthropic)",
            "command": "claude",
            "category": "coding",
            "capabilities": ("code", "analysis", "reasoning", "security"),
        },
        {
            "name": "ollama",
            "display_name": "Ollama (Local LLM)",
            "command": "ollama",
            "category": "llm",
            "capabilities": ("chat", "code", "local", "offline", "unlimited"),
        },
        {
            "name": "openclaw",
            "display_name": "OpenClaw (Local-first Agent)",
            "command": "openclaw",
            "category": "coding",
            "capabilities": ("code", "automation", "local-first"),
        },
        {
            "name": "gemini_cli",
            "display_name": "Gemini CLI (Google)",
            "command": "gemini",
            "category": "coding",
            "capabilities": ("code", "analysis", "multimodal"),
        },
        {
            "name": "gocoder",
            "display_name": "Godcoder (Local Desktop)",
            "command": "gocoder",
            "category": "coding",
            "capabilities": ("code", "local", "desktop"),
        },
        {
            "name": "code_buddy",
            "display_name": "Code Buddy (Multi-Provider)",
            "command": "code-buddy",
            "category": "coding",
            "capabilities": ("code", "15-providers", "110-tools"),
        },
        {
            "name": "node",
            "display_name": "Node.js",
            "command": "node",
            "category": "runtime",
            "capabilities": ("javascript", "typescript", "npm"),
        },
        {
            "name": "python",
            "display_name": "Python",
            "command": "python3",
            "category": "runtime",
            "capabilities": ("python", "pip", "pytest"),
        },
        {
            "name": "git",
            "display_name": "Git",
            "command": "git",
            "category": "tool",
            "capabilities": ("version-control", "branch", "merge"),
        },
        {
            "name": "docker",
            "display_name": "Docker",
            "command": "docker",
            "category": "tool",
            "capabilities": ("containers", "compose", "deploy"),
        },
        {
            "name": "npm",
            "display_name": "npm",
            "command": "npm",
            "category": "tool",
            "capabilities": ("packages", "node-modules"),
        },
    ]

    def __init__(self) -> None:
        self._agents: dict[str, AgentInfo] = {}
        self._init_known()

    def _init_known(self) -> None:
        for agent_def in self.KNOWN_AGENTS:
            info = AgentInfo(
                name=agent_def["name"],
                display_name=agent_def["display_name"],
                command=agent_def["command"],
                capabilities=agent_def["capabilities"],
                category=agent_def["category"],
            )
            self._agents[info.name] = info

    def scan(self) -> list[AgentInfo]:
        """สแกนหา agents ที่ติดตั้งอยู่ในเครื่อง."""
        for agent in self._agents.values():
            path = shutil.which(agent.command)
            if path:
                agent.available = True
                agent.path = path
                agent.version = self._get_version(agent.command)
            else:
                agent.available = False
        return list(self._agents.values())

    def get_available(self) -> list[AgentInfo]:
        """ดึงเฉพาะตัวที่พร้อมใช้งาน."""
        return [a for a in self._agents.values() if a.available]

    def get_by_category(self, category: str) -> list[AgentInfo]:
        """ดึงตาม category."""
        return [a for a in self._agents.values() if a.category == category]

    def get_by_name(self, name: str) -> AgentInfo | None:
        """ดึงตามชื่อ."""
        return self._agents.get(name)

    def run(self, agent_name: str, prompt: str, *, timeout: int = 60) -> dict:
        """เรียกใช้ agent."""
        agent = self._agents.get(agent_name)
        if not agent or not agent.available:
            return {"ok": False, "error": f"Agent {agent_name} not available"}

        try:
            cmd = [agent.command]
            if agent_name == "codex":
                cmd = ["codex", "-q", prompt]
            elif agent_name == "claude_code":
                cmd = ["claude", "-p", prompt]
            elif agent_name == "ollama":
                cmd = ["ollama", "run", "llama3", prompt]
            elif agent_name == "gemini_cli":
                cmd = ["gemini", "-p", prompt]
            else:
                cmd = [agent.command, prompt]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
            return {
                "ok": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:500] if result.stderr else "",
                "agent": agent_name,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Timeout", "agent": agent_name}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "agent": agent_name}

    def status(self) -> dict:
        """สถานะทั้งหมด."""
        available = self.get_available()
        return {
            "total_agents": len(self._agents),
            "available": len(available),
            "unavailable": len(self._agents) - len(available),
            "agents": {
                name: {
                    "available": agent.available,
                    "path": agent.path,
                    "version": agent.version,
                    "category": agent.category,
                }
                for name, agent in self._agents.items()
            },
        }

    def _get_version(self, command: str) -> str:
        try:
            result = subprocess.run(
                [command, "--version"], capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()[:100]
        except Exception:
            return ""
