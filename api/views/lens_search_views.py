from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.lens_search_service import LensSearchService
from ..serializers import LensSerializer, LensStockSerializer

class LensSearchView(APIView):
    """
    API View to search for lenses based on brand, type, coating, and power values.
    """

    def get(self, request):
        """
        Search for a lens with exact specifications.
        """
        # ✅ Get query parameters
        brand_id = request.query_params.get("brand_id")
        type_id = request.query_params.get("type_id")
        coating_id = request.query_params.get("coating_id")
        sph_left = request.query_params.get("sph_left")
        sph_right = request.query_params.get("sph_right")
        cyl_left = request.query_params.get("cyl_left")
        cyl_right = request.query_params.get("cyl_right")
        add_left = request.query_params.get("add_left")
        add_right = request.query_params.get("add_right")

        # ✅ Validate required fields
        if not (brand_id and type_id and coating_id):
            return Response({"error": "Brand, type, and coating are required."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Convert numeric values (if provided)
        sph_left = float(sph_left) if sph_left else None
        sph_right = float(sph_right) if sph_right else None
        cyl_left = float(cyl_left) if cyl_left else None
        cyl_right = float(cyl_right) if cyl_right else None
        add_left = float(add_left) if add_left else None
        add_right = float(add_right) if add_right else None

        # ✅ Call the search service
        lens, stock = LensSearchService.find_matching_lens(
            brand_id, type_id, coating_id, sph_left, sph_right, cyl_left, cyl_right, add_left, add_right
        )

        if lens and stock:
            return Response({
                "lens": LensSerializer(lens).data,
                "stock": LensStockSerializer(stock).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No matching lens available."}, status=status.HTTP_404_NOT_FOUND)
