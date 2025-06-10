from rest_framework import generics, status
from rest_framework.response import Response
from ..models import FrameStock
from ..serializers import FrameStockSerializer
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from ..models import Branch
from ..services.stock_adjustment import adjust_stock_bulk

# List and Create FrameStock Records
class FrameStockListCreateView(generics.ListCreateAPIView):
    queryset = FrameStock.objects.all()
    serializer_class = FrameStockSerializer

    def list(self, request, *args, **kwargs):
        """
        List all FrameStock records.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new FrameStock record.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# Retrieve, Update, and Delete FrameStock Records
class FrameStockRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FrameStock.objects.all()
    serializer_class = FrameStockSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single FrameStock record.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update an existing FrameStock record.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a FrameStock record.
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class StockAdjustmentView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def adjust(self, request):
        """
        POST /api/frames/stocks/adjust
        Payload:
        {
            "branch_id": 1,
            "action": "add",
            "items": [
                {"frame_id": 101, "quantity": 5},
                {"frame_id": 202, "quantity": 3}
            ]
        }
        """
        branch_id = request.data.get("branch_id")
        action = request.data.get("action")
        items = request.data.get("items")

        if not branch_id or not action or not items:
            return Response({"error": "branch_id, action, and items are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            branch = Branch.objects.get(id=branch_id)
        except Branch.DoesNotExist:
            return Response({"error": "Invalid branch_id."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            updated_stocks = adjust_stock_bulk(
                action=action,
                items=items,
                branch=branch,
                performed_by=request.user
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Serialize inline to avoid serializer boilerplate (can optimize later)
        response_data = [
            {
                "frame_id": stock.frame.id,
                "branch_id": stock.branch.id,
                "updated_qty": stock.qty
            } for stock in updated_stocks
        ]

        return Response({"success": True, "updated": response_data}, status=status.HTTP_200_OK)
