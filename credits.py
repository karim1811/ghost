#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────
# GHOST Credits System
# Gestion des credits pour l'enrichissement AI
# ──────────────────────────────────────────────────────────
#
# Usage:
#   from credits import CreditsManager
#   cm = CreditsManager()
#   cm.add_credits(user_id, 10)
#   cm.deduct_credits(user_id, 1)
#   cm.get_balance(user_id)
# ──────────────────────────────────────────────────────────

import json
import os
import time
from pathlib import Path
from typing import Optional

# ── Config ──────────────────────────────────────────────
CREDITS_DB_PATH = Path(os.getenv("GHOST_CREDITS_DB", "credits.json"))
CREDITS_PER_SCAN = int(os.getenv("GHOST_CREDITS_PER_SCAN", "1"))
CREDITS_PER_DEEP = int(os.getenv("GHOST_CREDITS_PER_DEEP", "3"))
FREE_DAILY_SCANS = int(os.getenv("GHOST_FREE_DAILY", "3"))

# ── Credits Manager ─────────────────────────────────────

class CreditsManager:
    """Gestion des credits utilisateur"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or CREDITS_DB_PATH
        self._load()

    def _load(self):
        """Charge la DB credits"""
        if self.db_path.exists():
            self.db = json.loads(self.db_path.read_text(encoding="utf-8"))
        else:
            self.db = {"users": {}, "transactions": []}

    def _save(self):
        """Sauvegarde la DB"""
        self.db_path.write_text(json.dumps(self.db, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_balance(self, user_id: str) -> dict:
        """Retourne le solde d'un utilisateur"""
        user = self.db["users"].get(str(user_id), {})
        return {
            "credits": user.get("credits", 0),
            "free_scans_today": user.get("free_scans_today", 0),
            "free_scans_reset": user.get("free_reset", 0),
            "total_scans": user.get("total_scans", 0),
            "plan": user.get("plan", "free"),  # free, pro, enterprise
        }

    def add_credits(self, user_id: str, amount: int, reason: str = "purchase"):
        """Ajoute des credits"""
        uid = str(user_id)
        if uid not in self.db["users"]:
            self.db["users"][uid] = {"credits": 0, "free_scans_today": 0, "total_scans": 0, "plan": "free"}

        self.db["users"][uid]["credits"] = self.db["users"][uid].get("credits", 0) + amount
        self.db["transactions"].append({
            "user_id": uid,
            "type": "add",
            "amount": amount,
            "reason": reason,
            "timestamp": time.time(),
        })
        self._save()
        return self.db["users"][uid]["credits"]

    def can_scan(self, user_id: str, deep: bool = False) -> tuple:
        """
        Verifie si un utilisateur peut lancer un scan.
        Retourne (bool, reason)
        """
        uid = str(user_id)
        user = self.db["users"].get(uid, {"credits": 0, "free_scans_today": 0, "plan": "free"})

        # Reset daily scans if needed
        now = time.time()
        last_reset = user.get("free_reset", 0)
        if now - last_reset > 86400:  # 24h
            user["free_scans_today"] = 0
            user["free_reset"] = now
            self.db["users"][uid] = user
            self._save()

        # Pro/Enterprise users have unlimited scans
        if user.get("plan") in ("pro", "enterprise"):
            return True, "unlimited"

        # Check free daily scans
        if user.get("free_scans_today", 0) < FREE_DAILY_SCANS:
            return True, "free_tier"

        # Check paid credits
        cost = CREDITS_PER_DEEP if deep else CREDITS_PER_SCAN
        if user.get("credits", 0) >= cost:
            return True, "paid"

        return False, f"Insufficient credits (need {cost}, have {user.get('credits', 0)})"

    def deduct_credits(self, user_id: str, deep: bool = False) -> bool:
        """Deduit les credits pour un scan. Retourne True si succes."""
        uid = str(user_id)
        can, reason = self.can_scan(user_id, deep)

        if not can:
            return False

        if uid not in self.db["users"]:
            self.db["users"][uid] = {"credits": 0, "free_scans_today": 0, "total_scans": 0, "plan": "free"}

        user = self.db["users"][uid]

        if reason == "free_tier":
            user["free_scans_today"] = user.get("free_scans_today", 0) + 1
        elif reason == "paid":
            cost = CREDITS_PER_DEEP if deep else CREDITS_PER_SCAN
            user["credits"] = user.get("credits", 0) - cost
            self.db["transactions"].append({
                "user_id": uid,
                "type": "deduct",
                "amount": cost,
                "reason": "deep_scan" if deep else "scan",
                "timestamp": time.time(),
            })

        user["total_scans"] = user.get("total_scans", 0) + 1
        self._save()
        return True

    def set_plan(self, user_id: str, plan: str):
        """Definit le plan d'un utilisateur (free, pro, enterprise)"""
        uid = str(user_id)
        if uid not in self.db["users"]:
            self.db["users"][uid] = {"credits": 0, "free_scans_today": 0, "total_scans": 0, "plan": "free"}
        self.db["users"][uid]["plan"] = plan
        self._save()

    def get_stats(self) -> dict:
        """Statistiques globales"""
        total_users = len(self.db["users"])
        total_scans = sum(u.get("total_scans", 0) for u in self.db["users"].values())
        total_credits_sold = sum(
            t["amount"] for t in self.db.get("transactions", [])
            if t["type"] == "add"
        )
        return {
            "total_users": total_users,
            "total_scans": total_scans,
            "total_credits_sold": total_credits_sold,
            "active_plans": {
                plan: sum(1 for u in self.db["users"].values() if u.get("plan") == plan)
                for plan in ["free", "pro", "enterprise"]
            },
        }


# ── Pricing ─────────────────────────────────────────────

PACKAGES = {
    "starter": {"credits": 10, "price_eur": 4.99, "label": "10 scans"},
    "pro": {"credits": 50, "price_eur": 19.99, "label": "50 scans"},
    "unlimited": {"credits": 999, "price_eur": 49.99, "label": "Unlimited (pro plan)"},
}

if __name__ == "__main__":
    # Demo
    cm = CreditsManager()

    # Add test user
    cm.add_credits("user123", 10, "purchase")
    print(f"Balance: {cm.get_balance('user123')}")

    # Try scan
    can, reason = cm.can_scan("user123", deep=True)
    print(f"Can scan (deep): {can} ({reason})")

    if can:
        cm.deduct_credits("user123", deep=True)
        print(f"After scan: {cm.get_balance('user123')}")

    print(f"Stats: {cm.get_stats()}")
