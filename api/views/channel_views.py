from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status,generics
from django.db import transaction
from ..models import Doctor, Patient, Schedule, Appointment, ChannelPayment
from ..serializers import PatientSerializer, ScheduleSerializer, AppointmentSerializer, ChannelPaymentSerializer,ChannelListSerializer,AppointmentDetailSerializer,AppointmentTimeListSerializer
from rest_framework.generics import ListAPIView
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ..services.doctor_schedule_service import DoctorScheduleService
from ..services.pagination_service import PaginationService
from ..services.patient_service import PatientService
from ..services.soft_delete_service import ChannelSoftDeleteService
from django.shortcuts import get_object_or_404
class ChannelAppointmentView(APIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data

        # Step 1: Validate Input
        required_fields = ['doctor_id', 'name', 'address', 'contact_number', 'channel_date', 'time', 'channeling_fee', 'branch_id', 'payments']
        for field in required_fields:
            if field not in data:
                return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Step 2: Handle Patient
            patient_payload = {
                "id": data.get("patient_id"),
                "name": data["name"],
                "phone_number": data["contact_number"],
                "address": data.get("address", "")
            }
            patient = PatientService.create_or_update_patient(patient_payload)

            # Step 3: Handle Schedule (Create If Not Exists)
            schedule, created = Schedule.objects.get_or_create(
                doctor_id=data['doctor_id'],
                date=data['channel_date'],
                start_time=data['time'],
                branch_id=data['branch_id'],
                defaults={'status': 'Available'}
            )

            if not created and schedule.status != 'Available':
                return Response({"error": "The selected schedule is not available."}, status=status.HTTP_400_BAD_REQUEST)

            # Step 4: Calculate channel number (branch + date specific)
            channel_date = data['channel_date']
            branch_id = data['branch_id']
            appointments_today = Appointment.objects.filter(date=channel_date, branch_id=branch_id).count()
            channel_no = appointments_today + 1

            # Step 5: Create Appointment
            appointment_data = {
                "doctor": data['doctor_id'],
                "patient": patient.id,
                "schedule": schedule.id,
                "date": data['channel_date'],
                "time": data['time'],
                "status": "Pending",
                "note": data.get('note', ''),
                "amount": data['channeling_fee'],
                "channel_no": channel_no,
                "branch": branch_id
            }

            appointment_serializer = AppointmentSerializer(data=appointment_data)
            appointment_serializer.is_valid(raise_exception=True)
            appointment = appointment_serializer.save()

            # Step 6: Handle Payments
            total_paid = 0
            payment_records = []
            for payment in data['payments']:
                payment_data = {
                    "appointment": appointment.id,
                    "amount": payment['amount'],
                    "payment_method": payment['payment_method'],
                    "is_final": False
                }
                total_paid += payment['amount']
                payment_serializer = ChannelPaymentSerializer(data=payment_data)
                payment_serializer.is_valid(raise_exception=True)
                payment_records.append(payment_serializer.save())

            # Step 7: Final Payment
            if total_paid == data['channeling_fee']:
                payment_records[-1].is_final = True
                payment_records[-1].save()
            elif total_paid > data['channeling_fee']:
                raise ValueError("Total payments exceed the channeling fee.")

            # Step 8: Update Schedule Status
            schedule.status = 'Booked'
            schedule.save()

            # Return Response
            return Response({
                "patient": PatientSerializer(patient).data,
                "schedule": ScheduleSerializer(schedule).data,
                "appointment": AppointmentSerializer(appointment).data,
                "payments": ChannelPaymentSerializer(payment_records, many=True).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ChannelListView(ListAPIView):
    queryset = Appointment.objects.prefetch_related('payments').select_related('doctor', 'patient', 'branch')
    serializer_class = ChannelListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['doctor', 'date','branch','invoice_number']  # Optional DRF filters
    search_fields = ['id', 'patient__phone_number']
    ordering_fields = ['channel_no']
    pagination_class = PaginationService

    def get_queryset(self):
        queryset = super().get_queryset()

        # ✅ Get branch_id from query params
        branch_id = self.request.query_params.get('branch_id')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        return queryset

    
class AppointmentRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Appointment.objects.select_related('doctor', 'patient', 'schedule').prefetch_related('payments')  # Use the correct related_name
    serializer_class = AppointmentDetailSerializer

    def put(self, request, *args, **kwargs):
        """Handle appointment update"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Update the appointment
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)
    def perform_update(self, serializer):
        """Perform the update and ensure `updated_at` is saved."""
        serializer.save()

    def delete(self, request, *args, **kwargs):
        """Handle appointment delete"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Appointment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class DoctorScheduleTransferView(APIView):
    def post(self, request, *args, **kwargs):
        doctor_id = request.data.get("doctor_id")
        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")
        branch_id = request.data.get("branch_id")

        if not all([doctor_id, from_date, to_date, branch_id]):
            return Response({"error": "doctor_id, from_date, to_date, branch_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_schedules = DoctorScheduleService.transfer_schedules(
                doctor_id=doctor_id,
                from_date=from_date,
                to_date=to_date,
                branch_id=branch_id
            )

            return Response({
                "message": f"{len(new_schedules)} schedules transferred.",
                "new_schedules": ScheduleSerializer(new_schedules, many=True).data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class DoctorAppointmentTransferView(APIView):
    def post(self, request, *args, **kwargs):
        doctor_id = request.data.get("doctor_id")
        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")

        if not all([doctor_id, from_date, to_date]):
            return Response({"error": "doctor_id, from_date, and to_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            updated_appointments = DoctorScheduleService.transfer_appointments_only(
                doctor_id=doctor_id,
                from_date=from_date,
                to_date=to_date
            )

            return Response({
                "message": f"{len(updated_appointments)} appointments were rescheduled.",
                "updated_appointments": AppointmentSerializer(updated_appointments, many=True).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DoctorAppointmentTimeListView(APIView):
    def get(self, request, *args, **kwargs):
        doctor_id = request.query_params.get('doctor_id')
        branch_id = request.query_params.get('branch_id')
        date = request.query_params.get('date')

        # Input validation
        if not all([doctor_id, branch_id, date]):
            return Response(
                {"error": "doctor_id, branch_id, and date are required query parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Try to get the schedule first
            schedule = Schedule.objects.filter(
                doctor_id=doctor_id,
                branch_id=branch_id,
                date=date,
                status__in=[Schedule.StatusChoices.AVAILABLE, Schedule.StatusChoices.BOOKED]
            ).select_related('doctor', 'branch').first()

            if not schedule:
                return Response({
                    "total_appointments": 0,
                    "doctor_arrival": None,  # Format time as 12-hour
                    "appointments": [],
                },
                    status=status.HTTP_200_OK
                )

            # Get appointments for the specified criteria
            appointments = Appointment.objects.filter(
                doctor_id=doctor_id,
                branch_id=branch_id,
                date=date
            ).select_related('patient').order_by('time')

            # Get total count
            total_count = appointments.count()

            # Serialize the appointments
            serializer = AppointmentTimeListSerializer(appointments, many=True)
        
            return Response({
                "total_appointments": total_count,
                "doctor_arrival": schedule.start_time.strftime('%I:%M %p'),  # Format time as 12-hour
                "appointments": serializer.data,
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {"error": "Invalid date format. Please use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class ChannelUpdateView(APIView):
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        appointment_id = kwargs.get('pk')  # Assuming this view is routed as /channels/<pk>/
        data = request.data

        # Step 1: Validate required fields
        required_fields = ['doctor_id', 'name', 'address', 'contact_number', 'channel_date',
                           'time', 'channeling_fee', 'branch_id', 'payments']
        for field in required_fields:
            if field not in data:
                return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Step 2: Fetch & update patient
            appointment = get_object_or_404(Appointment, pk=appointment_id)
            patient = appointment.patient

            patient_payload = {
                "id": patient.id,
                "name": data["name"],
                "phone_number": data["contact_number"],
                "address": data.get("address", "")
            }
            patient = PatientService.create_or_update_patient(patient_payload)

            # Step 3: Handle schedule (create or reassign)
            new_schedule, created = Schedule.objects.get_or_create(
                doctor_id=data['doctor_id'],
                date=data['channel_date'],
                start_time=data['time'],
                branch_id=data['branch_id'],
                defaults={'status': 'Available'}
            )

            if not created and new_schedule.status != 'Available' and appointment.schedule_id != new_schedule.id:
                return Response({"error": "The selected schedule is not available."}, status=status.HTTP_400_BAD_REQUEST)

            # If the schedule changed, release old and book new
            if appointment.schedule_id != new_schedule.id:
                if appointment.schedule:
                    appointment.schedule.status = 'Available'
                    appointment.schedule.save()
                new_schedule.status = 'Booked'
                new_schedule.save()

            # Step 4: Recalculate channel number if branch/date changed
            is_same_date_branch = (
                str(appointment.date) == data['channel_date'] and
                str(appointment.branch_id) == str(data['branch_id'])
            )
            if not is_same_date_branch:
                appointments_today = Appointment.objects.filter(
                    date=data['channel_date'],
                    branch_id=data['branch_id']
                ).count()
                channel_no = appointments_today + 1
            else:
                channel_no = appointment.channel_no  # keep current number

            # Step 5: Update appointment
            appointment_data = {
                "doctor": data['doctor_id'],
                "patient": patient.id,
                "schedule": new_schedule.id,
                "date": data['channel_date'],
                "time": data['time'],
                "status": "Pending",
                "note": data.get('note', ''),
                "amount": data['channeling_fee'],
                "channel_no": channel_no,
                "branch": data['branch_id']
            }
            serializer = AppointmentSerializer(appointment, data=appointment_data)
            serializer.is_valid(raise_exception=True)
            appointment = serializer.save()

            # Step 6: Replace payments
            existing_payments = ChannelPayment.objects.filter(appointment=appointment)
            existing_payments.delete()

            total_paid = 0
            payment_records = []
            for payment in data['payments']:
                payment_data = {
                    "appointment": appointment.id,
                    "amount": payment['amount'],
                    "payment_method": payment['payment_method'],
                    "is_final": False
                }
                total_paid += payment['amount']
                payment_serializer = ChannelPaymentSerializer(data=payment_data)
                payment_serializer.is_valid(raise_exception=True)
                payment_records.append(payment_serializer.save())

            # Step 7: Final payment logic
            if total_paid == data['channeling_fee']:
                payment_records[-1].is_final = True
                payment_records[-1].save()
            elif total_paid > data['channeling_fee']:
                raise ValueError("Total payments exceed the channeling fee.")

            # Step 8: Return updated response
            return Response({
                "patient": PatientSerializer(patient).data,
                "schedule": ScheduleSerializer(new_schedule).data,
                "appointment": AppointmentSerializer(appointment).data,
                "payments": ChannelPaymentSerializer(payment_records, many=True).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class CancelChannelView(APIView):
    def delete(self, request, pk):
        try:
            result = ChannelSoftDeleteService.soft_delete_channel(pk)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
