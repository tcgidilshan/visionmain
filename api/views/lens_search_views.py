from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from ..services.lens_search_service import LensSearchService
from ..serializers import LensSerializer, LensStockSerializer
from ..models import Lens

class LensSearchAPIView(APIView):
    """
    API View to search for an exact lens match in stock.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Search for an exact lens match based on brand, type, coating, and power values.
        Returns lens details and available stock if found.
        """

       # Extract query parameters
        brand_id = request.query_params.get("brand_id")
        type_id = request.query_params.get("type_id")
        coating_id = request.query_params.get("coating_id")
        sph = request.query_params.get("sph")  # Optional
        cyl = request.query_params.get("cyl")  # Optional
        add = request.query_params.get("add")  # Optional

        # Validate required parameters (Brand, Type, Coating are mandatory)
        if not all([brand_id, type_id, coating_id]):
            return Response({"error": "Missing required parameters: brand_id, type_id, coating_id are required."},
                            status=status.HTTP_400_BAD_REQUEST)


        # Call the LensSearchService
        matching_lens, stock = LensSearchService.find_matching_lens(brand_id, type_id, coating_id, sph, cyl, add)

        if matching_lens:
            return Response({
                "lens": LensSerializer(matching_lens).data,
                "stock": LensStockSerializer(stock).data
            }, status=status.HTTP_200_OK)
        
        return Response({"message": "No matching lens available."}, status=status.HTTP_404_NOT_FOUND)
