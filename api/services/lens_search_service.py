from django.db.models import Prefetch
from ..models import Lens, LensPower, LensStock

class LensSearchService:
    """
    Service class to search for lenses with exact specifications and available stock.
    """

    @staticmethod
    def find_matching_lens( brand_id, type_id, coating_id, sph, cyl, add, side, branch_id):
        """
        Searches for an exact lens match based on brand, type, coating, and power values.
        Supports left/right separation.
        """

        # ✅ Step 1: Filter Lenses by Brand, Type, Coating
        lenses = Lens.objects.filter(
            brand_id=brand_id,
            type_id=type_id,
            coating_id=coating_id
        ).prefetch_related(
            Prefetch("lens_powers", queryset=LensPower.objects.select_related("power"))
        )

        # ✅ Step 2: Check Power Values for Each Side (SPH, CYL, ADD)
        
        for lens in lenses:
            lens_powers = lens.lens_powers.all()

            # Determine if the lens has the required SPH
            if sph is not None:
                has_sph = lens_powers.filter(power__name="SPH", value=sph).exists()
            else:
                # Lens should not have any SPH power
                has_sph = not lens_powers.filter(power__name="SPH").exists()

            # Determine if the lens has the required CYL
            if cyl is not None:
                has_cyl = lens_powers.filter(power__name="CYL", value=cyl).exists()
            else:
                # Lens should not have any CYL power
                has_cyl = not lens_powers.filter(power__name="CYL").exists()

            # Determine if the lens has the required ADD
            if add is not None:
                has_add = lens_powers.filter(power__name="ADD", value=add).exists()
            else:
                # Lens should not have any ADD power
                has_add = not lens_powers.filter(power__name="ADD").exists()

            # Check if all specifications are met
            if has_sph and has_cyl and has_add:
                stock = LensStock.objects.filter(
                    lens=lens,
                    branch_id=branch_id,
                    qty__gt=0
                ).first()
                if stock:
                    return lens, stock

        return None, None  # ❌ No matching lens found
