from django.db.models import Prefetch
from ..models import Lens, LensPower, LensStock, Power

class LensSearchService:
    """
    Service class to search for lenses with exact specifications and available stock.
    """

    @staticmethod
    def find_matching_lens(brand_id, type_id, coating_id, sph, cyl, add):
        """
        Searches for an exact lens match based on brand, type, coating, and power values.
        Returns the matching lens and available stock if found, otherwise returns None.
        """

        # Step 1: Filter Lenses by Brand, Type, Coating
        lenses = Lens.objects.filter(
            brand_id=brand_id,
            type_id=type_id,
            coating_id=coating_id
        ).prefetch_related(
            Prefetch("lens_powers", queryset=LensPower.objects.select_related("power"))
        )

        # Step 2: Check Power Values (SPH, CYL, ADD)
        for lens in lenses:
            lens_powers = lens.lens_powers.all()  # ✅ Use related_name="lens_powers"

            has_sph = sph is None or lens_powers.filter(power__name="SPH", value=sph).exists()
            has_cyl = cyl is None or lens_powers.filter(power__name="CYL", value=cyl).exists()
            has_add = add is None or lens_powers.filter(power__name="ADD", value=add).exists()

            if has_sph and has_cyl and has_add:
                stock = LensStock.objects.filter(lens=lens, qty__gt=0).first()
                if stock:
                    return lens, stock  # ✅ Exact match found, return immediately

        return None, None  # No matching lens found
