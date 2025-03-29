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
        sph = request.query_params.get("sph")
        cyl = request.query_params.get("cyl")
        add = request.query_params.get("add")
        side = request.query_params.get("side")
        branch_id = request.query_params.get("branch_id")

        

        # ✅ Validate required fields
        if not (brand_id and type_id and coating_id):
            return Response({"error": "Brand, type, and coating are required."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Convert numeric values (if provided)
        sph = float(sph) if sph else None
        cyl = float(cyl) if cyl else None
        add = float(add) if add else None
        brand_id = int(brand_id) if brand_id else None
        type_id = int(type_id) if type_id else None
        coating_id = int(coating_id) if coating_id else None
   

        # ✅ Call the search service
        lens, stock = LensSearchService.find_matching_lens(
            brand_id, type_id, coating_id, sph, cyl, add, side, branch_id
        )

        if lens and stock:
            return Response({
                "lens": LensSerializer(lens).data,
                "stock": LensStockSerializer(stock).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No matching lens available."}, status=status.HTTP_404_NOT_FOUND)
