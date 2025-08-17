from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from ..models import Refraction, Patient, Order
from ..serializers import RefractionSerializer, PatientRefractionDetailOrderSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

class RefractionCreateAPIView(generics.CreateAPIView):
    """
    API View to create a new Refraction record.
    """
    queryset = Refraction.objects.all()
    serializer_class = RefractionSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Override the default create method to handle automatic refraction number generation
        and patient association.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get patient_id from request data if it exists
        patient_id = request.data.get('patient_id')
        
        # Save the refraction with the patient if provided
        if patient_id is not None:
            try:
                patient = Patient.objects.get(id=patient_id)
                refraction = serializer.save(patient=patient)
            except Patient.DoesNotExist:
                return Response(
                    {"error": "Patient with the provided ID does not exist"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            refraction = serializer.save()

        return Response(
            {
                "message": "Refraction created successfully",
                "refraction_number": refraction.refraction_number,
                "data": RefractionSerializer(refraction).data,
            },
            status=status.HTTP_201_CREATED,
        )

# Custom Pagination Class
class RefractionPagination(PageNumberPagination):
    page_size = 10  # Customize as needed

class RefractionListAPIView(generics.ListAPIView):
    """
    API View to list all Refractions with pagination, search, ordering,
    and optional filtering by branch_id and patient_id.
    """
    serializer_class = RefractionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RefractionPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # Fields searchable via ?search=
    search_fields = ['customer_full_name', 'customer_mobile', 'refraction_number']

    # Fields orderable via ?ordering=
    ordering_fields = ['refraction_number', 'customer_full_name']
    ordering = ['-refraction_number']  # Default ordering (latest first)

    def get_queryset(self):
        """
        Optionally filter by branch_id using ?branch_id=<id> and patient_id using ?patient_id=<id>
        """
        queryset = Refraction.objects.only(
            'id', 'customer_full_name', 'customer_mobile', 'refraction_number', 'branch_id', 'patient_id'
        )

        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
            
        patient_id = self.request.query_params.get("patient_id")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        return queryset

#update
class RefractionUpdateAPIView(generics.RetrieveUpdateAPIView):
    """
    API View to Update an Existing Refraction Record
    """
    queryset = Refraction.objects.only('id', 'customer_full_name', 'customer_mobile', 'refraction_number')
    serializer_class = RefractionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        """
        Override the default update method for better error handling.
        """
        partial = kwargs.pop('partial', False)  # Enable PATCH if needed
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            updated_instance = serializer.save()
            return Response(
                {
                    "message": "Refraction updated successfully",
                    "data": RefractionSerializer(updated_instance).data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Invalid data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
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
            serializer = PatientRefractionDetailOrderSerializer(orders, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": "An error occurred while processing your request"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )