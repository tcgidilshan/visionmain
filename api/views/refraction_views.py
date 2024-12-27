from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from ..models import Refraction
from ..serializers import RefractionSerializer
from rest_framework.pagination import PageNumberPagination

class RefractionCreateAPIView(generics.CreateAPIView):
    """
    API View to create a new Refraction record.
    """
    queryset = Refraction.objects.all()
    serializer_class = RefractionSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Override the default create method to handle automatic refraction number generation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save and trigger refraction number generation
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
    API View to List All Refractions with Pagination, Filtering, and Search
    """
    queryset = Refraction.objects.only('id', 'customer_full_name', 'customer_mobile', 'refraction_number')
    serializer_class = RefractionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RefractionPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # Define searchable fields
    search_fields = ['customer_full_name', 'customer_mobile', 'refraction_number']
    ordering_fields = ['refraction_number', 'customer_full_name']
    ordering = ['-refraction_number']  # Default ordering (descending)
    
#update
class RefractionUpdateAPIView(generics.UpdateAPIView):
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