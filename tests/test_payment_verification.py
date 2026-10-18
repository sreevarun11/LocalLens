import unittest
import uuid
import hmac
import hashlib
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.db.repository import Repository
from backend.app.db.local_db import get_connection
from backend.app.auth.tokens import create_access_token

client = TestClient(app)

class TestPaymentVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test users
        cls.user_a_name = f"pay_user_a_{uuid.uuid4().hex[:8]}"
        cls.user_a = Repository.create_user(
            username=cls.user_a_name,
            password="StrongPassword123!",
            display_name="Payment User Alpha",
            email=f"{cls.user_a_name}@example.com",
            is_admin=False,
            is_email_verified=True
        )
        cls.token_a = create_access_token(
            user_id=cls.user_a["id"],
            username_or_email=cls.user_a_name,
            is_email_verified=True,
            is_admin=False
        )

        cls.user_b_name = f"pay_user_b_{uuid.uuid4().hex[:8]}"
        cls.user_b = Repository.create_user(
            username=cls.user_b_name,
            password="StrongPassword123!",
            display_name="Payment User Beta",
            email=f"{cls.user_b_name}@example.com",
            is_admin=False,
            is_email_verified=True
        )
        cls.token_b = create_access_token(
            user_id=cls.user_b["id"],
            username_or_email=cls.user_b_name,
            is_email_verified=True,
            is_admin=False
        )

    def _generate_signature(self, order_id: str, payment_id: str, secret: str) -> str:
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def test_01_invalid_signature_rejected(self):
        """Cryptographic signature mismatch must return HTTP 400 Bad Request."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        secret = "test_secret_for_validation_123"
        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=2900,
            amount_inr=29.0
        )

        headers = {"Authorization": f"Bearer {self.token_a}"}
        payload = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": f"pay_{uuid.uuid4().hex[:12]}",
            "razorpay_signature": "invalid_forged_signature_hex"
        }

        with patch.object(settings, "RAZORPAY_KEY_SECRET", secret):
            resp = client.post("/api/payments/verify-payment", json=payload, headers=headers)
            self.assertEqual(resp.status_code, 400)
            self.assertIn("signature verification failed", resp.json()["error"]["message"])

    def test_02_wrong_user_order_rejected(self):
        """User B must be rejected when attempting to verify an order owned by User A."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        secret = "test_secret_for_validation_123"
        signature = self._generate_signature(order_id, payment_id, secret)

        # Recorded for user_a
        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=2900,
            amount_inr=29.0
        )

        # Request made by user_b
        headers_b = {"Authorization": f"Bearer {self.token_b}"}
        payload = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        with patch.object(settings, "RAZORPAY_KEY_SECRET", secret):
            resp = client.post("/api/payments/verify-payment", json=payload, headers=headers_b)
            self.assertEqual(resp.status_code, 400)
            self.assertIn("could not be processed", resp.json()["error"]["message"])
            self.assertIn("does not belong", resp.json()["error"]["message"])

    def test_03_unknown_order_rejected(self):
        """Verifying a non-existent order ID must return HTTP 400 Bad Request."""
        order_id = f"order_nonexistent_{uuid.uuid4().hex[:10]}"
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        secret = "test_secret_for_validation_123"
        signature = self._generate_signature(order_id, payment_id, secret)

        headers = {"Authorization": f"Bearer {self.token_a}"}
        payload = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        with patch.object(settings, "RAZORPAY_KEY_SECRET", secret):
            resp = client.post("/api/payments/verify-payment", json=payload, headers=headers)
            self.assertEqual(resp.status_code, 400)
            self.assertIn("could not be processed", resp.json()["error"]["message"])
            self.assertIn("not found", resp.json()["error"]["message"])

    def test_04_repeated_verification_idempotent(self):
        """Repeated verification of the same payment ID is idempotent and grants credit only once."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        secret = "test_secret_for_validation_123"
        signature = self._generate_signature(order_id, payment_id, secret)

        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=2900,
            amount_inr=29.0
        )

        headers = {"Authorization": f"Bearer {self.token_a}"}
        payload = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        with patch.object(settings, "RAZORPAY_KEY_SECRET", secret):
            initial_credits = Repository.get_credits(self.user_a["id"])["credits_remaining"]

            # First verification
            resp1 = client.post("/api/payments/verify-payment", json=payload, headers=headers)
            self.assertEqual(resp1.status_code, 200)
            self.assertTrue(resp1.json()["success"])
            credits_after_first = Repository.get_credits(self.user_a["id"])["credits_remaining"]
            self.assertEqual(credits_after_first, initial_credits + 1)

            # Second verification (replay)
            resp2 = client.post("/api/payments/verify-payment", json=payload, headers=headers)
            self.assertEqual(resp2.status_code, 200)
            self.assertTrue(resp2.json()["success"])
            credits_after_second = Repository.get_credits(self.user_a["id"])["credits_remaining"]
            self.assertEqual(credits_after_second, initial_credits + 1, "Duplicate verification must NOT increment credits twice")

    def test_05_conflicting_payment_id_rejected(self):
        """Re-verifying an already-paid order with a DIFFERENT payment ID must be rejected with HTTP 400."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        payment_id_1 = f"pay_{uuid.uuid4().hex[:12]}"
        payment_id_2 = f"pay_{uuid.uuid4().hex[:12]}"
        secret = "test_secret_for_validation_123"
        sig_1 = self._generate_signature(order_id, payment_id_1, secret)
        sig_2 = self._generate_signature(order_id, payment_id_2, secret)

        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=2900,
            amount_inr=29.0
        )

        headers = {"Authorization": f"Bearer {self.token_a}"}
        payload_1 = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id_1,
            "razorpay_signature": sig_1
        }
        payload_2 = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id_2,
            "razorpay_signature": sig_2
        }

        with patch.object(settings, "RAZORPAY_KEY_SECRET", secret):
            # 1. Complete order with payment_id_1
            resp1 = client.post("/api/payments/verify-payment", json=payload_1, headers=headers)
            self.assertEqual(resp1.status_code, 200)

            credits_before = Repository.get_credits(self.user_a["id"])["credits_remaining"]

            # 2. Attempt verification with payment_id_2 on same order
            resp2 = client.post("/api/payments/verify-payment", json=payload_2, headers=headers)
            self.assertEqual(resp2.status_code, 400)
            self.assertIn("could not be processed", resp2.json()["error"]["message"])
            self.assertIn("Conflicting payment ID", resp2.json()["error"]["message"])

            credits_after = Repository.get_credits(self.user_a["id"])["credits_remaining"]
            self.assertEqual(credits_after, credits_before, "No credits awarded for conflicting payment ID")

    def test_06_order_amount_mismatch_rejected(self):
        """An order with an unexpected amount (e.g. tampered 100 paise) must be rejected."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        secret = "test_secret_for_validation_123"
        signature = self._generate_signature(order_id, payment_id, secret)

        # Record order with invalid amount (100 paise instead of 2900)
        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=100,
            amount_inr=1.0
        )

        headers = {"Authorization": f"Bearer {self.token_a}"}
        payload = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        with patch.object(settings, "RAZORPAY_KEY_SECRET", secret):
            resp = client.post("/api/payments/verify-payment", json=payload, headers=headers)
            self.assertEqual(resp.status_code, 400)
            self.assertIn("could not be processed", resp.json()["error"]["message"])
            self.assertIn("amount mismatch", resp.json()["error"]["message"])

    def test_07_invalid_order_status_rejected(self):
        """Orders in non-payable state ('cancelled', 'failed') must not be verified."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        secret = "test_secret_for_validation_123"
        signature = self._generate_signature(order_id, payment_id, secret)

        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=2900,
            amount_inr=29.0
        )

        # Manually update status to 'cancelled' in DB
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE payments SET status = 'cancelled' WHERE razorpay_order_id = ?", (order_id,))
        conn.commit()
        conn.close()

        headers = {"Authorization": f"Bearer {self.token_a}"}
        payload = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        with patch.object(settings, "RAZORPAY_KEY_SECRET", secret):
            resp = client.post("/api/payments/verify-payment", json=payload, headers=headers)
            self.assertEqual(resp.status_code, 400)
            self.assertIn("could not be processed", resp.json()["error"]["message"])
            self.assertIn("invalid state", resp.json()["error"]["message"])

    def test_08_idempotency_key_prevents_duplicate_order_creation(self):
        """Submitting duplicate create-order requests with the same idempotency_key returns the same order."""
        # Set user credits to 0 so order creation is triggered
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE report_credits SET credits_remaining = 0 WHERE user_id = ?", (self.user_a["id"],))
        conn.commit()
        conn.close()

        headers = {"Authorization": f"Bearer {self.token_a}"}
        idempotency_key = f"idem_key_{uuid.uuid4().hex[:12]}"

        # First creation call
        resp1 = client.post("/api/payments/create-order", json={"idempotency_key": idempotency_key}, headers=headers)
        self.assertEqual(resp1.status_code, 200)
        order_id_1 = resp1.json()["order_id"]

        # Second creation call with identical idempotency_key
        resp2 = client.post("/api/payments/create-order", json={"idempotency_key": idempotency_key}, headers=headers)
        self.assertEqual(resp2.status_code, 200)
        order_id_2 = resp2.json()["order_id"]

        self.assertEqual(order_id_1, order_id_2, "Identical idempotency_key must return the same order ID")

        # Verify only 1 row exists in payments table with that idempotency_key
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM payments WHERE idempotency_key = ?", (idempotency_key,))
        count = cur.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1, "Exactly one order row must exist for the idempotency key")

    def test_09_concurrent_verification_safe_single_credit(self):
        """Concurrent verification calls from multiple threads must grant exactly 1 credit."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        secret = "test_secret_for_validation_123"
        signature = self._generate_signature(order_id, payment_id, secret)

        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=2900,
            amount_inr=29.0
        )

        initial_credits = Repository.get_credits(self.user_a["id"])["credits_remaining"]

        def _verify_worker():
            return Repository.verify_and_complete_payment(
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature=signature,
                expected_user_id=self.user_a["id"],
                expected_amount_paise=2900
            )

        # Run 8 concurrent threads attempting verification
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(_verify_worker) for _ in range(8)]
            results = [f.result() for f in futures]

        # Verify all threads received True (either initial or idempotent success)
        for success, message in results:
            self.assertTrue(success, f"Concurrent verification failed: {message}")

        final_credits = Repository.get_credits(self.user_a["id"])["credits_remaining"]
        self.assertEqual(
            final_credits,
            initial_credits + 1,
            f"Exactly 1 credit must be granted despite 8 concurrent workers. Got {final_credits - initial_credits}"
        )

    def test_10_database_rollback_on_credit_grant_failure(self):
        """If credit update fails, transaction must roll back without setting order to 'paid'."""
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        signature = "sig_dummy_123"

        Repository.record_payment_order(
            user_id=self.user_a["id"],
            razorpay_order_id=order_id,
            amount_paise=2900,
            amount_inr=29.0
        )

        initial_credits = Repository.get_credits(self.user_a["id"])["credits_remaining"]

        # Simulate exception during the credit grant execution inside the transaction
        original_get_conn = get_connection
        def _failing_connection():
            conn = original_get_conn()
            original_cursor = conn.cursor
            def _failing_cursor():
                cur = original_cursor()
                original_execute = cur.execute
                def _execute_hook(query, params=None):
                    if "UPDATE report_credits" in query:
                        raise RuntimeError("Simulated database failure during credit update")
                    return original_execute(query, params)
                cur.execute = _execute_hook
                return cur
            conn.cursor = _failing_cursor
            return conn

        with patch("backend.app.db.repository.get_connection", side_effect=_failing_connection):
            success, message = Repository.verify_and_complete_payment(
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature=signature,
                expected_user_id=self.user_a["id"],
                expected_amount_paise=2900
            )
            self.assertFalse(success)
            self.assertIn("Simulated database failure", message)

        # Verify that rollback restored order status to 'created'
        order = Repository.get_payment_by_order_id(order_id)
        self.assertIsNotNone(order)
        self.assertEqual(order["status"], "created", "Order status must remain 'created' after rollback")

        # Verify user credits did not change
        final_credits = Repository.get_credits(self.user_a["id"])["credits_remaining"]
        self.assertEqual(final_credits, initial_credits, "Credits must not change when transaction rolls back")

if __name__ == "__main__":
    unittest.main()
