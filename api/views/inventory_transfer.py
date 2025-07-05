from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from ..models import Frame, FrameStock, FrameStockHistory, Branch, Lens, LensStock, LensStockHistory
from ..serializers import FrameStockSerializer, LensStockSerializer

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


class LensTransferView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        Manage lens stock with different actions: ADD, TRANSFER, REMOVE
        
        For ADD action (add stock to a branch):
        {
            "action": "add",
            "lens_id": 1,              # ID of the lens
            "to_branch_id": 2,          # Destination branch ID
            "quantity": 5,              # Quantity to add
            "note": "Adding new stock"  # Optional note
        }
        
        For TRANSFER action (transfer between branches):
        {
            "action": "transfer",
            "lens_id": 1,              # ID of the lens
            "from_branch_id": 1,        # Source branch ID
            "to_branch_id": 2,          # Destination branch ID
            "quantity": 5,              # Quantity to transfer
            "note": "Transfer note"     # Optional note
        }
        
        For REMOVE action (remove stock from a branch):
        {
            "action": "remove",
            "lens_id": 1,              # ID of the lens
            "from_branch_id": 1,        # Branch ID to remove from
            "quantity": 2,              # Quantity to remove
            "reason": "Damaged",        # Reason for removal
            "note": "Damaged stock"     # Optional note
        }
        """
        action = request.data.get('action', '').lower()
        lens_id = request.data.get('lens_id')
        quantity = request.data.get('quantity')
        
        # Validate common required fields
        if not all([action, lens_id, quantity is not None]):
            return Response(
                {"error": "action, lens_id, and quantity are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if quantity <= 0:
            return Response(
                {"error": "Quantity must be greater than 0"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Check if lens exists and is active
            lens = Lens.objects.get(id=lens_id, is_active=True)
            
            if action == 'add':
                return self._handle_add_action(request, lens)
            elif action == 'transfer':
                return self._handle_transfer_action(request, lens)
            elif action == 'remove':
                return self._handle_remove_action(request, lens)
            else:
                return Response(
                    {"error": "Invalid action. Must be one of: add, transfer, remove"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Lens.DoesNotExist:
            return Response(
                {"error": "Lens not found or is inactive"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Branch.DoesNotExist:
            return Response(
                {"error": "Branch not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_add_action(self, request, lens):
        """Handle adding stock to a branch"""
        to_branch_id = request.data.get('to_branch_id')
        quantity = int(request.data.get('quantity'))
        
        if not to_branch_id:
            raise ValueError("to_branch_id is required for add action")
            
        # Get or create destination stock
        to_branch = Branch.objects.get(id=to_branch_id)
        to_stock, created = LensStock.objects.get_or_create(
            lens=lens,
            branch=to_branch,
            defaults={'qty': 0, 'initial_count': 0}
        )
        
        # Update quantities
        to_stock.qty += quantity
        if created or to_stock.initial_count is None:
            to_stock.initial_count = quantity
        else:
            to_stock.initial_count += quantity
        to_stock.save()
        
        # Create history record
        LensStockHistory.objects.create(
            lens=lens,
            branch=to_branch,
            action=LensStockHistory.ADD,
            quantity_changed=quantity
        )
        
        return Response({
            "message": "Stock added successfully",
            "stock": LensStockSerializer(to_stock).data
        }, status=status.HTTP_200_OK)
    
    def _handle_transfer_action(self, request, lens):
        """Handle transferring stock between branches"""
        from_branch_id = request.data.get('from_branch_id')
        to_branch_id = request.data.get('to_branch_id')
        quantity = int(request.data.get('quantity'))
        
        if not all([from_branch_id, to_branch_id]):
            raise ValueError("from_branch_id and to_branch_id are required for transfer action")
            
        if from_branch_id == to_branch_id:
            raise ValueError("Source and destination branches cannot be the same")
        
        # Get or create source stock
        from_branch = Branch.objects.get(id=from_branch_id)
        from_stock, _ = LensStock.objects.get_or_create(
            lens=lens,
            branch=from_branch,
            defaults={'qty': 0, 'initial_count': 0}
        )
        
        # Check if source has enough quantity
        if from_stock.qty < quantity:
            raise ValueError(f"Insufficient stock. Available: {from_stock.qty}")
        
        # Get or create destination stock
        to_branch = Branch.objects.get(id=to_branch_id)
        to_stock, created = LensStock.objects.get_or_create(
            lens=lens,
            branch=to_branch,
            defaults={'qty': 0, 'initial_count': 0}
        )
        
        # Update quantities
        from_stock.qty -= quantity
        to_stock.qty += quantity
        
        # Update initial_count for the destination
        if created or to_stock.initial_count is None:
            to_stock.initial_count = quantity
        else:
            to_stock.initial_count += quantity
            
        from_stock.save()
        to_stock.save()
        
        # Create history record
        LensStockHistory.objects.create(
            lens=lens,
            branch=from_branch,
            transfer_to=to_branch,
            action=LensStockHistory.TRANSFER,
            quantity_changed=quantity
        )
        
        return Response({
            "message": "Transfer successful",
            "from_stock": LensStockSerializer(from_stock).data,
            "to_stock": LensStockSerializer(to_stock).data
        }, status=status.HTTP_200_OK)
    
    def _handle_remove_action(self, request, lens):
        """Handle removing stock from a branch"""
        from_branch_id = request.data.get('from_branch_id')
        quantity = int(request.data.get('quantity'))
        
        if not from_branch_id:
            raise ValueError("from_branch_id is required for remove action")
        
        # Get source stock
        from_branch = Branch.objects.get(id=from_branch_id)
        from_stock = LensStock.objects.get(
            lens=lens,
            branch=from_branch
        )
        
        # Check if source has enough quantity
        if from_stock.qty < quantity:
            raise ValueError(f"Insufficient stock. Available: {from_stock.qty}")
        
        # Update quantity
        from_stock.qty -= quantity
        from_stock.save()
        
        # Create history record
        LensStockHistory.objects.create(
            lens=lens,
            branch=from_branch,
            action=LensStockHistory.REMOVE,
            quantity_changed=quantity
        )
        
        return Response({
            "message": f"Removed {quantity} items from stock",
            "stock": LensStockSerializer(from_stock).data
        }, status=status.HTTP_200_OK)