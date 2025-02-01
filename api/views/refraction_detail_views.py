from rest_framework import generics, permissions, status
from rest_framework.response import Response
from ..models import RefractionDetails
from ..serializers import RefractionDetailsSerializer
from ..services.refraction_details_service import RefractionDetailsService


class RefractionDetailCreateAPIView(generics.CreateAPIView):
    """
    API View to create RefractionDetails.
    """
    queryset = RefractionDetails.objects.all()
    serializer_class = RefractionDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Override create to use the service for creating refraction details.
        """
        refraction_details = RefractionDetailsService.create_refraction_details(request.data)

        return Response(
            {
                "message": "Refraction details created successfully.",
                "data": RefractionDetailsSerializer(refraction_details).data
            },
            status=status.HTTP_201_CREATED
        )
