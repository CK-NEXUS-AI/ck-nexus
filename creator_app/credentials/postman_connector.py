"""Postman API Connector — เชื่อมต่อ Postman ผ่าน API Key.

วิธีใช้:
    1. ใส่ POSTMAN_API_KEY ใน .env
    2. connector = PostmanConnector()
    3. collections = connector.list_collections()
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests


@dataclass
class PostmanCollection:
    """ข้อมูล collection หนึ่งชิ้น."""

    uid: str
    name: str
    description: str = ""
    owner: str = ""
    createdAt: str = ""
    updatedAt: str = ""
    schema: str = ""


@dataclass
class PostmanEnvironment:
    """ข้อมูล environment หนึ่งชิ้น."""

    uid: str
    name: str
    values: list[dict] = field(default_factory=list)


class PostmanConnector:
    """เชื่อมต่อ Postman API.

    วิธีใช้:
        connector = PostmanConnector()  # ดึง key จาก .env
        collections = connector.list_collections()
        for c in collections:
            print(f"  {c.name} ({c.uid})")
    """

    BASE_URL = "https://api.getpostman.com"

    def __init__(self, api_key: str | None = None, vault_id: str | None = None):
        if vault_id:
            from creator_app.credentials.blind_vault import BlindVault
            vault = BlindVault()
            self._api_key = vault.retrieve(vault_id)
        else:
            self._api_key = api_key or os.getenv("POSTMAN_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "POSTMAN_API_KEY not found. "
                "Set it in .env, pass api_key=, or vault_id= parameter."
            )
        self._headers = {
            "X-Api-Key": self._api_key,
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str) -> dict:
        """ส่ง GET request."""
        url = f"{self.BASE_URL}{endpoint}"
        resp = requests.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, data: dict) -> dict:
        """ส่ง POST request."""
        url = f"{self.BASE_URL}{endpoint}"
        resp = requests.post(url, headers=self._headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _put(self, endpoint: str, data: dict) -> dict:
        """ส่ง PUT request."""
        url = f"{self.BASE_URL}{endpoint}"
        resp = requests.put(url, headers=self._headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, endpoint: str) -> dict:
        """ส่ง DELETE request."""
        url = f"{self.BASE_URL}{endpoint}"
        resp = requests.delete(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    # ─── Collections ────────────────────────────────────

    def list_collections(self) -> list[PostmanCollection]:
        """ดึงรายการ Collections ทั้งหมด."""
        data = self._get("/collections")
        collections = []
        for c in data.get("collections", []):
            info = c.get("info", {})
            collections.append(PostmanCollection(
                uid=c.get("uid", ""),
                name=info.get("name", ""),
                description=info.get("description", ""),
                owner=info.get("owner", ""),
                createdAt=info.get("createdAt", ""),
                updatedAt=info.get("updatedAt", ""),
                schema=info.get("schema", ""),
            ))
        return collections

    def get_collection(self, uid: str) -> dict:
        """ดึงรายละเอียด Collection."""
        data = self._get(f"/collections/{uid}")
        return data.get("collection", data)

    def create_collection(self, name: str, description: str = "") -> dict:
        """สร้าง Collection ใหม่."""
        data = {
            "collection": {
                "info": {
                    "name": name,
                    "description": description,
                    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                },
                "item": [],
            }
        }
        return self._post("/collections", data)

    def delete_collection(self, uid: str) -> dict:
        """ลบ Collection."""
        return self._delete(f"/collections/{uid}")

    # ─── Environments ───────────────────────────────────

    def list_environments(self) -> list[PostmanEnvironment]:
        """ดึงรายการ Environments ทั้งหมด."""
        data = self._get("/environments")
        envs = []
        for e in data.get("environments", []):
            envs.append(PostmanEnvironment(
                uid=e.get("uid", ""),
                name=e.get("name", ""),
                values=e.get("values", []),
            ))
        return envs

    def get_environment(self, uid: str) -> dict:
        """ดึงรายละเอียด Environment."""
        data = self._get(f"/environments/{uid}")
        return data.get("environment", data)

    def create_environment(self, name: str, values: list[dict] | None = None) -> dict:
        """สร้าง Environment ใหม่."""
        data = {
            "environment": {
                "name": name,
                "values": values or [],
            }
        }
        return self._post("/environments", data)

    # ─── Workspaces ─────────────────────────────────────

    def list_workspaces(self) -> list[dict]:
        """ดึงรายการ Workspaces."""
        data = self._get("/workspaces")
        return data.get("workspaces", [])

    # ─── History ────────────────────────────────────────

    def list_history(self, limit: int = 50) -> list[dict]:
        """ดึงประวัติคำขอ."""
        data = self._get(f"/history?limit={limit}")
        return data.get("history", [])

    # ─── Monitoring ─────────────────────────────────────

    def list_monitors(self) -> list[dict]:
        """ดึงรายการ Monitors."""
        data = self._get("/monitors")
        return data.get("monitors", [])

    # ─── Status ─────────────────────────────────────────

    def status(self) -> dict:
        """สถานะการเชื่อมต่อ."""
        try:
            workspaces = self.list_workspaces()
            collections = self.list_collections()
            environments = self.list_environments()
            return {
                "connected": True,
                "api_key_set": bool(self._api_key),
                "workspaces": len(workspaces),
                "collections": len(collections),
                "environments": len(environments),
            }
        except Exception as exc:
            return {
                "connected": False,
                "error": str(exc),
            }
