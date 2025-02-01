from ..models import RefractionDetails
from ..serializers import RefractionDetailsSerializer

class RefractionDetailsService:
    """
    Service class to handle refraction details creation and updating.
    """

    @staticmethod
    def create_refraction_details(refraction_details_data):
        """
        Creates refraction details and returns the instance.
        """
        serializer = RefractionDetailsSerializer(data=refraction_details_data)
        serializer.is_valid(raise_exception=True)
        refraction_details = serializer.save()
        return refraction_details
