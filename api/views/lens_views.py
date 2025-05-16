from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from ..models import Lens, LensStock, LensPower
from ..serializers import LensSerializer, LensStockSerializer, LensPowerSerializer
from ..services.branch_protection_service import BranchProtectionsService
from rest_framework.exceptions import ValidationError

# List and Create Lenses (with stock and powers)
class LensListCreateView(generics.ListCreateAPIView):
    queryset = Lens.objects.all()
    serializer_class = LensSerializer

    def list(self, request, *args, **kwargs):
        """
        List all ACTIVE lenses with their branch-wise stock and powers.
        If branch_id is passed, only show stock for that branch.
        """
        BranchProtectionsService.validate_branch_id(request)
        branch_id = request.query_params.get('branch_id', None)
        status_filter = request.query_params.get('status', 'active').lower()

        lenses = self.get_queryset()

        # 🔍 Apply is_active filter
        if status_filter == 'active':
            lenses = lenses.filter(is_active=True)
        elif status_filter == 'inactive':
            lenses = lenses.filter(is_active=False)
        elif status_filter == 'all':
            pass  # no filtering
        else:
            return Response(
                {"error": "Invalid status. Allowed values: active, inactive, all."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = []

        for lens in lenses:
            # 🔍 Filter stock by branch if branch_id is provided
            if branch_id:
                stocks = lens.stocks.filter(branch_id=branch_id)
            else:
                stocks = lens.stocks.all()

            powers = lens.lens_powers.all()

            lens_data = LensSerializer(lens).data
            lens_data['stock'] = LensStockSerializer(stocks, many=True).data
            lens_data['powers'] = LensPowerSerializer(powers, many=True).data

            data.append(lens_data)

        return Response(data)

    @transaction.atomic
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create a new lens, its stock, and powers.
        Validates that type + coating + brand + powers (side+value+power_id) combination is unique.
        """

        lens_data = request.data.get('lens')
        stock_data_list = request.data.get('stock', [])
        powers_data = request.data.get('powers', [])

        if not lens_data:
            return Response({"error": "Lens data is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not powers_data:
            return Response({"error": "Powers data are required."}, status=status.HTTP_400_BAD_REQUEST)

        # 🔥 STEP 1: Extract Lens Basic Info
        type_id = lens_data.get('type')
        coating_id = lens_data.get('coating')
        brand_id = lens_data.get('brand')

        # 🔥 STEP 2: Search existing lenses with same type + coating + brand
        existing_lenses = Lens.objects.filter(
            type_id=type_id,
            coating_id=coating_id,
            brand_id=brand_id
        )

        # 🔥 STEP 3: Prepare incoming power set
        incoming_power_set = set(
            (power['side'], str(power['value']), power['power'])  # side, value as string, power_id
            for power in powers_data
        )

        # 🔥 STEP 4: Check against each existing lens
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

        # ✅ STEP 5: Save Lens
        lens_serializer = self.get_serializer(data=lens_data)
        lens_serializer.is_valid(raise_exception=True)
        lens = lens_serializer.save()

        # ✅ STEP 6: Save Stock
        created_stocks = []
        if isinstance(stock_data_list, list):
            for stock_data in stock_data_list:
                if 'initial_count' not in stock_data:
                    return Response(
                        {"error": "initial_count is required for each stock entry."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                stock_data['lens'] = lens.id
                stock_serializer = LensStockSerializer(data=stock_data)
                stock_serializer.is_valid(raise_exception=True)
                created_stocks.append(stock_serializer.save())
        else:
            return Response(
                {"error": "Stock data must be a list."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ STEP 7: Save Powers
        created_powers = []
        for power_data in powers_data:
            power_data['lens'] = lens.id
            power_serializer = LensPowerSerializer(data=power_data)
            power_serializer.is_valid(raise_exception=True)
            created_powers.append(power_serializer.save())

        # ✅ STEP 8: Prepare Response
        response_data = lens_serializer.data
        response_data['stock'] = LensStockSerializer(created_stocks, many=True).data
        response_data['powers'] = powers_data  # or serialize if you want

        return Response(response_data, status=status.HTTP_201_CREATED)


# Retrieve, Update, and Delete Lenses (with stock and powers)
class LensRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lens.objects.all()
    serializer_class = LensSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a lens with optional branch-specific stock and full powers.
        """
        branch = BranchProtectionsService.validate_branch_id(request)
        lens = self.get_object()

        # Full lens info
        lens_data = LensSerializer(lens).data

        stocks = lens.stocks.filter(branch_id=branch.id)

        # Add filtered stocks to response
        lens_data['stock'] = LensStockSerializer(stocks, many=True).data

        # Powers are always complete
        powers = lens.lens_powers.all()
        lens_data['powers'] = LensPowerSerializer(powers, many=True).data

        return Response(lens_data)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Update lens details, along with optional branch-wise stocks and powers.
        """
        lens = self.get_object()
        lens_serializer = self.get_serializer(lens, data=request.data.get("lens", {}), partial=True)
        lens_serializer.is_valid(raise_exception=True)
        lens_serializer.save()

        # Process stock updates
        stock_data_list = request.data.get("stock", [])
        updated_stocks = []

        if isinstance(stock_data_list, list):
            for stock_data in stock_data_list:
                if "initial_count" not in stock_data:
                    return Response(
                        {"error": "initial_count is required for each stock entry."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                branch_id = stock_data.get("branch_id")
                if not branch_id:
                    return Response(
                        {"error": "branch_id is required for stock updates."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # ✅ Check if stock exists for this lens + branch
                stock_instance = lens.stocks.filter(branch_id=branch_id).first()

                stock_data["lens"] = lens.id
                if stock_instance:
                    # Update
                    stock_serializer = LensStockSerializer(stock_instance, data=stock_data, partial=True)
                else:
                    # Create
                    stock_serializer = LensStockSerializer(data=stock_data)

                stock_serializer.is_valid(raise_exception=True)
                updated_stocks.append(stock_serializer.save())

        # Process power updates
        powers_data = request.data.get("powers", [])
        updated_powers = []

        for power_data in powers_data:
            if not power_data.get("power"):
                return Response({"error": "Each power entry must include 'power' field."}, status=400)

            power_data["lens"] = lens.id

            # Update if side + power already exist, else create
            existing_power = lens.lens_powers.filter(
                power_id=power_data["power"],
                side=power_data.get("side")
            ).first()

            if existing_power:
                power_serializer = LensPowerSerializer(existing_power, data=power_data, partial=True)
            else:
                power_serializer = LensPowerSerializer(data=power_data)

            power_serializer.is_valid(raise_exception=True)
            updated_powers.append(power_serializer.save())

        # Final response
        response_data = lens_serializer.data
        response_data["stocks"] = LensStockSerializer(updated_stocks, many=True).data
        response_data["powers"] = LensPowerSerializer(updated_powers, many=True).data

        return Response(response_data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete: Mark the lens as inactive instead of deleting it.
        """
        lens = self.get_object()
        lens.is_active = False
        lens.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


