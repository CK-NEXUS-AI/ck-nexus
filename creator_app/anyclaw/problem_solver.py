"""Problem Solver Toolkit — ช่วย GPT แก้ปัญหาทุกประเภท.

5 Problem Categories:
1. Code: write, debug, review, explain
2. Web: scrape, search, extract
3. File: read, write, manage
4. System: run commands, check status
5. Data: process, analyze, convert
"""
from __future__ import annotations

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class ProblemSolver:
    """ช่วย GPT แก้ปัญหาทุกประเภท."""

    def __init__(self):
        self._history: list[dict] = []

    def solve(self, category: str, task: str, **kwargs) -> dict:
        """แก้ปัญหา — เลือก category แล้วทำเลย."""
        handlers = {
            "code": self._solve_code,
            "web": self._solve_web,
            "file": self._solve_file,
            "system": self._solve_system,
            "data": self._solve_data,
        }
        handler = handlers.get(category)
        if not handler:
            return {"error": f"Unknown category: {category}"}

        result = handler(task, **kwargs)
        self._history.append({"category": category, "task": task, "result": result})
        return result

    # ═══ CODE ═══
    def _solve_code(self, task: str, **kwargs) -> dict:
        action = kwargs.get("action", "write")
        language = kwargs.get("language", "python")

        if action == "write":
            return self._code_write(task, language)
        elif action == "debug":
            return self._code_debug(task, kwargs.get("code", ""))
        elif action == "review":
            return self._code_review(kwargs.get("code", ""))
        elif action == "explain":
            return self._code_explain(kwargs.get("code", ""))
        return {"error": f"Unknown code action: {action}"}

    def _code_write(self, description: str, language: str) -> dict:
        templates = {
            "python": "# " + description + "\n" + "def solution():" + "\n" + "    pass" + "\n" + "\n" + 'if __name__ == "__main__":' + "\n" + "    print(solution())",
            "javascript": "// " + description + "\nfunction solution() {}" + "\nmodule.exports = solution;",
            "bash": "#!/bin/bash\n# " + description + "\necho \"" + description + "\"",
        }
        code = templates.get(language, templates["python"])
        return {"success": True, "code": code, "language": language}

    def _code_debug(self, description: str, code: str) -> dict:
        issues = []
        if not code:
            return {"error": "No code provided"}
        if "import" not in code and "require" not in code:
            issues.append("Missing imports")
        if "def " not in code and "function " not in code:
            issues.append("No function defined")
        if "return" not in code:
            issues.append("No return statement")
        if "error" in code.lower() and "try" not in code:
            issues.append("Error handling missing")
        return {"success": True, "issues": issues, "code": code}

    def _code_review(self, code: str) -> dict:
        if not code:
            return {"error": "No code provided"}
        suggestions = []
        lines = code.split("\n")
        if len(lines) > 50:
            suggestions.append("Code is long — consider splitting")
        if "TODO" in code:
            suggestions.append("Has TODO comments")
        if "FIXME" in code:
            suggestions.append("Has FIXME comments")
        if "print(" in code and "logging" not in code:
            suggestions.append("Consider using logging instead of print")
        return {"success": True, "suggestions": suggestions, "lines": len(lines)}

    def _code_explain(self, code: str) -> dict:
        if not code:
            return {"error": "No code provided"}
        explanation = f"Code has {len(code.split(chr(10)))} lines, {len(code.split())} words"
        return {"success": True, "explanation": explanation}

    # ═══ WEB ═══
    def _solve_web(self, task: str, **kwargs) -> dict:
        action = kwargs.get("action", "search")
        if action == "search":
            return self._web_search(task)
        elif action == "scrape":
            return self._web_scrape(kwargs.get("url", ""))
        elif action == "extract":
            return self._web_extract(kwargs.get("url", ""), kwargs.get("selector", ""))
        return {"error": f"Unknown web action: {action}"}

    def _web_search(self, query: str) -> dict:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            return {"success": True, "results": results, "count": len(results)}
        except Exception as e:
            return {"error": str(e)}

    def _web_scrape(self, url: str) -> dict:
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.find("title").text if soup.find("title") else "N/A"
            text = soup.get_text()[:500]
            return {"success": True, "title": title, "text": text, "status": resp.status_code}
        except Exception as e:
            return {"error": str(e)}

    def _web_extract(self, url: str, selector: str) -> dict:
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            elements = soup.select(selector)
            texts = [e.get_text()[:100] for e in elements[:10]]
            return {"success": True, "elements": texts, "count": len(elements)}
        except Exception as e:
            return {"error": str(e)}

    # ═══ FILE ═══
    def _solve_file(self, task: str, **kwargs) -> dict:
        action = kwargs.get("action", "read")
        path = kwargs.get("path", "")
        if action == "read":
            return self._file_read(path)
        elif action == "write":
            return self._file_write(path, kwargs.get("content", ""))
        elif action == "list":
            return self._file_list(path)
        elif action == "exists":
            return {"success": True, "exists": Path(path).exists()}
        return {"error": f"Unknown file action: {action}"}

    def _file_read(self, path: str) -> dict:
        try:
            p = Path(path)
            if not p.exists():
                return {"error": f"File not found: {path}"}
            content = p.read_text()[:5000]
            return {"success": True, "content": content, "size": p.stat().st_size}
        except Exception as e:
            return {"error": str(e)}

    def _file_write(self, path: str, content: str) -> dict:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return {"success": True, "path": path, "size": len(content)}
        except Exception as e:
            return {"error": str(e)}

    def _file_list(self, path: str) -> dict:
        try:
            p = Path(path)
            if not p.exists():
                return {"error": f"Path not found: {path}"}
            items = []
            for item in sorted(p.iterdir())[:50]:
                items.append({"name": item.name, "type": "dir" if item.is_dir() else "file", "size": item.stat().st_size if item.is_file() else 0})
            return {"success": True, "items": items, "count": len(items)}
        except Exception as e:
            return {"error": str(e)}

    # ═══ SYSTEM ═══
    def _solve_system(self, task: str, **kwargs) -> dict:
        action = kwargs.get("action", "run")
        if action == "run":
            return self._system_run(kwargs.get("command", task))
        elif action == "status":
            return self._system_status()
        elif action == "process":
            return self._system_process()
        return {"error": f"Unknown system action: {action}"}

    def _system_run(self, command: str) -> dict:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:500],
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"error": str(e)}

    def _system_status(self) -> dict:
        import platform
        return {
            "success": True,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cwd": os.getcwd(),
        }

    def _system_process(self) -> dict:
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split("\n")[:10]
            return {"success": True, "processes": lines}
        except Exception as e:
            return {"error": str(e)}

    # ═══ DATA ═══
    def _solve_data(self, task: str, **kwargs) -> dict:
        action = kwargs.get("action", "convert")
        if action == "convert":
            return self._data_convert(kwargs.get("data", ""), kwargs.get("from_fmt", ""), kwargs.get("to_fmt", ""))
        elif action == "analyze":
            return self._data_analyze(kwargs.get("data", ""))
        elif action == "json":
            return self._data_json(kwargs.get("data", ""))
        return {"error": f"Unknown data action: {action}"}

    def _data_convert(self, data: str, from_fmt: str, to_fmt: str) -> dict:
        try:
            if from_fmt == "json" and to_fmt == "yaml":
                import yaml
                parsed = json.loads(data)
                converted = yaml.dump(parsed)
                return {"success": True, "result": converted}
            elif from_fmt == "json" and to_fmt == "csv":
                parsed = json.loads(data)
                if isinstance(parsed, list) and len(parsed) > 0:
                    headers = list(parsed[0].keys())
                    rows = [",".join(str(r.get(h, "")) for h in headers) for r in parsed]
                    csv = ",".join(headers) + "\n" + "\n".join(rows)
                    return {"success": True, "result": csv}
            return {"error": f"Conversion {from_fmt} -> {to_fmt} not supported"}
        except Exception as e:
            return {"error": str(e)}

    def _data_analyze(self, data: str) -> dict:
        try:
            parsed = json.loads(data) if data.startswith(("[", "{")) else data.split("\n")
            return {"success": True, "type": type(parsed).__name__, "length": len(parsed)}
        except:
            return {"success": True, "type": "string", "length": len(data)}

    def _data_json(self, data: str) -> dict:
        try:
            parsed = json.loads(data)
            return {"success": True, "valid": True, "type": type(parsed).__name__}
        except json.JSONDecodeError as e:
            return {"success": True, "valid": False, "error": str(e)}

    # ═══ HELPERS ═══
    def get_tools(self) -> list[dict]:
        """Get tool definitions for GPT."""
        return [
            {"name": "solve_code", "description": "แก้ปัญหาโค้ด: write, debug, review, explain", "category": "code"},
            {"name": "solve_web", "description": "ค้นหา/ดึงข้อมูลเว็บ: search, scrape, extract", "category": "web"},
            {"name": "solve_file", "description": "จัดการไฟล์: read, write, list, exists", "category": "file"},
            {"name": "solve_system", "description": "รันคำสั่ง/ตรวจสอบระบบ: run, status, process", "category": "system"},
            {"name": "solve_data", "description": "ประมวลผลข้อมูล: convert, analyze, json", "category": "data"},
        ]

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool — main entry point for GPT."""
        category = name.replace("solve_", "")
        return self.solve(category, arguments.get("task", ""), **arguments)


# ═══ Singleton ═══
_solver = ProblemSolver()

def get_tools() -> list[dict]:
    return _solver.get_tools()

def call_tool(name: str, arguments: dict) -> dict:
    return _solver.call_tool(name, arguments)
