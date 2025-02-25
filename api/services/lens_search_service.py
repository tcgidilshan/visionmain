from django.db.models import Prefetch
from ..models import Lens, LensPower, LensStock

class LensSearchService:
    """
    Service class to search for lenses with exact specifications and available stock.
    """

    @staticmethod
    def find_matching_lens(brand_id, type_id, coating_id, sph_left, sph_right, cyl_left, cyl_right, add_left, add_right):
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
            lens_powers = lens.lens_powers.all()  # ✅ Use related_name="lens_powers"

            # ✅ Validate LEFT Eye Powers
            has_sph_left = sph_left is None or lens_powers.filter(power__name="SPH", value=sph_left, side="left").exists()
            has_cyl_left = cyl_left is None or lens_powers.filter(power__name="CYL", value=cyl_left, side="left").exists()
            has_add_left = add_left is None or lens_powers.filter(power__name="ADD", value=add_left, side="left").exists()

            # ✅ Validate RIGHT Eye Powers
            has_sph_right = sph_right is None or lens_powers.filter(power__name="SPH", value=sph_right, side="right").exists()
            has_cyl_right = cyl_right is None or lens_powers.filter(power__name="CYL", value=cyl_right, side="right").exists()
            has_add_right = add_right is None or lens_powers.filter(power__name="ADD", value=add_right, side="right").exists()

            # ✅ If all power values match for both sides, check stock
            if has_sph_left and has_cyl_left and has_add_left and has_sph_right and has_cyl_right and has_add_right:
                stock = LensStock.objects.filter(lens=lens, qty__gt=0).first()
                if stock:
                    return lens, stock  # ✅ Exact match found, return immediately

        return None, None  # ❌ No matching lens found
