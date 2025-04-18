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
        Transfers the doctor's schedule from one date to another. It ensures the schedule exists
        on the original date and performs the transfer to the new date. 
        """
        # Step 1: Validate that a schedule exists for the given doctor, from_date, and branch_id
        try:
            # Find the schedule for the specified doctor, date, and branch
            old_schedule = Schedule.objects.get(
                doctor_id=doctor_id,
                date=from_date,
                branch_id=branch_id
            )
            print(f"Found schedule: {old_schedule}")

        except Schedule.DoesNotExist:
            # If no schedule is found, raise an error
            print(f"Schedule not found for doctor {doctor_id} on {from_date} at branch {branch_id}")
            raise ValueError("Original schedule does not exist.")

        # Step 2: Create a new schedule for the doctor on the target date
        # The new schedule will have the same doctor, branch, and status as the original one
        new_schedule = Schedule(
            doctor_id=doctor_id,
            date=to_date,
            start_time=old_schedule.start_time,  # You can also update the start_time if needed
            status=old_schedule.status,  # Retain the status of the original schedule
            branch_id=branch_id  # Ensure it’s assigned to the correct branch
        )
        new_schedule.save()

        print(f"Transferred schedule to new date: {new_schedule}")

        # Step 3: Optional - Update the status of the old schedule (if needed)
        old_schedule.status = "Transferred"  # You can set this status as per the requirement
        old_schedule.save()

        # Return the new schedule details (can also return the old schedule if needed)
        return new_schedule