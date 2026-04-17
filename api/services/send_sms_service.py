import time
import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

from ..models import SMSToken, SMSTemplate, SMSLog

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
    def send_sms(
        mobile_numbers: list,
        message: str,
        source_address: str = None,
        template=None,
        template_type: str = None,
    ) -> dict:
        """
        Send SMS to one or more mobile numbers via Dialog eSMS API v2.

        mobile_numbers : list of strings, e.g. ["714551682", "763625800"]
        message        : SMS body text
        source_address : optional sender mask (max 11 chars)
        template       : SMSTemplate instance (for logging FK)
        template_type  : template type string snapshot (for logging)

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

        log_defaults = dict(
            message=message,
            source_address=source_address or None,
            template=template,
            template_type=template_type,
            transaction_id=transaction_id,
        )

        try:
            resp = requests.post(SEND_SMS_URL, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            for num in mobile_numbers:
                SMSLog.objects.create(
                    mobile_number=num,
                    status=SMSLog.Status.ERROR,
                    comment=str(e),
                    **log_defaults,
                )
            raise ValidationError(f"SMS send request failed: {e}")

        data = resp.json()
        if data.get("status") != "success":
            api_data = data.get("data") or {}
            for num in mobile_numbers:
                SMSLog.objects.create(
                    mobile_number=num,
                    status=SMSLog.Status.FAILED,
                    err_code=str(data.get("errCode") or ""),
                    comment=data.get("comment", ""),
                    **log_defaults,
                )
            raise ValidationError(
                f"SMS send failed: {data.get('comment', 'Unknown error')} "
                f"(errCode={data.get('errCode')})"
            )

        api_data = data.get("data") or {}
        for num in mobile_numbers:
            SMSLog.objects.create(
                mobile_number=num,
                status=SMSLog.Status.SUCCESS,
                campaign_id=api_data.get("campaignId"),
                campaign_cost=api_data.get("campaignCost"),
                wallet_balance=str(api_data.get("walletBalance") or ""),
                duplicates_removed=api_data.get("duplicatesRemoved", 0),
                invalid_numbers=api_data.get("invalidNumbers", 0),
                mask_blocked_numbers=api_data.get("mask_blocked_numbers", 0),
                err_code=str(data.get("errCode") or ""),
                comment=data.get("comment", ""),
                **log_defaults,
            )

        return data

    @staticmethod
    def _substitute(template_text: str, context: dict) -> str:
        """Replace {key} placeholders in template_text using context dict."""
        message = template_text
        for key, value in context.items():
            message = message.replace(f"{{{key}}}", str(value) if value is not None else "")
        return message

    @staticmethod
    def send_sms_by_template_type(
        template_type: str,
        recipients: list,
    ) -> list:
        """
        Resolve the active template, personalise per recipient, and send.

        template_type : one of SMSTemplate.TemplateType values
                        ('birthday', 'issue_to_customer', 'order_ready')

        recipients    : list of dicts — each dict must have a 'mobile' key;
                        all other keys are treated as placeholder context.
                        Example:
                        [
                          {
                            "mobile": "714551682",
                            "customer_name": "John Silva",
                            "branch_name": "Colombo 03",
                            "branch_address": "123 Main St",
                            "branch_contact_number": "0112345678",
                            "invoice_number": "INV-00042",
                          },
                          {
                            "mobile": "763625800",
                            "customer_name": "Nimal Perera",
                            "invoice_number": "INV-00043",
                          },
                        ]

        Returns a list of per-recipient result dicts:
          [{"mobile": "...", "status": "sent", "result": {...}}, ...]
          or {"mobile": "...", "status": "error", "error": "..."} on failure.

        Raises ValidationError if no active template is found.
        """
        template = SMSTemplate.objects.filter(
            template_type=template_type, active=True
        ).first()

        if not template:
            raise ValidationError(
                f"No active SMS template found for type '{template_type}'."
            )

        results = []
        for recipient in recipients:
            mobile = recipient.get("mobile")
            if not mobile:
                results.append({"mobile": None, "status": "error", "error": "missing 'mobile' field"})
                continue

            context = {k: v for k, v in recipient.items() if k != "mobile"}
            message = SMSService._substitute(template.template, context)

            try:
                result = SMSService.send_sms(
                    [mobile],
                    message,
                    template.source_address or None,
                    template=template,
                    template_type=template.template_type,
                )
                results.append({"mobile": mobile, "status": "sent", "result": result})
            except Exception as e:
                results.append({"mobile": mobile, "status": "error", "error": str(e)})

        return results
