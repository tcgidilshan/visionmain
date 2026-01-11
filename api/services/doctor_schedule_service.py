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
            status=Schedule.StatusChoices.DOCTOR,
        )
        
        return schedule, created

    @staticmethod
    def get_upcoming_arrival_days(doctor_id, branch=None, status=None):
        """
        Get all upcoming arrival days for a doctor. Optionally filtered by branch and status.
        Status matching is case-insensitive.
        """
        qs = Schedule.objects.filter(doctor_id=doctor_id, date__gte=timezone.now().date())
        if branch:
            qs = qs.filter(branch=branch)
        if status:
            # Case-insensitive status matching
            qs = qs.filter(status__iexact=status)

        return qs.order_by('date')
    
    @staticmethod
    @transaction.atomic
    def transfer_schedules(doctor_id, from_date, to_date, branch_id):
        doctor = Doctor.objects.get(id=doctor_id)
        branch = Branch.objects.get(id=branch_id)

        # 🔹 1. Get active schedules for the from_date
        original_schedules = Schedule.objects.filter(
            doctor=doctor,
            date=from_date,
            branch=branch,
            status='DOCTOR'
        )

        if not original_schedules.exists():
            raise ValueError("No available schedules found on the given from_date for the specified branch.")

        new_schedules = []

        for schedule in original_schedules:
            # 🔸 2. Mark old schedule as Unavailable
            schedule.status = "Unavailable"
            schedule.save()

            # 🔸 3. Check if a schedule already exists for to_date with same time
            existing_schedule = Schedule.objects.filter(
                doctor=doctor,
                date=to_date,
                start_time=schedule.start_time,
                branch=branch
            ).first()

            if existing_schedule:
                # Update existing schedule to DOCTOR status
                existing_schedule.status = 'DOCTOR'
                existing_schedule.save()
                new_schedules.append(existing_schedule)
            else:
                # Create new schedule for to_date
                new_schedule = Schedule.objects.create(
                    doctor=doctor,
                    date=to_date,
                    start_time=schedule.start_time,
                    branch=branch,
                    status='DOCTOR'
                )
                new_schedules.append(new_schedule)

        return new_schedules
    
    @staticmethod
    def transfer_appointments_only(doctor_id, from_date, to_date, branch_id):
        doctor = Doctor.objects.get(id=doctor_id)
        branch = Branch.objects.get(id=branch_id)

        appointments = Appointment.objects.filter(
            doctor=doctor,
            date=from_date,
            branch=branch
        )

        if not appointments.exists():
            raise ValueError("No appointments found on the given from_date for the specified branch.")

        updated = []
        for appt in appointments:
            appt.date = to_date
            appt.status = "Confirmed"  # ✅ Force status update
            appt.save()
            updated.append(appt)

        return updated
