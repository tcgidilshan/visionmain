# services/channel_transfer_service.py
from django.db import transaction
from ..models import Appointment, Schedule

class ChannelTransferService:
    @staticmethod
    @transaction.atomic
    def transfer_appointment(appointment_id, new_doctor_id, new_date, new_time, branch_id):
        try:
            # Step 1: Fetch Original Appointment
            appointment = Appointment.objects.select_related("schedule", "doctor", "branch").get(id=appointment_id)

            # Step 2: Determine Doctor
            doctor_id = new_doctor_id or appointment.doctor_id

            # Step 3: Get/Create Schedule
            schedule, _ = Schedule.objects.get_or_create(
                doctor_id=doctor_id,
                date=new_date,
                start_time=new_time,
                branch_id=branch_id,
                defaults={"status": "Available"}
            )

            # Step 4: Calculate new channel number for the date & branch
            appointments_on_date = Appointment.objects.filter(date=new_date, branch_id=branch_id).count()
            new_channel_no = appointments_on_date + 1

            # Step 5: Update appointment
            appointment.schedule = schedule
            appointment.doctor_id = doctor_id
            appointment.date = new_date
            appointment.time = new_time
            appointment.branch_id = branch_id
            appointment.channel_no = new_channel_no
            appointment.save()

            return appointment

        except Appointment.DoesNotExist:
            raise ValueError("Appointment not found.")
        except Exception as e:
            raise ValueError(f"Transfer failed: {str(e)}")
