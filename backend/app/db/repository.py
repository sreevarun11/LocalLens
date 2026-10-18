import json
import uuid
import logging
from datetime import datetime
from typing import Any
from backend.app.config import settings
from backend.app.db.local_db import get_connection, hash_password, verify_password
from backend.app.auth.argon2_utils import generate_recovery_codes, verify_recovery_code, hash_secret

logger = logging.getLogger(__name__)

class Repository:
    """
    Data repository handling users, preferences, credits, search history, saved locations, reports, payments, and recovery codes.
    """

    @staticmethod
    def create_user(
        email_or_username: str | None = None,
        password: str = "",
        display_name: str | None = None,
        is_email_verified: bool = True,
        username: str | None = None,
        email: str | None = None,
        is_admin: bool = False
    ) -> dict[str, Any] | None:
        """
        Creates a user account using Argon2id password hashing and generates 10 single-use recovery codes.
        Enforces a minimum password length of 10 characters.
        Returns:
            user_dict (containing plain 'recovery_codes') on success, or None on failure.
        """
        if len(password) < 10:
            return None

        target_email = email
        target_username = username

        if email_or_username:
            if "@" in email_or_username:
                if not target_email:
                    target_email = email_or_username
                if not target_username:
                    target_username = email_or_username.split("@")[0]
            else:
                if not target_username:
                    target_username = email_or_username

        if not target_username and target_email:
            target_username = target_email.split("@")[0]
        if not target_username:
            target_username = "user"

        clean_username = target_username.lower().strip()
        clean_email = target_email.lower().strip() if target_email else None
        name = (display_name or target_username).strip()

        conn = get_connection()
        cursor = conn.cursor()
        user_id = str(uuid.uuid4())
        pwd_hash, salt = hash_password(password)
        now = datetime.utcnow().isoformat()

        try:
            # Check for existing username or email
            cursor.execute("SELECT id FROM users WHERE LOWER(username) = ?", (clean_username,))
            if cursor.fetchone():
                return None
            if clean_email:
                cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (clean_email,))
                if cursor.fetchone():
                    return None

            # Generate 10 single-use recovery codes
            plain_codes, hashed_codes = generate_recovery_codes(10)

            cursor.execute(
                """INSERT INTO users (id, username, email, password_hash, salt, display_name, is_admin, is_email_verified, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, target_username, clean_email, pwd_hash, salt, name, bool(is_admin), bool(is_email_verified), now, now)
            )
            cursor.execute(
                "INSERT INTO profiles (id, display_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, name, now, now)
            )
            cursor.execute(
                "INSERT INTO user_preferences (id, user_id, default_profile, default_priorities, distance_preferences, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, "family", json.dumps(["education", "healthcare", "transport", "daily_life"]), json.dumps([]), now)
            )
            
            # 3 free reports allowance if email verified, 0 if unverified
            initial_credits = 3 if is_email_verified else 0
            cursor.execute(
                "INSERT INTO report_credits (id, user_id, credits_remaining, credits_used, updated_at) VALUES (?, ?, ?, 0, ?)",
                (str(uuid.uuid4()), user_id, initial_credits, now)
            )

            # Insert hashed recovery codes
            for h_code in hashed_codes:
                cursor.execute(
                    "INSERT INTO recovery_codes (id, user_id, code_hash, used_at, created_at) VALUES (?, ?, ?, NULL, ?)",
                    (str(uuid.uuid4()), user_id, h_code, now)
                )

            conn.commit()

            return {
                "id": user_id,
                "username": target_username,
                "email": clean_email,
                "display_name": name,
                "is_admin": bool(is_admin),
                "is_email_verified": bool(is_email_verified),
                "created_at": now,
                "recovery_codes": plain_codes
            }
        except Exception:
            conn.rollback()
            return None
        finally:
            conn.close()

    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            clean_identifier = username_or_email.lower().strip()
            cursor.execute(
                "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
                (clean_identifier, clean_identifier)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            salt = row["salt"] if "salt" in row.keys() and row["salt"] else ""
            if verify_password(password, row["password_hash"], salt):
                row_keys = row.keys()
                user_is_admin = bool(row["is_admin"]) if "is_admin" in row_keys and row["is_admin"] is not None else False
                return {
                    "id": row["id"],
                    "username": row["username"] if "username" in row_keys and row["username"] else (row["email"].split("@")[0] if "email" in row_keys and row["email"] else "user"),
                    "email": row["email"] if "email" in row_keys else None,
                    "display_name": row["display_name"],
                    "is_admin": user_is_admin,
                    "is_email_verified": bool(row["is_email_verified"]) if "is_email_verified" in row_keys else True,
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
            row_keys = row.keys()
            user_is_admin = bool(row["is_admin"]) if "is_admin" in row_keys and row["is_admin"] is not None else False
            return {
                "id": row["id"],
                "username": row["username"] if "username" in row_keys and row["username"] else (row["email"].split("@")[0] if "email" in row_keys and row["email"] else "user"),
                "email": row["email"] if "email" in row_keys else None,
                "display_name": row["display_name"],
                "is_admin": user_is_admin,
                "is_email_verified": bool(row["is_email_verified"]) if "is_email_verified" in row_keys else True,
                "created_at": row["created_at"]
            }
        finally:
            conn.close()

    @staticmethod
    def recover_password(username: str, recovery_code: str, new_password: str) -> tuple[bool, str]:
        """
        Validates a single-use recovery code against Argon2id hashes, updates the password,
        marks the recovery code used, and revokes all active sessions for the user.
        """
        if len(new_password) < 10:
            return False, "New password must be at least 10 characters long."

        conn = get_connection()
        cursor = conn.cursor()
        try:
            clean_name = username.lower().strip()
            cursor.execute("SELECT id FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?", (clean_name, clean_name))
            user_row = cursor.fetchone()
            if not user_row:
                return False, "User account not found."

            user_id = user_row["id"]
            cursor.execute("SELECT id, code_hash FROM recovery_codes WHERE user_id = ? AND used_at IS NULL", (user_id,))
            unused_codes = cursor.fetchall()

            matched_code_id = None
            for code_row in unused_codes:
                if verify_recovery_code(code_row["code_hash"], recovery_code):
                    matched_code_id = code_row["id"]
                    break

            if not matched_code_id:
                return False, "Invalid or already-used recovery code."

            now = datetime.utcnow().isoformat()
            cursor.execute("UPDATE recovery_codes SET used_at = ? WHERE id = ?", (now, matched_code_id))
            pwd_hash, _ = hash_password(new_password)
            cursor.execute("UPDATE users SET password_hash = ?, salt = '', updated_at = ? WHERE id = ?", (pwd_hash, now, user_id))
            cursor.execute("UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (now, user_id))
            conn.commit()
            return True, "Password reset successfully. All active sessions have been revoked. Please log in with your new password."
        except Exception as e:
            conn.rollback()
            return False, f"Failed to reset password: {e}"
        finally:
            conn.close()

    @staticmethod
    def regenerate_recovery_codes(user_id: str, current_password: str) -> tuple[list[str] | None, str]:
        """
        Replaces all existing recovery codes with 10 newly generated ones after verifying current password.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                return None, "User not found."

            salt = user_row["salt"] if "salt" in user_row.keys() and user_row["salt"] else ""
            if not verify_password(current_password, user_row["password_hash"], salt):
                return None, "Current password does not match."

            now = datetime.utcnow().isoformat()
            cursor.execute("UPDATE recovery_codes SET used_at = ? WHERE user_id = ? AND used_at IS NULL", (now, user_id))

            plain_codes, hashed_codes = generate_recovery_codes(10)
            for h_code in hashed_codes:
                cursor.execute(
                    "INSERT INTO recovery_codes (id, user_id, code_hash, used_at, created_at) VALUES (?, ?, ?, NULL, ?)",
                    (str(uuid.uuid4()), user_id, h_code, now)
                )
            conn.commit()
            return plain_codes, "Successfully regenerated 10 single-use recovery codes."
        except Exception as e:
            conn.rollback()
            return None, f"Failed to regenerate recovery codes: {e}"
        finally:
            conn.close()

    @staticmethod
    def verify_user_email(user_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_email_verified = TRUE WHERE id = ?", (user_id,))
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
                    "raw_evidence": json.loads(snap["raw_evidence"]) if snap["raw_evidence"] else [],
                    "aggregated_metrics": json.loads(snap["aggregated_metrics"]) if snap["aggregated_metrics"] else {},
                    "providers_used": json.loads(snap["providers_used"]) if snap["providers_used"] else []
                }

            # Fetch property context if present
            cursor.execute(
                "SELECT property_address, floor_level, unit_facing, water_source_declared, power_backup_declared, rent_or_price, user_notes FROM report_properties WHERE report_id = ?",
                (report_id,)
            )
            prop = cursor.fetchone()
            if prop:
                report["property_context"] = dict(prop)

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

    @staticmethod
    def get_report_by_id_for_user(report_id: str, user_id: str | None = None, is_admin: bool = False) -> dict[str, Any] | None:
        """
        Retrieves report with cross-user isolation.
        Non-admin users can strictly access only their own reports.
        """
        report = Repository.get_report_by_id(report_id)
        if not report:
            return None
        if is_admin:
            return report
        if user_id and report.get("user_id") != user_id:
            return None
        return report

    @staticmethod
    def create_session(user_id: str, session_token: str, expires_in_seconds: int = 86400 * 7) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.utcnow()
        expires_at = datetime.utcfromtimestamp(now.timestamp() + expires_in_seconds).isoformat()
        try:
            cursor.execute(
                "INSERT INTO sessions (id, user_id, session_token, expires_at, created_at, revoked_at) VALUES (?, ?, ?, ?, ?, NULL)",
                (str(uuid.uuid4()), user_id, session_token, expires_at, now.isoformat())
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def is_session_valid(session_token: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT expires_at, revoked_at FROM sessions WHERE session_token = ?",
                (session_token,)
            )
            row = cursor.fetchone()
            if not row or row["revoked_at"] is not None:
                return False
            return row["expires_at"] > datetime.utcnow().isoformat()
        finally:
            conn.close()

    @staticmethod
    def revoke_all_sessions(user_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
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
    def is_token_revoked(session_token: str) -> bool:
        """Checks if a session token has been revoked in the sessions table."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT revoked_at FROM sessions WHERE session_token = ?",
                (session_token,)
            )
            row = cursor.fetchone()
            if row and row["revoked_at"] is not None:
                return True
            return False
        finally:
            conn.close()

    @staticmethod
    def revoke_session(session_token: str) -> bool:
        """Invalidates a specific session token."""
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        try:
            cursor.execute(
                "SELECT id FROM sessions WHERE session_token = ?",
                (session_token,)
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE sessions SET revoked_at = ? WHERE session_token = ?",
                    (now, session_token)
                )
            else:
                from backend.app.auth.tokens import decode_access_token
                payload = decode_access_token(session_token) or {}
                user_id = payload.get("sub", "unknown")
                cursor.execute(
                    "INSERT INTO sessions (id, user_id, session_token, expires_at, created_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), user_id, session_token, now, now, now)
                )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def provision_admin_user(username: str = "sreevarun", password: str | None = None) -> dict[str, Any] | None:
        """
        Securely provisions or synchronizes the administrator account on the server side.
        Guarantees that the account has is_admin=1 in the database.
        Never allows public registrations to elevate or overwrite admin credentials.
        """
        clean_username = username.lower().strip()
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        try:
            cursor.execute("SELECT id, password_hash, salt, is_admin FROM users WHERE LOWER(username) = ?", (clean_username,))
            row = cursor.fetchone()
            if row:
                user_id = row["id"]
                # Ensure is_admin is TRUE in the database
                cursor.execute("UPDATE users SET is_admin = TRUE, updated_at = ? WHERE id = ?", (now, user_id))
                # If a new password is provided, update hash using Argon2id
                if password and len(password) >= 10:
                    pwd_hash, salt = hash_password(password)
                    cursor.execute("UPDATE users SET password_hash = ?, salt = ?, updated_at = ? WHERE id = ?", (pwd_hash, salt, now, user_id))
                conn.commit()
                return Repository.get_user_by_id(user_id)
            else:
                # Create the administrator account directly
                if settings.ENVIRONMENT == "production":
                    if not password or len(password) < 10:
                        raise RuntimeError(
                            "ADMIN_PASSWORD environment variable (at least 10 characters) is required to provision administrator in production."
                        )
                    effective_password = password
                else:
                    if password and len(password) >= 10:
                        effective_password = password
                    else:
                        logger.warning("No valid ADMIN_PASSWORD configured; skipping administrator auto-provisioning in development.")
                        return None

                pwd_hash, salt = hash_password(effective_password)
                user_id = str(uuid.uuid4())
                cursor.execute(
                    """INSERT INTO users (id, username, email, password_hash, salt, display_name, is_admin, is_email_verified, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, TRUE, TRUE, ?, ?)""",
                    (user_id, clean_username, None, pwd_hash, salt, "Administrator", now, now)
                )
                cursor.execute(
                    "INSERT INTO profiles (id, display_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (user_id, "Administrator", now, now)
                )
                cursor.execute(
                    "INSERT INTO report_credits (id, user_id, credits_remaining, credits_used, updated_at) VALUES (?, ?, 100, 0, ?)",
                    (str(uuid.uuid4()), user_id, now)
                )
                conn.commit()
                return Repository.get_user_by_id(user_id)
        except RuntimeError:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to provision administrator: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_payment_by_order_id(razorpay_order_id: str) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM payments WHERE razorpay_order_id = ?", (razorpay_order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_payment_by_idempotency_key(user_id: str, idempotency_key: str) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM payments WHERE user_id = ? AND idempotency_key = ?", (user_id, idempotency_key))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def record_payment_order(
        user_id: str,
        razorpay_order_id: str,
        amount_paise: int,
        amount_inr: float,
        idempotency_key: str | None = None
    ) -> dict[str, Any] | None:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        order_uuid = str(uuid.uuid4())
        try:
            if idempotency_key:
                cursor.execute(
                    "SELECT * FROM payments WHERE user_id = ? AND idempotency_key = ?",
                    (user_id, idempotency_key)
                )
                existing_key = cursor.fetchone()
                if existing_key:
                    return dict(existing_key)

            cursor.execute("SELECT * FROM payments WHERE razorpay_order_id = ?", (razorpay_order_id,))
            existing = cursor.fetchone()
            if existing:
                return dict(existing)

            cursor.execute(
                """INSERT INTO payments (id, user_id, razorpay_order_id, razorpay_payment_id, razorpay_signature, amount_paise, amount_inr, status, idempotency_key, created_at, updated_at)
                   VALUES (?, ?, ?, NULL, NULL, ?, ?, 'created', ?, ?, ?)""",
                (order_uuid, user_id, razorpay_order_id, amount_paise, amount_inr, idempotency_key, now, now)
            )
            conn.commit()
            return {
                "id": order_uuid,
                "user_id": user_id,
                "razorpay_order_id": razorpay_order_id,
                "amount_paise": amount_paise,
                "amount_inr": amount_inr,
                "status": "created",
                "idempotency_key": idempotency_key
            }
        except Exception as e:
            conn.rollback()
            # If concurrent insert with same idempotency key succeeded, return existing
            if idempotency_key:
                try:
                    cursor.execute(
                        "SELECT * FROM payments WHERE user_id = ? AND idempotency_key = ?",
                        (user_id, idempotency_key)
                    )
                    existing_key = cursor.fetchone()
                    if existing_key:
                        return dict(existing_key)
                except Exception:
                    pass
            logger.error(f"Failed to record payment order: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def verify_and_complete_payment(
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        expected_user_id: str | None = None,
        expected_amount_paise: int | None = None
    ) -> tuple[bool, str]:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        try:
            cursor.execute(
                "SELECT id, user_id, status, amount_paise, razorpay_payment_id, razorpay_signature FROM payments WHERE razorpay_order_id = ?",
                (razorpay_order_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False, "Order not found."

            if expected_user_id and row["user_id"] != expected_user_id:
                return False, "Order does not belong to the authenticated user."

            if expected_amount_paise is not None and row["amount_paise"] != expected_amount_paise:
                return False, f"Order amount mismatch: expected {expected_amount_paise}, got {row['amount_paise']}."

            if row["status"] == "paid":
                # Idempotency check: verify that the payment ID matches the original payment
                if row["razorpay_payment_id"] == razorpay_payment_id:
                    return True, "Payment already verified successfully."
                else:
                    logger.warning(
                        f"Inconsistent payment verification attempt: order {razorpay_order_id} "
                        f"was paid with {row['razorpay_payment_id']}, but received {razorpay_payment_id}"
                    )
                    return False, "Conflicting payment ID for already-paid order."

            if row["status"] != "created":
                return False, f"Order is in invalid state '{row['status']}' for completion."

            # Concurrency-safe atomic state transition:
            cursor.execute(
                """UPDATE payments
                   SET status = 'paid', razorpay_payment_id = ?, razorpay_signature = ?, updated_at = ?
                   WHERE razorpay_order_id = ? AND status = 'created'""",
                (razorpay_payment_id, razorpay_signature, now, razorpay_order_id)
            )

            if cursor.rowcount > 0:
                # Atomically grant exactly 1 credit in the same transaction
                cursor.execute(
                    "UPDATE report_credits SET credits_remaining = credits_remaining + 1, updated_at = ? WHERE user_id = ?",
                    (now, row["user_id"])
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        "INSERT INTO report_credits (id, user_id, credits_remaining, credits_used, updated_at) VALUES (?, ?, 1, 0, ?)",
                        (str(uuid.uuid4()), row["user_id"], now)
                    )
                conn.commit()
                return True, "Payment verified successfully and credit granted."
            else:
                # Concurrent transaction already updated the order. Roll back and re-check.
                conn.rollback()
                cursor.execute(
                    "SELECT status, razorpay_payment_id FROM payments WHERE razorpay_order_id = ?",
                    (razorpay_order_id,)
                )
                concurrent_row = cursor.fetchone()
                if concurrent_row and concurrent_row["status"] == "paid" and concurrent_row["razorpay_payment_id"] == razorpay_payment_id:
                    return True, "Payment already completed by concurrent request."
                return False, "Concurrent update conflict."
        except Exception as e:
            conn.rollback()
            logger.error(f"Error in verify_and_complete_payment: {e}")
            return False, f"Database transaction failed: {e}"
        finally:
            conn.close()

    @staticmethod
    def get_admin_analytics() -> dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM search_history")
            total_searches = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM reports")
            total_reports = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'paid'")
            successful_payments = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(amount_inr), 0) FROM payments WHERE status = 'paid'")
            total_revenue_inr = float(cursor.fetchone()[0])

            cursor.execute("SELECT COALESCE(SUM(credits_used), 0) FROM report_credits")
            credits_used = cursor.fetchone()[0]

            # Real live data records (no mock data)
            cursor.execute(
                """SELECT id, username, email, display_name, is_admin, is_email_verified, created_at
                   FROM users ORDER BY created_at DESC LIMIT 10"""
            )
            reg_rows = cursor.fetchall()
            recent_registrations = [
                {
                    "id": r["id"],
                    "username": r["username"] if "username" in r.keys() and r["username"] else (r["email"].split("@")[0] if "email" in r.keys() and r["email"] else "user"),
                    "email": r["email"] if "email" in r.keys() else None,
                    "display_name": r["display_name"] if "display_name" in r.keys() else None,
                    "is_admin": bool(r["is_admin"]) if "is_admin" in r.keys() and r["is_admin"] is not None else False,
                    "is_email_verified": bool(r["is_email_verified"]) if "is_email_verified" in r.keys() else True,
                    "created_at": r["created_at"] if "created_at" in r.keys() else None
                }
                for r in reg_rows
            ]

            cursor.execute(
                """SELECT id, user_id, title, locality_name, lat, lng, created_at, status
                   FROM reports ORDER BY created_at DESC LIMIT 10"""
            )
            rep_rows = cursor.fetchall()
            recent_reports = [
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "title": r["title"] or r["locality_name"],
                    "locality_name": r["locality_name"],
                    "lat": r["lat"],
                    "lng": r["lng"],
                    "created_at": r["created_at"],
                    "status": r["status"]
                }
                for r in rep_rows
            ]

            cursor.execute(
                """SELECT id, user_id, razorpay_order_id, razorpay_payment_id, amount_inr, status, created_at
                   FROM payments ORDER BY created_at DESC LIMIT 10"""
            )
            pay_rows = cursor.fetchall()
            recent_payments = [
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "razorpay_order_id": r["razorpay_order_id"],
                    "razorpay_payment_id": r["razorpay_payment_id"],
                    "amount_inr": r["amount_inr"],
                    "status": r["status"],
                    "created_at": r["created_at"]
                }
                for r in pay_rows
            ]

            return {
                "users": {
                    "total_registered": total_users,
                    "recent_registrations": recent_registrations
                },
                "activity": {
                    "total_searches": total_searches,
                    "total_reports_generated": total_reports,
                    "total_report_credits_used": credits_used,
                    "recent_reports": recent_reports
                },
                "payments": {
                    "successful_orders": successful_payments,
                    "total_revenue_inr": total_revenue_inr,
                    "report_price_inr": 29,
                    "recent_payments": recent_payments
                }
            }
        finally:
            conn.close()
