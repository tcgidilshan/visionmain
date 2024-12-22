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
        List all lenses with their stock and powers.
        """
        lenses = self.get_queryset()
        data = []
        for lens in lenses:
            stock = lens.stocks.first()  # Assuming one stock per lens
            powers = lens.lens_powers.all()  # Fetch related lens powers
            stock_data = LensStockSerializer(stock).data if stock else None
            powers_data = LensPowerSerializer(powers, many=True).data
            lens_data = LensSerializer(lens).data
            lens_data['stock'] = stock_data
            lens_data['powers'] = powers_data
            data.append(lens_data)
        return Response(data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create a new lens, its stock (with initial_count), and powers.
        """
        lens_data = request.data.get('lens')
        stock_data = request.data.get('stock')
        powers_data = request.data.get('powers')

        # Validate initial stock data
        if not stock_data or 'initial_count' not in stock_data:
            return Response(
                {"error": "initial_count is required for creating stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create Lens
        lens_serializer = self.get_serializer(data=lens_data)
        lens_serializer.is_valid(raise_exception=True)
        lens = lens_serializer.save()

        # Create Stock
        stock_data['lens'] = lens.id
        stock_serializer = LensStockSerializer(data=stock_data)
        stock_serializer.is_valid(raise_exception=True)
        stock_serializer.save()

        # Create Powers
        for power_data in powers_data:
            power_data['lens'] = lens.id
            power_serializer = LensPowerSerializer(data=power_data)
            power_serializer.is_valid(raise_exception=True)
            power_serializer.save()

        # Prepare Response
        response_data = lens_serializer.data
        response_data['stock'] = stock_serializer.data
        response_data['powers'] = powers_data
        return Response(response_data, status=status.HTTP_201_CREATED)


# Retrieve, Update, and Delete Lenses (with stock and powers)
class LensRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lens.objects.all()
    serializer_class = LensSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a lens with its stock and powers.
        """
        lens = self.get_object()
        stock = lens.stocks.first()  # Assuming one stock per lens
        powers = lens.lens_powers.all()  # Fetch related lens powers
        lens_data = LensSerializer(lens).data
        lens_data['stock'] = LensStockSerializer(stock).data if stock else None
        lens_data['powers'] = LensPowerSerializer(powers, many=True).data
        return Response(lens_data)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Update lens details. Stock and powers updates handled separately.
        """
        lens = self.get_object()
        lens_serializer = self.get_serializer(lens, data=request.data, partial=True)
        lens_serializer.is_valid(raise_exception=True)
        lens_serializer.save()
        return Response(lens_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a lens, its associated stock, and powers.
        """
        lens = self.get_object()
        lens.stocks.all().delete()  # Delete associated stock
        lens.lens_powers.all().delete()  # Delete associated powers
        lens.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
