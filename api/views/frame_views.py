from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import Frame, FrameStock
from ..serializers import FrameSerializer, FrameStockSerializer
from django.db import transaction

# List and Create Frames (with stock)
class FrameListCreateView(generics.ListCreateAPIView):
    queryset = Frame.objects.all()
    serializer_class = FrameSerializer

    def list(self, request, *args, **kwargs):
        """
        List all frames along with their stock details.
        """
        frames = self.get_queryset()
        data = []
        for frame in frames:
            stock = frame.stocks.first()  # Assuming one stock per frame
            stock_data = FrameStockSerializer(stock).data if stock else None
            frame_data = FrameSerializer(frame).data
            frame_data['stock'] = stock_data
            data.append(frame_data)
        return Response(data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create a frame and its initial stock (initial_count is required).
        """
        frame_data = request.data.get('frame')
        stock_data = request.data.get('stock')

        if not stock_data or 'initial_count' not in stock_data:
            return Response(
                {"error": "initial_count is required for creating stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        frame_serializer = self.get_serializer(data=frame_data)
        frame_serializer.is_valid(raise_exception=True)
        frame = frame_serializer.save()

        stock_data['frame'] = frame.id
        stock_serializer = FrameStockSerializer(data=stock_data)
        stock_serializer.is_valid(raise_exception=True)
        stock_serializer.save()

        response_data = frame_serializer.data
        response_data['stock'] = stock_serializer.data
        return Response(response_data, status=status.HTTP_201_CREATED)


# Retrieve, Update, and Delete Frames (with stock details)
class FrameRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Frame.objects.all()
    serializer_class = FrameSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a frame along with its stock details.
        """
        frame = self.get_object()
        stock = frame.stocks.first()  # Assuming one stock per frame
        frame_data = FrameSerializer(frame).data
        frame_data['stock'] = FrameStockSerializer(stock).data if stock else None
        return Response(frame_data)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Update frame details. Stock updates are handled separately.
        """
        frame = self.get_object()
        frame_serializer = self.get_serializer(frame, data=request.data, partial=True)
        frame_serializer.is_valid(raise_exception=True)
        frame_serializer.save()
        return Response(frame_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a frame and its associated stock.
        """
        frame = self.get_object()
        frame.stocks.all().delete()  # Delete associated stock
        frame.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
