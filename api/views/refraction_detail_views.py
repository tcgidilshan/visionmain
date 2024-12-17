from rest_framework import generics, permissions, status
from rest_framework.response import Response
from ..models import RefractionDetails
from ..serializers import RefractionDetailsSerializer


class RefractionDetailCreateAPIView(generics.CreateAPIView):
    """
    API View to create RefractionDetails.
    """
    queryset = RefractionDetails.objects.all()
    serializer_class = RefractionDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Override create to handle any specific logic or responses.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save the validated data
        refraction_details = serializer.save()

        # Return a custom success response
        return Response(
            {
                "message": "Refraction details created successfully.",
                "data": RefractionDetailsSerializer(refraction_details).data
            },
            status=status.HTTP_201_CREATED
        )
