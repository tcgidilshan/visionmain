from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status,generics
from django.db import transaction
from ..models import Doctor, Patient, Schedule, Appointment, ChannelPayment
from ..serializers import PatientSerializer, ScheduleSerializer, AppointmentSerializer, ChannelPaymentSerializer,ChannelListSerializer,AppointmentDetailSerializer
from rest_framework.generics import ListAPIView
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ..services.doctor_schedule_service import DoctorScheduleService

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
            patient = None
            phone_number = data.get('contact_number')

            if data.get('patient_id'):
                try:
                    patient = Patient.objects.get(id=data['patient_id'])
                    patient.name = data['name']
                    patient.phone_number = phone_number
                    patient.address = data.get('address', patient.address)
                    patient.save()
                except Patient.DoesNotExist:
                    return Response({"error": "Provided patient_id does not exist."}, status=status.HTTP_400_BAD_REQUEST)

            else:
                # Try to get patient by phone number
                patient = Patient.objects.filter(phone_number=phone_number).first()
                if patient:
                    # Update patient info
                    patient.name = data['name']
                    patient.address = data.get('address', patient.address)
                    patient.save()
                else:
                    # Create new patient
                    patient = Patient.objects.create(
                        name=data['name'],
                        phone_number=phone_number,
                        address=data.get('address', '')
                    )

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
    filterset_fields = ['doctor', 'date','branch']  # Optional DRF filters
    search_fields = ['id', 'patient__phone_number']
    ordering_fields = ['channel_no']
    pagination_class = None

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

        # Step 1: Validate the incoming data
        if not all([doctor_id, from_date, to_date, branch_id]):
            return Response({"error": "doctor_id, from_date, to_date, branch_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Step 2: Transfer the schedule using the service method
            transfer_result = DoctorScheduleService.transfer_schedule(
                doctor_id=doctor_id,
                from_date=from_date,
                to_date=to_date,
                branch_id=branch_id
            )

            # Step 3: Return the response with the new schedule details
            return Response({
                "message": f"{len(transfer_result['updated_appointments'])} appointments were rescheduled.",
                "new_schedules": ScheduleSerializer(transfer_result['new_schedules'], many=True).data,
                "updated_appointments": AppointmentSerializer(transfer_result['updated_appointments'], many=True).data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
