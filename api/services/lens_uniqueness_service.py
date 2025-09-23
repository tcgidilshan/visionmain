from rest_framework.exceptions import ValidationError
from decimal import Decimal
from ..models import Lens, LensPower


class LensUniquenessService:
    @staticmethod
    def check_lens_uniqueness(type_id, coating_id, brand_id, powers_data, exclude_lens_id=None):
        """
        Checks if a lens with the same type, coating, brand, and powers already exists.
        
        Args:
            type_id: ID of the lens type
            coating_id: ID of the coating
            brand_id: ID of the brand
            powers_data: List of power dictionaries with 'side', 'value', 'power' keys
            exclude_lens_id: ID of the lens to exclude (for updates)
        
        Raises:
            ValidationError: If a duplicate lens is found
        """
        # Find existing lenses with same type, coating, brand
        existing_lenses = Lens.objects.filter(
            type_id=type_id,
            coating_id=coating_id,
            brand_id=brand_id
        )
        
        if exclude_lens_id:
            existing_lenses = existing_lenses.exclude(id=exclude_lens_id)
        
        if not existing_lenses.exists():
            return  # No existing lenses with same basic attributes, so unique
        
        # Prepare incoming power set
        incoming_power_set = set(
            (power['side'], str(Decimal(str(power['value'])).quantize(Decimal('0.01'))), power['power'])
            for power in powers_data
        )
        
        # Check against each existing lens
        for existing_lens in existing_lenses:
            existing_powers = existing_lens.lens_powers.all()
            existing_power_set = set(
                (p.side, str(p.value), p.power_id)  # side, value as string, power_id
                for p in existing_powers
            )
            
            if incoming_power_set == existing_power_set:
                raise ValidationError(
                    "A lens with the same type, coating, brand, and powers already exists."
                )