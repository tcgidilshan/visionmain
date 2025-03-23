from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from ..models import Lens, LensStock, LensPower
from ..serializers import LensSerializer, LensStockSerializer, LensPowerSerializer

# List and Create Lenses (with stock and powers)
class LensListCreateView(generics.ListCreateAPIView):
    queryset = Lens.objects.all()
    serializer_class = LensSerializer

    def list(self, request, *args, **kwargs):
        """
        List all lenses with their branch-wise stock and powers.
        If branch_id is passed, only show stock for that branch.
        """
        branch_id = request.query_params.get('branch_id', None)
        lenses = self.get_queryset()
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
    def create(self, request, *args, **kwargs):
        """
        Create a new lens, its stock (with initial_count), and powers.
        Supports multiple branch-wise stocks.
        """
        lens_data = request.data.get('lens')
        stock_data_list = request.data.get('stock', [])  # ✅ Accept list of stocks
        powers_data = request.data.get('powers', [])

        # ✅ Create Lens
        lens_serializer = self.get_serializer(data=lens_data)
        lens_serializer.is_valid(raise_exception=True)
        lens = lens_serializer.save()

        # ✅ Process branch-wise stock
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

        # ✅ Process powers
        created_powers = []
        for power_data in powers_data:
            power_data['lens'] = lens.id
            power_serializer = LensPowerSerializer(data=power_data)
            power_serializer.is_valid(raise_exception=True)
            created_powers.append(power_serializer.save())

        # ✅ Prepare response
        response_data = lens_serializer.data
        response_data['stock'] = LensStockSerializer(created_stocks, many=True).data
        response_data['powers'] = powers_data  # original request payload, or serialize if needed

        return Response(response_data, status=status.HTTP_201_CREATED)


# Retrieve, Update, and Delete Lenses (with stock and powers)
class LensRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lens.objects.all()
    serializer_class = LensSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a lens with optional branch-specific stock and full powers.
        """
        branch_id = request.query_params.get('branch_id')
        lens = self.get_object()

        # Full lens info
        lens_data = LensSerializer(lens).data

        # Filter stocks by branch if param is present
        if branch_id:
            stocks = lens.stocks.filter(branch_id=branch_id)
        else:
            stocks = lens.stocks.all()

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
        Delete a lens, its associated stock, and powers.
        """
        lens = self.get_object()
        lens.stocks.all().delete()  # Delete associated stock
        lens.lens_powers.all().delete()  # Delete associated powers
        lens.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

