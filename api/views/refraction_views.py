from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from ..models import Refraction, Patient, Order
from ..serializers import RefractionSerializer, PatientRefractionDetailOrderSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django.db.models import Q
from ..services.pagination_service import PaginationService

class RefractionCreateAPIView(generics.CreateAPIView):
    """
    API View to create a new Refraction record.
    """
    queryset = Refraction.objects.all()
    serializer_class = RefractionSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Handle creation of refraction with optional patient creation.
        If patient_id is not provided, creates a new patient with the given details.
        """
        data = request.data.copy()
        patient_id = data.get('patient_id')
        
        # If no patient_id is provided, create a new patient
        if not patient_id:
            name = data.get('customer_full_name')
            phone_number = data.get('customer_mobile')
            nic = data.get('nic')
            
            if not name:
                return Response(
                    {"error": "Customer name is required when creating a new patient"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Create new patient
            try:
                patient = Patient.objects.create(
                    name=name,
                    phone_number=phone_number if phone_number else None,
                    nic=nic if nic else None
                )
                data['patient_id'] = patient.id
            except Exception as e:
                return Response(
                    {"error": f"Failed to create patient: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Now handle the refraction creation
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get the patient instance if it exists
            patient = None
            if 'patient_id' in data:
                try:
                    patient = Patient.objects.get(id=data['patient_id'])
                except Patient.DoesNotExist:
                    return Response(
                        {"error": f"Patient with ID {data['patient_id']} does not exist"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Save the refraction with the patient if provided
            refraction = serializer.save(patient=patient)
            
            return Response(
                {
                    "message": "Refraction created successfully",
                    "refraction_number": refraction.refraction_number,
                    "data": RefractionSerializer(refraction).data,
                },
                status=status.HTTP_201_CREATED,
            )
            
        except Exception as e:
            return Response(
                {"error": f"Failed to create refraction: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class RefractionListAPIView(generics.ListAPIView):
    """
    API View to list all Refractions with pagination, search, ordering,
    and optional filtering by branch_id and patient_id.
    """
    serializer_class = RefractionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PaginationService
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # Fields searchable via ?search=
    search_fields = [
        'refraction_number',
        'patient__name',  # Search by patient name
        'patient__phone_number',  # Search by patient phone number
        'patient__nic',  # Search by patient NIC
    ]

    # Fields orderable via ?ordering=
    ordering_fields = ['refraction_number', 'created_at']
    ordering = ['-refraction_number']  # Default ordering (latest first)

    def get_queryset(self):
        """
        Optionally filter by branch_id using ?branch_id=<id> and patient_id using ?patient_id=<id>
        Also supports search by patient name, phone number, and NIC
        """
        queryset = Refraction.objects.select_related('branch', 'patient').all()

        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
            
        patient_id = self.request.query_params.get("patient_id")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
            
        search_term = self.request.query_params.get("search")
        if search_term:
            queryset = queryset.filter(
                Q(patient__name__icontains=search_term) |
                Q(patient__phone_number__icontains=search_term) |
                Q(patient__nic__icontains=search_term) |
                Q(refraction_number__icontains=search_term)
            )

        return queryset

#update
class RefractionUpdateAPIView(generics.RetrieveUpdateAPIView):
    """
    API View to Update an Existing Refraction Record
    """
    queryset = Refraction.objects.all()
    serializer_class = RefractionSerializer
    permission_classes = [permissions.IsAuthenticated]
#//TODO  TEST PATINT UPDATE ?? Debug all patient relations
    def update(self, request, *args, **kwargs):
        """
        Override the default update method to handle patient updates and better error handling.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()
        
        # Handle patient data if provided
        if 'customer_full_name' in data or 'customer_mobile' in data or 'nic' in data:
            if not instance.patient:
                # Create new patient if none exists
                name = data.pop('customer_full_name', '')
                if not name:
                    return Response(
                        {"error": "Customer name is required when creating a new patient"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                patient = Patient.objects.create(
                    name=name,
                    phone_number=data.pop('customer_mobile', None),
                    nic=data.pop('nic', None)
                )
                data['patient_id'] = patient.id
            else:
                # Update existing patient
                patient = instance.patient
                if 'customer_full_name' in data:
                    patient.name = data.pop('customer_full_name')
                if 'customer_mobile' in data:
                    patient.phone_number = data.pop('customer_mobile')
                if 'nic' in data:
                    patient.nic = data.pop('nic')
                patient.save()
        
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            updated_instance = serializer.save()
            return Response(
                {
                    "message": "Refraction updated successfully",
                    "data": RefractionSerializer(updated_instance).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to update refraction: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

#delete
class RefractionDeleteAPIView(generics.DestroyAPIView):
    """
    API View to Delete a Refraction Record
    """
    queryset = Refraction.objects.only('id')
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Refraction deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

class RefractionOrderView(APIView):
    """
    API endpoint that returns all orders with refraction details for a specific patient.
    Requires patient_id as a query parameter.
    """
    
    def get(self, request):
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {"error": "patient_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Get orders with refraction for the specified patient
            orders = Order.objects.filter(
                refraction__isnull=False,
                customer_id=patient_id
            ).select_related(
                'refraction', 
                'customer', 
                'invoice',
                'refraction__refraction_details',
                'refraction__refraction_details__user'
            ).order_by('-order_date')  # Order by most recent first
            
            # Use the new serializer
            paginator=PaginationService()
            page = paginator.paginate_queryset(orders, request, view=self)
            serializer = PatientRefractionDetailOrderSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": "An error occurred while processing your request"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )