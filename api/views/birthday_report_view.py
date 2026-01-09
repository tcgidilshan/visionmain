from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from api.models import Patient, OrderPayment, ChannelPayment, BirthdayReminder, Branch
from datetime import datetime
from django.utils import timezone
from api.services.pagination_service import PaginationService
from api.services.time_zone_convert_service import TimezoneConverterService

class BirthdayReportView(APIView):
    def get(self, request):
        date_param = request.query_params.get('date')
        if not date_param:
            return Response({"error": "Date parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Parse the date to extract month and day
            birthday_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            birthday_month = birthday_date.month
            birthday_day = birthday_date.day
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter patients by month and day only (ignore year)
        patients = Patient.objects.filter(
            date_of_birth__month=birthday_month,
            date_of_birth__day=birthday_day
        )
        
        # Set up pagination
        paginator = PaginationService()
        paginated_patients = paginator.paginate_queryset(patients, request)
        
        report_data = []
        for patient in paginated_patients:
            # Calculate total from Orders (sum of OrderPayment amounts)
            order_total = OrderPayment.objects.filter(
                order__customer=patient,
                is_deleted=False
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate total from Appointments (sum of ChannelPayment amounts)
            appointment_total = ChannelPayment.objects.filter(
                appointment__patient=patient,
                is_deleted=False
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate age based on the provided date parameter
            if patient.date_of_birth:
                age = birthday_date.year - patient.date_of_birth.year
                # Adjust if birthday hasn't occurred yet this year
                if (birthday_date.month, birthday_date.day) < (patient.date_of_birth.month, patient.date_of_birth.day):
                    age -= 1
            else:
                age = None
            
            # Get birthday reminder data for this patient created TODAY
            birthday_reminder_data = None
            
            # Use today's date to check if reminder was created today for this patient
            today_date = timezone.localdate().strftime('%Y-%m-%d')
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(
                today_date, None
            )
            
            if start_datetime and end_datetime:
                birthday_reminders = BirthdayReminder.objects.filter(
                    patient=patient,
                    created_at__range=(start_datetime, end_datetime)
                ).order_by('-created_at')
            else:
                birthday_reminders = []
            
            if birthday_reminders:
                birthday_reminder_data = []
                for reminder in birthday_reminders:
                    birthday_reminder_data.append({
                        'id': reminder.id,
                        'branch_id': reminder.branch.id if reminder.branch else None,
                        'branch_name': reminder.branch.branch_name if reminder.branch else None,
                        'is_sms_sent': reminder.is_sms_sent,
                        'sms_sent_at': reminder.sms_sent_at,
                        'called_at': reminder.called_at,
                        'created_at': reminder.created_at
                    })
            
            patient_data = {
                'id': patient.id,
                'name': patient.name,
                'date_of_birth': patient.date_of_birth,
                'age': age,
                'phone_number': patient.phone_number,
                'extra_phone_number': patient.extra_phone_number,
                'address': patient.address,
                'nic': patient.nic,
                'patient_note': patient.patient_note,
                'city': patient.city,
                'total_from_orders': order_total,
                'total_from_appointments': appointment_total,
                'grand_total': order_total + appointment_total,
                'birthday_reminder': birthday_reminder_data
            }
            report_data.append(patient_data)
        
        return paginator.get_paginated_response(report_data)

class BirthdayReminderCreateView(APIView):
    def post(self, request):
        patient_id = request.data.get('patient_id')
        branch_id = request.data.get('branch_id')
        
        if not patient_id:
            return Response({"error": "Patient ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        
        branch = None
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id)
            except Branch.DoesNotExist:
                return Response({"error": "Branch not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Create birthday reminder with current time
        birthday_reminder = BirthdayReminder.objects.create(
            patient=patient,
            branch=branch,
            called_at=timezone.now()
        )
        
        response_data = {
            'id': birthday_reminder.id,
            'patient_id': patient.id,
            'patient_name': patient.name,
            'branch_id': branch.id if branch else None,
            'branch_name': branch.branch_name if branch else None,
            'called_at': birthday_reminder.called_at,
            'created_at': birthday_reminder.created_at
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)