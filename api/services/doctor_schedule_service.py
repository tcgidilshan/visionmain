from ..models import Schedule, Doctor, Branch, Appointment
from django.utils import timezone
from django.db import IntegrityError
from django.db import transaction
from django.utils.dateparse import parse_date
from datetime import datetime
from ..serializers import ScheduleSerializer

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
        Transfers the doctor's schedule from `from_date` to `to_date`.
        Handles different times on the same date.
        """

        # Step 1: Ensure the original schedule exists
        old_schedules = Schedule.objects.filter(
            doctor_id=doctor_id,
            date=from_date,
            branch_id=branch_id
        )

        if not old_schedules.exists():
            raise ValueError(f"No schedule found for doctor {doctor_id} on {from_date} at branch {branch_id}.")

        updated_appointments = []  # Track updated appointments
        new_schedules = []  # List to store newly created schedules

        for old_schedule in old_schedules:
            # Step 2: Create a new schedule for the doctor on the target date (same time)
            new_schedule, created = Schedule.objects.get_or_create(
                doctor_id=doctor_id,
                date=to_date,
                start_time=old_schedule.start_time,
                branch_id=branch_id,
                defaults={'status': old_schedule.status}
            )

            if created:
                new_schedules.append(new_schedule)
                print(f"✅ Created new schedule for {to_date}")
            else:
                print(f"⚠️ Reusing existing schedule for {to_date}")

            # Step 3: Update all appointments linked to the old schedule
            appointments = Appointment.objects.filter(schedule=old_schedule)
            for appointment in appointments:
                appointment.schedule = new_schedule  # Link the appointment to the new schedule
                appointment.status = 'Rescheduled'  # Mark the appointment as rescheduled
                appointment.save()  # Explicitly saving the appointment here
                updated_appointments.append(appointment)

            # Optionally mark the old schedule as transferred
            old_schedule.status = "Transferred"
            old_schedule.save()  # Ensure we save the old schedule after marking it as transferred

        # Return all the newly created schedules and the updated appointments
        return {
            "new_schedules": new_schedules,
            "updated_appointments": updated_appointments
        }
