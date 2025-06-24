from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from ..models import Frame, FrameStock, FrameStockHistory, Branch
from ..serializers import FrameStockSerializer

class FrameTransferView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        Transfer frames between branches.
        Expected request data:
        {
            "frame_id": 1,              # ID of the frame to transfer
            "from_branch_id": 1,        # Source branch ID
            "to_branch_id": 2,          # Destination branch ID
            "quantity": 5,              # Quantity to transfer
            "note": "Transfer note"     # Optional note
        }
        """
        frame_id = request.data.get('frame_id')
        from_branch_id = request.data.get('from_branch_id')
        to_branch_id = request.data.get('to_branch_id')
        quantity = request.data.get('quantity')


        # Validate required fields
        if not all([frame_id, from_branch_id, to_branch_id, quantity]):
            return Response(
                {"error": "frame_id, from_branch_id, to_branch_id, and quantity are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if from_branch_id == to_branch_id:
            return Response(
                {"error": "Source and destination branches cannot be the same"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {"error": "Quantity must be greater than 0"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Check if frame exists
            frame = Frame.objects.get(id=frame_id)
            
            # Get or create source stock
            from_branch = Branch.objects.get(id=from_branch_id)
            from_stock, created = FrameStock.objects.get_or_create(
                frame=frame,
                branch=from_branch,
                defaults={
                    'qty': 0,
                    'initial_count': 0
                }
            )

            # Check if source has enough quantity
            if from_stock.qty < quantity:
                return Response(
                    {"error": f"Insufficient stock. Available: {from_stock.qty}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get or create destination stock
            to_branch = Branch.objects.get(id=to_branch_id)
            to_stock, created = FrameStock.objects.get_or_create(
                frame=frame,
                branch=to_branch,
                defaults={
                    'qty': 0,
                    'initial_count': 0
                }
            )

            # Update quantities
            from_stock.qty -= quantity
            to_stock.qty += quantity
            
            # If this is a new stock record or initial_count is None, set it to the transferred quantity
            # Otherwise, increment the existing initial_count
            if created or to_stock.initial_count is None:
                to_stock.initial_count = quantity
            else:
                to_stock.initial_count += quantity

            # Save both stock records
            from_stock.save()
            to_stock.save()


            # Create history records
            FrameStockHistory.objects.create(
                frame=frame,
                branch_id=from_branch_id,
                transfer_to_id=to_branch_id,
                action=FrameStockHistory.TRANSFER,
                quantity_changed=quantity,
              
            )

            # Prepare response
            response_data = {
                "message": "Transfer successful",
                "from_stock": FrameStockSerializer(from_stock).data,
                "to_stock": FrameStockSerializer(to_stock).data
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Frame.DoesNotExist:
            return Response(
                {"error": "Frame not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Branch.DoesNotExist:
            return Response(
                {"error": "One or both branches not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )