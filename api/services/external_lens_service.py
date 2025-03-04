from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from ..models import ExternalLens
from ..serializers import ExternalLensSerializer,ExternalLensPowerSerializer


class ExternalLensService:
    @staticmethod
    @transaction.atomic
    def create_external_lens(lens_data, powers_data):
        """
        Handles the creation of an ExternalLens and its associated powers, including the price.
        """
        # Extract price from request data
        price = lens_data.get('price')
        if price is None:
            raise ValidationError({'price': 'Price is required for external lenses.'})

         # ✅ Pass validated data instead of trying to pass `price` separately
        external_lens_serializer = ExternalLensSerializer(data=lens_data)
        external_lens_serializer.is_valid(raise_exception=True)

        # ✅ Explicitly assign the price before saving
        external_lens = external_lens_serializer.save()
        external_lens.price = price
        external_lens.save()

        # Create Powers
        power_instances = []
        for power_data in powers_data:
            power_data['external_lens'] = external_lens.id  # Associate power with the lens
            power_serializer = ExternalLensPowerSerializer(data=power_data)
            if not power_serializer.is_valid():
                raise ValidationError(power_serializer.errors)
            
            power_instances.append(power_serializer.save())  # Save and collect instances

        return {
            'external_lens': external_lens_serializer.data,
            'powers': [ExternalLensPowerSerializer(power).data for power in power_instances]
        }
