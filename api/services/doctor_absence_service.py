from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from ..models import Appointment, Schedule
from ..serializers import AppointmentSerializer

class DoctorAbsenceService:
    @staticmethod
    @transaction.atomic
    def reschedule_appointments(doctor_id, from_date, to_date):
        """
        Reschedules all appointments for a doctor between from_date and to_date.
        Moves them to the next available schedule (per day per appointment).
        """

        # Step 1: Get all appointments in range
        appointments = Appointment.objects.filter(
            doctor_id=doctor_id,
            date__range=[from_date, to_date],
        )

        if not appointments.exists():
            return {"count": 0, "appointments": []}

        rescheduled_data = []
        updated_count = 0

        for appointment in appointments:
            current_schedule = appointment.schedule
            original_date = appointment.date
            original_time = appointment.time
            branch_id = appointment.branch_id

            # Step 2: Look for the next available schedule
            next_schedule = Schedule.objects.filter(
                doctor_id=doctor_id,
                date__gt=to_date,
                start_time=original_time,
                branch_id=branch_id,
                # status=Schedule.StatusChoices.AVAILABLE
            ).order_by('date', 'start_time').first()

            if not next_schedule:
                continue  # Skip if no upcoming schedule available

            # Step 3: Update appointment
            appointment.date = next_schedule.date
            appointment.schedule = next_schedule
            appointment.status = 'Rescheduled'
            appointment.save()

            # Step 4: Mark the new schedule as booked
            next_schedule.status = Schedule.StatusChoices.BOOKED
            next_schedule.save()

            # Track results
            rescheduled_data.append(AppointmentSerializer(appointment).data)
            updated_count += 1

        return {
            "count": updated_count,
            "appointments": rescheduled_data
        }
