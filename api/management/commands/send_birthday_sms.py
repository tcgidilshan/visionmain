from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from api.models import Patient
from api.services.send_sms_service import SMSService


class Command(BaseCommand):
    help = 'Send birthday SMS to patients whose birthday is today (Asia/Colombo time)'

    def handle(self, *args, **options):
        today = timezone.localdate()
        self.stdout.write(f"[send_birthday_sms] Running for date: {today}")

        patients = Patient.objects.filter(
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
        ).exclude(phone_number__isnull=True).exclude(phone_number='')

        if not patients.exists():
            self.stdout.write(self.style.WARNING("No birthday patients found for today."))
            return

        self.stdout.write(f"Found {patients.count()} patient(s) with birthdays today.")

        recipients = [
            {"mobile": p.phone_number, "customer_name": p.name}
            for p in patients
        ]

        try:
            results = SMSService.send_sms_by_template_type('birthday', recipients)
            sent = sum(1 for r in results if r.get('status') == 'sent')
            failed = len(results) - sent
            self.stdout.write(self.style.SUCCESS(
                f"Done. Sent: {sent}, Failed/Error: {failed}. All attempts logged to SMSLog."
            ))
        except ValidationError as e:
            self.stdout.write(self.style.ERROR(f"No active birthday SMS template found: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
