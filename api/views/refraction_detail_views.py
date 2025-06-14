from rest_framework import generics, permissions, status
from rest_framework.response import Response
from ..models import RefractionDetails
from ..serializers import RefractionDetailsSerializer
from ..services.refraction_details_service import RefractionDetailsService
from ..services.audit_log_service import RefractionDetailsAuditLogService
from django.forms.models import model_to_dict
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
    
class RefractionDetailRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View to Retrieve, Update, and Delete RefractionDetails by refraction ID.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, refraction_id):
        """
        Retrieve RefractionDetails by refraction_id.
        """
        try:
            refraction_details = RefractionDetails.objects.get(refraction_id=refraction_id)
            serializer = RefractionDetailsSerializer(refraction_details)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except RefractionDetails.DoesNotExist:
            return Response({"error": "Refraction details not found."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, refraction_id):
        """
        Update RefractionDetails.
        """
        try:
            refraction_details = RefractionDetails.objects.get(refraction_id=refraction_id)
            # Take a snapshot before update
            original_data = model_to_dict(refraction_details)
            serializer = RefractionDetailsSerializer(
                refraction_details,
                data=request.data,
                partial=False,
                context={"request": request}  # ✅ Required for audit log to have user
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            RefractionDetailsAuditLogService.log_changes(
                instance=refraction_details,
                updated_data=serializer.validated_data,
                original_data=original_data,
                raw_data=request.data  # should contain user_id/admin_id in your frontend
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except RefractionDetails.DoesNotExist:
            return Response({"error": "Refraction details not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, refraction_id):
        """
        Partially update RefractionDetails.
        """
        try:
            refraction_details = RefractionDetails.objects.get(refraction_id=refraction_id)
            serializer = RefractionDetailsSerializer(refraction_details, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except RefractionDetails.DoesNotExist:
            return Response({"error": "Refraction details not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, refraction_id):
        """
        Delete RefractionDetails.
        """
        try:
            refraction_details = RefractionDetails.objects.get(refraction_id=refraction_id)
            refraction_details.delete()
            return Response({"message": "Refraction details deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except RefractionDetails.DoesNotExist:
            return Response({"error": "Refraction details not found."}, status=status.HTTP_404_NOT_FOUND)
