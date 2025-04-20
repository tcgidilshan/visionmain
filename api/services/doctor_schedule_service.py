from ..models import Schedule, Doctor, Branch, Appointment
from django.utils import timezone
from django.db import IntegrityError
from django.db import transaction
from django.utils.dateparse import parse_date
from datetime import datetime

class DoctorScheduleService:
    
    @staticmethod
    def add_arrival_day(doctor_id, date, start_time, branch_id):
        doctor = Doctor.objects.get(id=doctor_id)
        branch = Branch.objects.get(id=branch_id)

        schedule, created = Schedule.objects.get_or_create(
            doctor=doctor,
            date=date,
            start_time=start_time,
            branch=branch,
            defaults={"status": "Available"}
        )

        return schedule, created

    @staticmethod
    def get_upcoming_arrival_days(doctor_id, branch=None):
        """
        Get all upcoming arrival days for a doctor. Optionally filtered by branch.
        """
        qs = Schedule.objects.filter(doctor_id=doctor_id, date__gte=timezone.now().date())

        if branch:
            qs = qs.filter(branch=branch)

        return qs.order_by('date')
    
    @staticmethod
    @transaction.atomic
    def transfer_schedule(doctor_id, from_date, to_date, branch_id):
        """
        Transfers a doctor's schedule from `from_date` to `to_date`.
        If a schedule already exists at `to_date`, it will reuse it.
        """

        # Step 1: Ensure the original schedule exists
        try:
            old_schedule = Schedule.objects.get(
                doctor_id=doctor_id,
                date=from_date,
                branch_id=branch_id
            )
        except Schedule.DoesNotExist:
            raise ValueError("Original schedule does not exist.")

        # Step 2: Check if a schedule already exists on the target date
        new_schedule, created = Schedule.objects.get_or_create(
            doctor_id=doctor_id,
            date=to_date,
            start_time=old_schedule.start_time,
            branch_id=branch_id,
            defaults={'status': old_schedule.status}
        )

        if created:
            print(f"✅ Created new schedule for {to_date}")
        else:
            print(f"⚠️ Reusing existing schedule for {to_date}")

        # Step 3: Optionally mark the old schedule
        old_schedule.status = "Transferred"
        old_schedule.save()

        return new_schedule
