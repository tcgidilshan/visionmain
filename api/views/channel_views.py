from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status,generics
from django.db import transaction
from ..models import Doctor, Patient, Schedule, Appointment, ChannelPayment
from ..serializers import PatientSerializer, ScheduleSerializer, AppointmentSerializer, ChannelPaymentSerializer,ChannelListSerializer,AppointmentDetailSerializer
from rest_framework.generics import ListAPIView
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

class ChannelAppointmentView(APIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data

        # Step 1: Validate Input
        required_fields = ['doctor_id', 'name', 'address', 'contact_number', 'channel_date', 'time', 'channeling_fee', 'payments']
        for field in required_fields:
            if field not in data:
                return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
           # Step 2: Handle Patient
            if 'patient_id' in data and data['patient_id']:  # If patient_id is provided
                try:
                    # Attempt to retrieve and update the existing patient
                    patient = Patient.objects.get(id=data['patient_id'])
                    patient.name = data['name']
                    patient.phone_number = data['contact_number']
                    patient.address = data.get('address', patient.address)
                    patient.save()
                    created = False  # Indicate that the patient was not newly created
                except Patient.DoesNotExist:
                    # If the provided patient_id does not exist, create a new patient
                    patient = Patient.objects.create(
                        id=data['patient_id'],
                        name=data['name'],
                        phone_number=data['contact_number'],
                        address=data.get('address', '')
                    )
                    created = True
            else:  # If patient_id is not provided, create a new patient
                patient = Patient.objects.create(
                    name=data['name'],
                    phone_number=data['contact_number'],
                    address=data.get('address', '')
                )
                created = True

            # Step 3: Handle Schedule (Create If Not Exists)
            schedule, created = Schedule.objects.get_or_create(
                doctor_id=data['doctor_id'],
                date=data['channel_date'],
                start_time=data['time'],
                defaults={'status': 'Available'}
            )
            if not created and schedule.status != 'Available':
                return Response({"error": "The selected schedule is not available."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Step 4: Calculate `channel_no`
            channel_date = data['channel_date']
            appointments_today = Appointment.objects.filter(date=channel_date).count()
            channel_no = appointments_today + 1  # Increment by 1 for the new appointment

            # Step 5: Create Appointment
            appointment_data = {
                "doctor": data['doctor_id'],
                "patient": patient.id,
                "schedule": schedule.id,
                "date": data['channel_date'],
                "time": data['time'],
                "status": "Pending",
                "amount": data['channeling_fee'],
                "channel_no": channel_no
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
                    "is_final": False  # Default as not final
                }
                total_paid += payment['amount']
                payment_serializer = ChannelPaymentSerializer(data=payment_data)
                payment_serializer.is_valid(raise_exception=True)
                payment_records.append(payment_serializer.save())

            # Step 7: Mark Final Payment
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
            transaction.set_rollback(True)  # Ensure rollback for any exception
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class ChannelListView(ListAPIView):
    queryset = Appointment.objects.prefetch_related('payments').select_related('doctor', 'patient')
    serializer_class = ChannelListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['doctor', 'date']  # Filter by doctor and date
    search_fields = ['id', 'patient__phone_number']  # Search by appointment ID and patient contact number
    ordering_fields = ['channel_no']  # Allow ordering by channel number
    pagination_class = None  # Set your pagination class or leave for default

    def get_queryset(self):
        queryset = super().get_queryset()

        # Add custom filtering logic if necessary
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
