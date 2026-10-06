import json
import uuid
from datetime import datetime
from typing import Any
from backend.app.db.local_db import get_connection, hash_password, verify_password

class Repository:
    """
    Data repository handling users, preferences, credits, search history, saved locations, and reports.
    """

    @staticmethod
    def create_user(email: str, password: str, display_name: str | None = None, is_email_verified: bool = False) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        user_id = str(uuid.uuid4())
        pwd_hash, salt = hash_password(password)
        now = datetime.utcnow().isoformat()
        name = display_name or email.split("@")[0]

        try:
            cursor.execute(
                "INSERT INTO users (id, email, password_hash, salt, display_name, is_email_verified, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, email.lower().strip(), pwd_hash, salt, name, 1 if is_email_verified else 0, now)
            )
            cursor.execute(
                "INSERT INTO profiles (id, display_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, name, now, now)
            )
            cursor.execute(
                "INSERT INTO user_preferences (id, user_id, default_profile, default_priorities, distance_preferences, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, "family", json.dumps(["education", "healthcare", "transport", "daily_life"]), json.dumps([]), now)
            )
            
            # Initial credits: 3 if verified, 0 if unverified
            initial_credits = 3 if is_email_verified else 0
            cursor.execute(
                "INSERT INTO report_credits (id, user_id, credits_remaining, credits_used, updated_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, initial_credits, 0, now)
            )
            conn.commit()

            return {
                "id": user_id,
                "email": email.lower().strip(),
                "display_name": name,
                "is_email_verified": is_email_verified,
                "created_at": now
            }
        except Exception as e:
            conn.rollback()
            return None
        finally:
            conn.close()

    @staticmethod
    def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
            row = cursor.fetchone()
            if not row:
                return None
            
            if verify_password(password, row["password_hash"], row["salt"]):
                return {
                    "id": row["id"],
                    "email": row["email"],
                    "display_name": row["display_name"],
                    "is_email_verified": bool(row["is_email_verified"]),
                    "created_at": row["created_at"]
                }
            return None
        finally:
            conn.close()

    @staticmethod
    def get_user_by_id(user_id: str) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "email": row["email"],
                "display_name": row["display_name"],
                "is_email_verified": bool(row["is_email_verified"]),
                "created_at": row["created_at"]
            }
        finally:
            conn.close()

    @staticmethod
    def verify_user_email(user_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_email_verified = 1 WHERE id = ?", (user_id,))
            # Grant 3 credits if not previously granted
            cursor.execute("SELECT credits_remaining, credits_used FROM report_credits WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                if row["credits_remaining"] == 0 and row["credits_used"] == 0:
                    cursor.execute("UPDATE report_credits SET credits_remaining = 3, updated_at = ? WHERE user_id = ?", (datetime.utcnow().isoformat(), user_id))
            else:
                cursor.execute(
                    "INSERT INTO report_credits (id, user_id, credits_remaining, credits_used, updated_at) VALUES (?, ?, 3, 0, ?)",
                    (str(uuid.uuid4()), user_id, datetime.utcnow().isoformat())
                )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def get_credits(user_id: str) -> dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT credits_remaining, credits_used FROM report_credits WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return {"credits_remaining": 0, "credits_used": 0, "can_generate_report": False}
            rem = row["credits_remaining"]
            used = row["credits_used"]
            return {
                "credits_remaining": rem,
                "credits_used": used,
                "can_generate_report": rem > 0
            }
        finally:
            conn.close()

    @staticmethod
    def deduct_credit(user_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT credits_remaining, credits_used FROM report_credits WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row or row["credits_remaining"] <= 0:
                return False
            
            cursor.execute(
                "UPDATE report_credits SET credits_remaining = credits_remaining - 1, credits_used = credits_used + 1, updated_at = ? WHERE user_id = ?",
                (datetime.utcnow().isoformat(), user_id)
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def add_credits(user_id: str, count: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE report_credits SET credits_remaining = credits_remaining + ?, updated_at = ? WHERE user_id = ?",
                (count, datetime.utcnow().isoformat(), user_id)
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def get_preferences(user_id: str) -> dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT default_profile, default_priorities, distance_preferences FROM user_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return {
                    "default_profile": "family",
                    "default_priorities": ["education", "healthcare", "transport", "daily_life"],
                    "distance_preferences": []
                }
            return {
                "default_profile": row["default_profile"],
                "default_priorities": json.loads(row["default_priorities"] or "[]"),
                "distance_preferences": json.loads(row["distance_preferences"] or "[]")
            }
        finally:
            conn.close()

    @staticmethod
    def update_preferences(user_id: str, default_profile: str, default_priorities: list[str], distance_preferences: list[dict]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE user_preferences SET default_profile = ?, default_priorities = ?, distance_preferences = ?, updated_at = ? WHERE user_id = ?",
                (default_profile, json.dumps(default_priorities), json.dumps(distance_preferences), datetime.utcnow().isoformat(), user_id)
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def get_search_history(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, locality_name, lat, lng, searched_at, provider FROM search_history WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def add_search_history(user_id: str, locality_name: str, lat: float, lng: float, provider: str = "Google Places") -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO search_history (id, user_id, locality_name, lat, lng, searched_at, provider) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, locality_name, lat, lng, datetime.utcnow().isoformat(), provider)
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def clear_search_history(user_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def get_saved_locations(user_id: str) -> list[dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, locality_name, lat, lng, label, notes, created_at, updated_at FROM saved_locations WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def add_saved_location(user_id: str, locality_name: str, lat: float, lng: float, label: str | None = None, notes: str | None = None) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        item_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        try:
            cursor.execute(
                "INSERT INTO saved_locations (id, user_id, locality_name, lat, lng, label, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item_id, user_id, locality_name, lat, lng, label, notes, now, now)
            )
            conn.commit()
            return {
                "id": item_id,
                "locality_name": locality_name,
                "lat": lat,
                "lng": lng,
                "label": label,
                "notes": notes,
                "created_at": now
            }
        except Exception:
            conn.rollback()
            return None
        finally:
            conn.close()

    @staticmethod
    def update_saved_location(user_id: str, location_id: str, label: str | None, notes: str | None) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE saved_locations SET label = ?, notes = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (label, notes, datetime.utcnow().isoformat(), location_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def delete_saved_location(user_id: str, location_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM saved_locations WHERE id = ? AND user_id = ?", (location_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def create_report(
        user_id: str,
        title: str,
        locality_name: str,
        lat: float,
        lng: float,
        comparison_locality_name: str | None,
        comparison_lat: float | None,
        comparison_lng: float | None,
        user_profile: str,
        user_priorities: list[str],
        sections_included: list[str],
        verification_hash: str,
        pdf_storage_path: str,
        qr_code_url: str,
        raw_evidence: list[dict],
        aggregated_metrics: dict,
        providers_used: list[dict],
        property_context: dict | None = None,
        report_id: str | None = None
    ) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        report_id = report_id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        try:
            cursor.execute("""
                INSERT INTO reports (
                    id, user_id, title, locality_name, lat, lng,
                    comparison_locality_name, comparison_lat, comparison_lng,
                    user_profile, user_priorities, sections_included,
                    verification_hash, pdf_storage_path, qr_code_url,
                    created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready')
            """, (
                report_id, user_id, title, locality_name, lat, lng,
                comparison_locality_name, comparison_lat, comparison_lng,
                user_profile, json.dumps(user_priorities), json.dumps(sections_included),
                verification_hash, pdf_storage_path, qr_code_url,
                now
            ))

            # Store snapshot (storable data only)
            cursor.execute("""
                INSERT INTO report_data_snapshots (
                    id, report_id, raw_evidence, aggregated_metrics, fetched_at, providers_used
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), report_id, json.dumps(raw_evidence), json.dumps(aggregated_metrics),
                now, json.dumps(providers_used)
            ))

            # Store property context if provided
            if property_context:
                cursor.execute("""
                    INSERT INTO report_properties (
                        id, report_id, property_address, floor_level, unit_facing,
                        water_source_declared, power_backup_declared, rent_or_price, user_notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()), report_id,
                    property_context.get("property_address"),
                    property_context.get("floor_level"),
                    property_context.get("unit_facing"),
                    property_context.get("water_source_declared"),
                    property_context.get("power_backup_declared"),
                    property_context.get("rent_or_price"),
                    property_context.get("user_notes"),
                    now
                ))

            conn.commit()
            return {
                "id": report_id,
                "title": title,
                "locality_name": locality_name,
                "created_at": now,
                "verification_hash": verification_hash,
                "pdf_storage_path": pdf_storage_path,
                "qr_code_url": qr_code_url,
                "status": "ready"
            }
        except Exception as e:
            conn.rollback()
            return None
        finally:
            conn.close()

    @staticmethod
    def get_user_reports(user_id: str) -> list[dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, title, locality_name, comparison_locality_name, created_at, status, verification_hash, pdf_storage_path, qr_code_url FROM reports WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_report_by_id(report_id: str) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM reports WHERE id = ?",
                (report_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            report = dict(row)
            # Parse json fields
            for f in ["user_priorities", "sections_included"]:
                if f in report and report[f]:
                    try:
                        report[f] = json.loads(report[f])
                    except Exception:
                        pass
            # Fetch snapshot data if present
            cursor.execute(
                "SELECT raw_evidence, aggregated_metrics, fetched_at, providers_used FROM report_data_snapshots WHERE report_id = ?",
                (report_id,)
            )
            snap = cursor.fetchone()
            if snap:
                report["snapshot"] = {
                    "fetched_at": snap["fetched_at"],
                    "aggregated_metrics": json.loads(snap["aggregated_metrics"]) if snap["aggregated_metrics"] else {},
                    "providers_used": json.loads(snap["providers_used"]) if snap["providers_used"] else []
                }
            return report
        finally:
            conn.close()

    @staticmethod
    def get_public_verification(report_id: str) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, title, locality_name, comparison_locality_name, created_at, verification_hash, status FROM reports WHERE id = ?",
                (report_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)
        finally:
            conn.close()

    @staticmethod
    def submit_feedback(user_id: str | None, report_id: str | None, locality_name: str | None, feedback_type: str, description: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO feedback (id, user_id, report_id, locality_name, feedback_type, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, report_id, locality_name, feedback_type, description, datetime.utcnow().isoformat())
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
