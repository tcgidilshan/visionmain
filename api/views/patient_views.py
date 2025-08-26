from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from ..models import Patient, PatientAuditLog,CustomUser
from ..serializers import PatientSerializer
from django_filters.rest_framework import DjangoFilterBackend
from ..services.pagination_service import PaginationService
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import serializers

def log_patient_changes(patient, old_data, new_data, user):
    """
    Helper function to log changes to patient fields in PatientAuditLog table
    """
    fields_to_track = ['name', 'phone_number', 'nic', 'date_of_birth', 'address', 'extra_phone_number', 'patient_note']
    
    for field in fields_to_track:
        old_value = old_data.get(field) if old_data else None
        new_value = new_data.get(field)
        
        # Convert values to strings for comparison and storage
        old_str = str(old_value) if old_value is not None else None
        new_str = str(new_value) if new_value is not None else None
        
        # Only log if there's an actual change
        if old_str != new_str:
            PatientAuditLog.objects.create(
                patient=patient,
                field_name=field,
                old_value=old_str,
                new_value=new_str,
                user=user
            )

class PatientListView(ListAPIView):
    """
    API View to List All Patients with Pagination and Search by Name, NIC, or Phone
    Search matches the start of each field (case-insensitive for name)
    """
    queryset = Patient.objects.all().order_by('id')
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationService
    filter_backends = [DjangoFilterBackend]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Get query parameters
        name = self.request.query_params.get('name', None)
        nic = self.request.query_params.get('nic', None)
        phone_number = self.request.query_params.get('phone_number', None)
        
        # Apply filters if parameters exist
        if name:
            queryset = queryset.filter(name__icontains=name)
        if nic:
            queryset = queryset.filter(nic__startswith=nic.upper())
        if phone_number:
            queryset = queryset.filter(phone_number__startswith=phone_number)
            
        return queryset

class PatientUpdateView(RetrieveUpdateAPIView):
    """
    API View to Retrieve and Update a Patient
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_update(self, serializer):
        """
        Check for duplicate phone_number and nic before updating.
        If duplicate NIC is found, raise a validation error with the existing patient's name.
        Also log all changes to the PatientAuditLog table.
        """
        user_id = self.request.data.get("user_id")
        instance = serializer.instance
        old_data = {
            'name': instance.name,
            'phone_number': instance.phone_number,
            'nic': instance.nic,
            'date_of_birth': instance.date_of_birth,
            'address': instance.address,
            'extra_phone_number': instance.extra_phone_number,
            'patient_note': instance.patient_note,
        }
        
        phone_number = self.request.data.get("phone_number", instance.phone_number)
        nic = self.request.data.get("nic", instance.nic)
        
        # Check for duplicate NIC
        if nic and nic != instance.nic:  # Only check if NIC is being changed
            duplicate_patient = Patient.objects.filter(
                nic__iexact=nic
            ).exclude(
                id=instance.id  # Exclude current patient from the check
            ).first()
            
            if duplicate_patient:
                raise serializers.ValidationError({
                    "nic": f"NIC already exists for patient: {duplicate_patient.name}"
                })
        user = None
        if user_id:
            user = CustomUser.objects.get(id=user_id)
        # If no duplicates, proceed with update
        updated_patient = serializer.save(
            name=self.request.data.get("name", instance.name),
            phone_number=phone_number,
            nic=nic,
        )
        
        # Log changes to audit table
        new_data = {
            'name': updated_patient.name,
            'phone_number': updated_patient.phone_number,
            'nic': updated_patient.nic,
            'date_of_birth': updated_patient.date_of_birth,
            'address': updated_patient.address,
            'extra_phone_number': updated_patient.extra_phone_number,
            'patient_note': updated_patient.patient_note,
        }
        
        log_patient_changes(updated_patient, old_data, new_data,user)

class CreatePatientView(APIView):
    """
    API View to create a new patient with NIC validation
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        # Create a mutable copy of the request data
        data = request.data.copy()
        nic = data.get('nic')
        
        # If NIC is provided, check if it already exists
        if nic:
            nic = nic.upper()
            existing_patient = Patient.objects.filter(nic=nic).first()
            if existing_patient:
                return Response(
                    {
                        'error': f'NIC {nic} is already in use by patient: {existing_patient.name}'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update the data with uppercase NIC
            data['nic'] = nic
        
        serializer = PatientSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            patient = serializer.save()
            return Response(
                PatientSerializer(patient).data,
                status=status.HTTP_201_CREATED
            )
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)