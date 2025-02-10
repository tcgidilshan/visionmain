from rest_framework import generics, status, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import Brand
from ..serializers import BrandSerializer

# ✅ List and Create Brands with Filtering
class BrandListCreateView(generics.ListCreateAPIView):
    """
    API to list and create brands.
    Supports filtering by brand_type (?brand_type=frame/lens/both).
    """
    serializer_class = BrandSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter brands by type if provided in query parameters.
        """
        queryset = Brand.objects.all()
        brand_type = self.request.query_params.get("brand_type", None)

        if brand_type in ["frame", "lens", "both"]:  # ✅ Apply filtering
            queryset = queryset.filter(brand_type=brand_type)

        return queryset


# ✅ Retrieve, Update, and Delete a Brand
class BrandRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    API to retrieve, update, or delete a brand.
    """
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        """
        Update an existing brand (supports partial updates).
        """
        partial = kwargs.pop('partial', False)  # ✅ Allows PATCH requests
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)