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
        
        Single Operation:
        {
            "operations": [
                {
                    "action": "add",
                    "lens_id": 1,
                    "to_branch_id": 2,
                    "quantity": 5
                },
                {
                    "action": "transfer",
                    "lens_id": 2,
                    "from_branch_id": 1,
                    "to_branch_id": 3,
                    "quantity": 3
                },
                {
                    "action": "remove",
                    "lens_id": 3,
                    "from_branch_id": 1,
                    "quantity": 2
                }
            ]
        }
        
        Each operation in the operations array can be one of:
        
        1. ADD action:
        {
            "action": "add",
            "lens_id": 1,              # ID of the lens
            "to_branch_id": 2,          # Destination branch ID
            "quantity": 5               # Quantity to add
        }
        
        2. TRANSFER action:
        {
            "action": "transfer",
            "lens_id": 1,              # ID of the lens
            "from_branch_id": 1,        # Source branch ID
            "to_branch_id": 2,          # Destination branch ID
            "quantity": 5               # Quantity to transfer
        }
        
        3. REMOVE action:
        {
            "action": "remove",
            "lens_id": 1,              # ID of the lens
            "from_branch_id": 1,        # Branch ID to remove from
            "quantity": 2               # Quantity to remove
        }
        """
        operations = request.data.get('operations', [])
        
        if not operations:
            return Response(
                {"error": "No operations provided. Use 'operations' array to specify actions."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        
        try:
            # Pre-fetch all lenses and branches to reduce DB queries
            lens_ids = {op.get('lens_id') for op in operations if op.get('lens_id')}
            branch_ids = set()
            
            for op in operations:
                if 'to_branch_id' in op:
                    branch_ids.add(op['to_branch_id'])
                if 'from_branch_id' in op:
                    branch_ids.add(op['from_branch_id'])
            
            # Get all lenses and branches in one query each
            lenses = {lens.id: lens for lens in Lens.objects.filter(id__in=lens_ids, is_active=True)}
            branches = {branch.id: branch for branch in Branch.objects.filter(id__in=branch_ids)}
            
            for idx, operation in enumerate(operations):
                try:
                    action = operation.get('action', '').lower()
                    lens_id = operation.get('lens_id')
                    quantity = operation.get('quantity')
                    
                    # Validate common required fields
                    if not all([action, lens_id is not None, quantity is not None]):
                        results.append({
                            "index": idx,
                            "status": "error",
                            "error": "action, lens_id, and quantity are required"
                        })
                        continue
                        
                    if quantity <= 0:
                        results.append({
                            "index": idx,
                            "status": "error",
                            "error": "Quantity must be greater than 0"
                        })
                        continue
                    
                    # Check if lens exists and is active
                    lens = lenses.get(lens_id)
                    if not lens:
                        results.append({
                            "index": idx,
                            "status": "error",
                            "error": f"Lens with ID {lens_id} not found or is inactive"
                        })
                        continue
                    
                    # Handle the action
                    if action == 'add':
                        result = self._handle_add_action(operation, lens, branches)
                    elif action == 'transfer':
                        result = self._handle_transfer_action(operation, lens, branches)
                    elif action == 'remove':
                        result = self._handle_remove_action(operation, lens, branches)
                    else:
                        results.append({
                            "index": idx,
                            "status": "error",
                            "error": "Invalid action. Must be one of: add, transfer, remove"
                        })
                        continue
                    
                    results.append({
                        "index": idx,
                        "status": "success",
                        "action": action,
                        "lens_id": lens_id,
                        **result
                    })
                    
                except Branch.DoesNotExist as e:
                    results.append({
                        "index": idx,
                        "status": "error",
                        "error": "Branch not found"
                    })
                except ValueError as e:
                    results.append({
                        "index": idx,
                        "status": "error",
                        "error": str(e)
                    })
                except Exception as e:
                    results.append({
                        "index": idx,
                        "status": "error",
                        "error": str(e)
                    })
            
            # Check if all operations failed
            if all(result.get('status') == 'error' for result in results):
                return Response(
                    {"results": results},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            return Response({"results": results}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_add_action(self, operation, lens, branches):
        """Handle adding stock to a branch"""
        to_branch_id = operation.get('to_branch_id')
        quantity = int(operation.get('quantity'))
        
        if not to_branch_id:
            raise ValueError("to_branch_id is required for add action")
            
        # Get destination branch from pre-fetched branches
        to_branch = branches.get(to_branch_id)
        if not to_branch:
            raise Branch.DoesNotExist(f"Branch with ID {to_branch_id} not found")
            
        # Get or create destination stock
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
        
        return {
            "message": "Stock added successfully",
            "to_branch_id": to_branch_id,
            "quantity": quantity,
            "stock": LensStockSerializer(to_stock).data
        }
    
    def _handle_transfer_action(self, operation, lens, branches):
        """Handle transferring stock between branches"""
        from_branch_id = operation.get('from_branch_id')
        to_branch_id = operation.get('to_branch_id')
        quantity = int(operation.get('quantity'))
        
        if not all([from_branch_id, to_branch_id]):
            raise ValueError("from_branch_id and to_branch_id are required for transfer action")
            
        if from_branch_id == to_branch_id:
            raise ValueError("Source and destination branches cannot be the same")
        
        # Get branches from pre-fetched branches
        from_branch = branches.get(from_branch_id)
        to_branch = branches.get(to_branch_id)
        
        if not from_branch:
            raise Branch.DoesNotExist(f"Source branch with ID {from_branch_id} not found")
        if not to_branch:
            raise Branch.DoesNotExist(f"Destination branch with ID {to_branch_id} not found")
        
        # Get or create source stock
        from_stock, _ = LensStock.objects.get_or_create(
            lens=lens,
            branch=from_branch,
            defaults={'qty': 0, 'initial_count': 0}
        )
        
        # Check if source has enough quantity
        if from_stock.qty < quantity:
            raise ValueError(f"Insufficient stock. Available: {from_stock.qty}")
        
        # Get or create destination stock
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
        
        return {
            "message": "Transfer successful",
            "from_branch_id": from_branch_id,
            "to_branch_id": to_branch_id,
            "quantity": quantity,
            "from_stock": LensStockSerializer(from_stock).data,
            "to_stock": LensStockSerializer(to_stock).data
        }
    
    def _handle_remove_action(self, operation, lens, branches):
        """Handle removing stock from a branch"""
        from_branch_id = operation.get('from_branch_id')
        quantity = int(operation.get('quantity'))
        
        if not from_branch_id:
            raise ValueError("from_branch_id is required for remove action")
        
        # Get branch from pre-fetched branches
        from_branch = branches.get(from_branch_id)
        if not from_branch:
            raise Branch.DoesNotExist(f"Branch with ID {from_branch_id} not found")
        
        # Get source stock
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
        
        return {
            "message": f"Removed {quantity} items from stock",
            "from_branch_id": from_branch_id,
            "quantity": quantity,
            "stock": LensStockSerializer(from_stock).data
        }