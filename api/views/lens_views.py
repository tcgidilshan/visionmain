from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from ..models import Lens, LensStock, LensPower,LensStockHistory
from ..serializers import LensSerializer, LensStockSerializer, LensPowerSerializer
from ..services.branch_protection_service import BranchProtectionsService
from ..services.lens_uniqueness_service import LensUniquenessService
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

# List and Create Lenses (with stock and powers)
class LensListCreateView(generics.ListCreateAPIView):
    queryset = Lens.objects.all()
    serializer_class = LensSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        queryset = super().get_queryset()
        init_branch_id = self.request.query_params.get('init_branch_id')
        if init_branch_id:
            queryset = queryset.filter(branch_id=init_branch_id)
        return queryset

    def list(self, request, *args, **kwargs):
        """
        List lenses with optional filters:
        - status: active|inactive|all - Filter lenses by active status
        - init_branch_id - Filter by initial branch
        
        Required parameters (one of):
        - branch_id - Return ALL lenses, but only include stock data for this branch
        - store_id - Return ONLY lenses that have stock in this branch, with their stock data
        """
        status_filter = request.query_params.get("status", "active").lower()
        branch_id = request.query_params.get("branch_id")
        store_id = request.query_params.get("store_id")
        
        if not (branch_id or store_id):
            return Response(
                {"error": "Either branch_id or store_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        lenses = self.get_queryset()
        
        # Apply status filter if provided
        if status_filter == "active":
            lenses = lenses.filter(is_active=True)
        elif status_filter == "inactive":
            lenses = lenses.filter(is_active=False)
        elif status_filter != "all":
            return Response(
                {"error": "Invalid status filter. Use 'active', 'inactive', or 'all'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Order by creation date descending (latest first)
        lenses = lenses.order_by('-id')

        data = []
        
        if store_id:
            # STORE_ID MODE: Only return lenses that have stock in the specified branch
            # and only include stock data for that branch
            lens_ids_with_stock = LensStock.objects.filter(
                branch_id=store_id,
            ).values_list('lens_id', flat=True).distinct()
            
            lenses = lenses.filter(id__in=lens_ids_with_stock)
            
            for lens in lenses:
                stocks = lens.stocks.filter(branch_id=store_id, qty__gt=0)
                powers = lens.lens_powers.all()
                
                lens_data = LensSerializer(lens).data
                lens_data['stock'] = LensStockSerializer(stocks, many=True).data
                lens_data['powers'] = LensPowerSerializer(powers, many=True).data
                data.append(lens_data)
                
        elif branch_id:
            # BRANCH_ID MODE: Return ALL lenses, but only include stock data for the specified branch
            for lens in lenses:
                stocks = lens.stocks.filter(branch_id=branch_id)
                powers = lens.lens_powers.all()
                
                lens_data = LensSerializer(lens).data
                lens_data['stock'] = LensStockSerializer(stocks, many=True).data
                lens_data['powers'] = LensPowerSerializer(powers, many=True).data
                data.append(lens_data)

        return Response(data, status=status.HTTP_200_OK)

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

        # 🔥 STEP 2: Check uniqueness
        LensUniquenessService.check_lens_uniqueness(type_id, coating_id, brand_id, powers_data)

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
                LensStockHistory.objects.create(
                    lens=lens,
                    branch_id=stock_data['branch_id'],
                    action=LensStockHistory.ADD,
                    quantity_changed=stock_data['qty']
                )
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
        Update an existing lens, its stock, and powers.
        Ensures the (type + coating + brand + powers) combination remains unique.
        """
        lens_id = kwargs.get('pk')
        lens_instance = get_object_or_404(Lens, pk=lens_id)

        lens_data = request.data.get('lens')
        stock_data_list = request.data.get('stock', [])
        powers_data = request.data.get('powers', [])

        if not lens_data and not stock_data_list and not powers_data:
            return Response({"error": "No data provided for update."}, status=status.HTTP_400_BAD_REQUEST)
            
        # If lens data is provided, validate it
        if lens_data:
            # Check for duplicate lens only if type, coating, or brand are being updated
            type_id = lens_data.get('type', lens_instance.type_id)
            coating_id = lens_data.get('coating', lens_instance.coating_id)
            brand_id = lens_data.get('brand', lens_instance.brand_id)

            # Check for duplicate lens (excluding current one) only if we have powers data
            if powers_data:
                LensUniquenessService.check_lens_uniqueness(type_id, coating_id, brand_id, powers_data, exclude_lens_id=lens_id)

        # If lens data is being updated, validate and save it
        if lens_data:
            lens_serializer = self.get_serializer(lens_instance, data=lens_data, partial=True)
            lens_serializer.is_valid(raise_exception=True)
            lens = lens_serializer.save()
        else:
            lens = lens_instance

        # ✅ Update/Create Stock if stock data is provided
        if not isinstance(stock_data_list, list):
            return Response({"error": "Stock data must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        updated_stocks = []
        for stock_data in stock_data_list:
            if 'initial_count' not in stock_data:
                return Response({"error": "initial_count is required."}, status=status.HTTP_400_BAD_REQUEST)

            branch_id = stock_data.get('branch_id')
            stock_data['lens'] = lens.id

            stock_instance = LensStock.objects.filter(lens=lens, branch_id=branch_id).first()
            old_qty = stock_instance.qty if stock_instance else 0
            
            if stock_instance:
                stock_serializer = LensStockSerializer(stock_instance, data=stock_data, partial=True)
            else:
                stock_serializer = LensStockSerializer(data=stock_data)

            stock_serializer.is_valid(raise_exception=True)
            updated_stock = stock_serializer.save()
            updated_stocks.append(updated_stock)
            
            # Create stock history record if quantity changed or it's a new stock
            if 'qty' in stock_data:
                if not stock_instance:  # New stock record
                    if int(stock_data['qty']) > 0:  # Only create history if initial qty > 0
                        LensStockHistory.objects.create(
                            lens=lens,
                            branch_id=branch_id,
                            action=LensStockHistory.ADD,
                            quantity_changed=int(stock_data['qty'])
                        )
                elif stock_instance:  # Existing stock record
                    qty_difference = int(stock_data['qty']) - old_qty
                    if qty_difference != 0:
                        action = LensStockHistory.ADD if qty_difference > 0 else LensStockHistory.REMOVE
                        LensStockHistory.objects.create(
                            lens=lens,
                            branch_id=branch_id,
                            action=action,
                            quantity_changed=abs(qty_difference)
                        )

        # ✅ Update Powers if powers data is provided
        if powers_data:
            lens.lens_powers.all().delete()
            updated_powers = []
            for power_data in powers_data:
                power_data['lens'] = lens.id
                power_serializer = LensPowerSerializer(data=power_data)
                power_serializer.is_valid(raise_exception=True)
                updated_powers.append(power_serializer.save())

        # ✅ Prepare Response
        response_data = self.get_serializer(lens).data
        response_data['stock'] = LensStockSerializer(
            lens.stocks.all(), 
            many=True
        ).data if not stock_data_list else LensStockSerializer(updated_stocks, many=True).data
        response_data['powers'] = LensPowerSerializer(
            lens.lens_powers.all(), 
            many=True
        ).data if not powers_data else powers_data

        return Response(response_data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete: Mark the lens as inactive instead of deleting it.
        """
        lens = self.get_object()
        lens.is_active = False
        lens.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
 