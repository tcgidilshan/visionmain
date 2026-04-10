import time
import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

from ..models import SMSToken

LOGIN_URL = "https://esms.dialog.lk/api/v2/user/login"
SEND_SMS_URL = "https://e-sms.dialog.lk/api/v2/sms"


class SMSService:

    @staticmethod
    def _get_valid_token() -> str:
        """Return a valid Bearer token, re-logging in only when expired or absent."""
        latest = SMSToken.objects.order_by('-created_at').first()

        if latest and latest.is_valid():
            return latest.token

        payload = {
            "username": settings.SMS_USER,
            "password": settings.SMS_PASSWORD,
        }
        try:
            resp = requests.post(LOGIN_URL, json=payload, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ValidationError(f"SMS login request failed: {e}")

        data = resp.json()
        if data.get("status") != "success":
            raise ValidationError(
                f"SMS login failed: {data.get('comment', 'Unknown error')} "
                f"(errCode={data.get('errCode')})"
            )

        SMSToken.objects.create(
            token=data["token"],
            refresh_token=data.get("refreshToken"),
            expiration_seconds=int(data.get("expiration", 43200)),
        )
        return data["token"]

    @staticmethod
    def send_sms(mobile_numbers: list, message: str, source_address: str = None) -> dict:
        """
        Send SMS to one or more mobile numbers via Dialog eSMS API v2.

        mobile_numbers : list of strings, e.g. ["714551682", "763625800"]
                         (9-digit format; 10/11-digit accepted by the API too)
        message        : SMS body text
        source_address : optional sender mask (max 11 chars)

        Returns the eSMS API response dict on success.
        Raises ValidationError on any failure.
        """
        token = SMSService._get_valid_token()

        # transaction_id must be a unique integer up to 18 digits
        transaction_id = int(time.time() * 1000) % (10 ** 18)

        msisdn = [{"mobile": num} for num in mobile_numbers]

        payload = {
            "msisdn": msisdn,
            "message": message,
            "transaction_id": transaction_id,
            "payment_method": 0,
        }
        if source_address:
            payload["sourceAddress"] = source_address

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(SEND_SMS_URL, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ValidationError(f"SMS send request failed: {e}")

        data = resp.json()
        if data.get("status") != "success":
            raise ValidationError(
                f"SMS send failed: {data.get('comment', 'Unknown error')} "
                f"(errCode={data.get('errCode')})"
            )

        return data
