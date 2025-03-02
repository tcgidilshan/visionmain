from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import Frame, Color
from ..serializers import ColorSerializer

class FrameColorListView(APIView):
    """
    API to fetch available colors for a selected frame brand and frame code.
    """
    def get(self, request):
        brand_id = request.query_params.get("brand_id")
        code_id = request.query_params.get("code_id")

        if not brand_id or not code_id:
            return Response({"error": "brand_id and code_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Get all frames that match the given brand and code
        frames = Frame.objects.filter(brand_id=brand_id, code=code_id)

        # ✅ Extract distinct color IDs
        color_ids = frames.values_list("color_id", flat=True).distinct()

        # ✅ Fetch colors from the Color table
        colors = Color.objects.filter(id__in=color_ids)
        serializer = ColorSerializer(colors, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
