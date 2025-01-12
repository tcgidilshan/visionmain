from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from ..models import LensStock
from ..serializers import LensStockSerializer

class LensStockListCreateView(APIView):
    """Handles listing and creating LensStock"""

    def get(self, request):
        """
        Get a list of all LensStock with related details.
        """
        lens_stocks = LensStock.objects.select_related('lens__type', 'lens__coating').all()  # Optimize related queries
        serializer = LensStockSerializer(lens_stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        """
        Create a new LensStock record.
        """
        serializer = LensStockSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LensStockRetrieveUpdateDeleteView(APIView):
    """Handles retrieving, updating, and deleting a specific LensStock"""

    def get(self, request, pk):
        """
        Retrieve a specific LensStock by ID.
        """
        lens_stock = get_object_or_404(LensStock, pk=pk)
        serializer = LensStockSerializer(lens_stock)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def put(self, request, pk):
        """
        Update a specific LensStock by ID.
        """
        lens_stock = get_object_or_404(LensStock, pk=pk)
        serializer = LensStockSerializer(lens_stock, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def patch(self, request, pk):
        """
        Partially update a specific LensStock by ID.
        """
        lens_stock = get_object_or_404(LensStock, pk=pk)
        serializer = LensStockSerializer(lens_stock, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def delete(self, request, pk):
        """
        Delete a specific LensStock by ID.
        """
        lens_stock = get_object_or_404(LensStock, pk=pk)
        lens_stock.delete()
        return Response({"message": "LensStock deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
