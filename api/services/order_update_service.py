from ..models import Order,Frame,OrderProgress, OtherItem,OrderItem, LensStock, LensCleanerStock, FrameStock,Lens,LensCleaner,Frame,ExternalLens,OtherItemStock,BusSystemSetting, HearingItem, HearingItemStock, Expense, ExpenseMainCategory, ExpenseSubCategory, OrderPayment
from ..serializers import OrderSerializer, OrderItemSerializer, ExternalLensSerializer
from django.db import transaction
from django.db.models import Sum
from ..services.order_payment_service import OrderPaymentService
from ..services.external_lens_service import ExternalLensService
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from ..services.check_stock_avilability import StockAvilabilityService
from django.utils import timezone
from decimal import Decimal, InvalidOperation


class OrderUpdateService:
    @staticmethod
    def get_stock_for_item(order_item_data, branch_id):
        """
        Retrieves stock object and type for a given order item.
        Skips external_lens and is_non_stock items.
        
        Returns:
            tuple: (stock_object, stock_type) or (None, 'external_lens')
        """

        # Skip external lenses - they don't maintain stock
        if order_item_data.get('external_lens'):
            return None, 'external_lens'
        
        stock = None
        stock_type = None
        
        if order_item_data.get('lens'):
            stock = LensStock.objects.select_for_update().filter(
                lens_id=order_item_data['lens'],
                branch_id=branch_id
            ).first()
            stock_type = 'lens'
        
        elif order_item_data.get('lens_cleaner'):
            stock = LensCleanerStock.objects.select_for_update().filter(
                lens_cleaner_id=order_item_data['lens_cleaner'],
                branch_id=branch_id
            ).first()
            stock_type = 'lens_cleaner'
        
        elif order_item_data.get('frame'):
            stock = FrameStock.objects.select_for_update().filter(
                frame_id=order_item_data['frame'],
                branch_id=branch_id
            ).first()
            stock_type = 'frame'
        
        elif order_item_data.get('other_item'):
            stock = OtherItemStock.objects.select_for_update().filter(
                other_item_id=order_item_data['other_item'],
                branch_id=branch_id
            ).first()
            stock_type = 'other_item'
        
        elif order_item_data.get('hearing_item'):
            stock = HearingItemStock.objects.select_for_update().filter(
                hearing_item_id=order_item_data['hearing_item'],
                branch_id=branch_id
            ).first()
            stock_type = 'hearing_item'
        
        return stock, stock_type
    #handle on holde for lens utill
    @staticmethod
    def handle_lens_stock_adjustment(stock, qty_diff,item_data, previous_on_hold, new_on_hold, is_refund):
        if is_refund:
            if  not previous_on_hold:
            # For refunds, simply add back the refunded quantity
                stock.qty += item_data['quantity']
                stock.save()
            else:
                # If previously on hold, no stock adjustment needed for refund
                pass

        else:
            if previous_on_hold == False and new_on_hold == False:
                # Case 1: Not on hold before or after - adjust normally
                if qty_diff > 0:
                    # Reducing stock
                    if stock.qty < qty_diff:
                        raise ValueError("Insufficient stock available.")
                    stock.qty -= qty_diff
                    stock.save()
                elif qty_diff < 0:
                    # Increasing stock
                    stock.qty += abs(qty_diff)
                    stock.save()

            elif previous_on_hold == True and new_on_hold == False:
                # Case 2: Was on hold, now not on hold - reduce stock for full quantity
                if stock.qty < item_data['quantity']:
                    #add the lens name as well in erro msg 
                    
                    raise ValueError(f"Insufficient stock for lens. Available: {stock.qty}, Required: {item_data['quantity']}")
                stock.qty -= item_data['quantity']
                stock.save()

            elif previous_on_hold == False and new_on_hold == True:
                # Case 3: Was not on hold, now on hold - restore stock for full quantity
                stock.qty += item_data['quantity']
                stock.save()

            elif previous_on_hold == True and new_on_hold == True:
                # Case 4: On hold before and after - no stock change
                pass


    @staticmethod
    @transaction.atomic
    def on_change_append(existing_item: OrderItem, new_data: dict, admin_id: int, user_id: int):
        """
        Medical-compliant item update with append-on-change logic.
        1. If any tracked field changes: soft-delete old, create new (copying original order ref, user/admin).
        2. If not changed: just return original (do nothing).
        """
        TRACKED_FIELDS = [
            "price_per_unit", "subtotal", "external_lens", "lens", "frame",
            "lens_cleaner", "other_item", "note", "quantity", "hearing_item","serial_no","battery","next_service_date"
        ]
        FK_FIELDS = {
            'frame': Frame,
            'lens': Lens,
            'external_lens': ExternalLens,
            'lens_cleaner': LensCleaner,
            'other_item': OtherItem,
            'hearing_item': HearingItem,
        }

        # Always recalculate subtotal using Decimal (ignore frontend subtotal)
        if 'quantity' in new_data and 'price_per_unit' in new_data:
            try:
                q = Decimal(str(new_data['quantity']))
                p = Decimal(str(new_data['price_per_unit']))
                new_data['subtotal'] = q * p
            except Exception:
                new_data['subtotal'] = Decimal('0.00')

        changed = False

        # Detect field changes robustly
        for field in TRACKED_FIELDS:
            old = getattr(existing_item, field)
            new = new_data.get(field, old)
            if field in FK_FIELDS:
                old_id = getattr(old, 'id', old) if old else None
                new_id = new if isinstance(new, int) else getattr(new, 'id', new) if new else None
                if old_id != new_id:
                    changed = True
                    break
            elif field in ["price_per_unit", "subtotal"]:
                try:
                    old_val = Decimal(str(old)) if old is not None else None
                    new_val = Decimal(str(new)) if new is not None else None
                    if old_val != new_val:
                        changed = True
                        break
                except (InvalidOperation, TypeError):
                    if old != new:
                        changed = True
                        break
            elif field == "next_service_date":
                # Handle date comparison properly
                old_date = old.isoformat() if old else None
                new_date = new.isoformat() if hasattr(new, 'isoformat') else new
                if old_date != new_date:
                    changed = True
                    break
            elif field == "quantity":
                try:
                    if int(old) != int(new):
                        changed = True
                        break
                except Exception:
                    if old != new:
                        changed = True
                        break
            else:
                if old != new:
                    changed = True
                    break

        if changed:
            # //TODO: Soft-delete the old item for compliance
            existing_item.is_deleted = True
            existing_item.deleted_at = timezone.now()
            existing_item.admin_id = admin_id  
            existing_item.user_id = user_id
            existing_item.save()

            # //TODO: Prepare new item data with proper FK resolution
            new_item_data = {
                **new_data,
                "order": existing_item.order,
                "admin_id": admin_id,
                "user_id": user_id,
            }
            new_item_data.pop("id", None)  # Ensure id not reused

            # Resolve FK IDs to instances
            for field, model in FK_FIELDS.items():
                value = new_item_data.get(field)
                if value and not isinstance(value, model):
                    new_item_data[field] = model.objects.get(pk=value)
                elif not value:
                    new_item_data[field] = None

            # //TODO: Audit log creation could be inserted here for regulatory trace
            new_item = OrderItem.objects.create(**new_item_data)
            return new_item
        else:
            # No changes: keep as is, don't update or touch
            return existing_item
  
    @staticmethod
    @transaction.atomic
    def update_order(order, order_data, order_items_data, payments_data, admin_id, user_id):
        """
        Updates an order with comprehensive handling of:
        - Item updates (on-change-append pattern)
        - New item creation
        - Item refunds with discount edge cases
        - Stock management (external_lens and is_non_stock items skipped)
        - On-hold order transitions
        - Progress status tracking
        - Payment synchronization
        """
        if order.is_deleted:
            raise ValidationError("This order has been deleted and cannot be modified.")
        
        try:
            branch_id = order.branch_id
            if not branch_id:
                raise ValueError("Order is not associated with a branch.")

            # Track on_hold flag changes
            previous_on_hold = order.on_hold
            new_on_hold = order_data.get("on_hold")

            # Fetch existing items once (O(1) query)
            existing_items = {item.id: item for item in order.order_items.filter(is_deleted=False)}
            for item_data in order_items_data:
                item_id = item_data.get('id',None)
                existing_item = existing_items[item_id] if item_id else None
                is_refund = item_data.get('is_refund')
                if item_id and item_id in existing_items:
                    #step 1: validate stock adn return validated data 
                    stock, stock_type = OrderUpdateService.get_stock_for_item(item_data, branch_id)

                    #step 2: check stock deferance and prepare stock adjustments
                    if existing_item:
                        qty_diff = item_data['quantity'] - existing_item.quantity
                        ## update stocks acording to diff or - reduce of plus add

                        if stock and stock_type != 'external_lens':
                            
                            # handle onhold transition for lens stock
                            #calse 1 previus on hold false new on hold false
                            #case 2 previus on hold true new on hold false
                            # case 3 previus on hold false new on hold true
                            # case 4 previus on hold true new on hold true
                            
                            if stock_type == 'lens':
                                OrderUpdateService.handle_lens_stock_adjustment(
                                    stock, qty_diff, previous_on_hold, new_on_hold, is_refund=is_refund, refund_qty=item_data['quantity'] if is_refund else 0
                                )
                               
                            elif stock_type != 'lens' and not is_refund:
                                if stock.qty < qty_diff:
                                    raise ValueError(f"Insufficient stock for item ID {item_id}. Available: {stock.qty}, Required additional: {qty_diff}")
                                stock.qty += qty_diff
                                stock.save()
                        elif stock and stock_type != 'external_lens' and is_refund :
                            stock.qty += item_data['quantity']
                            stock.save()
                    # Step 3: Update item using on-change-append logic
                    OrderUpdateService.on_change_append(
                        existing_item, item_data, admin_id, user_id
                    )
                else:
                    #create new items
                    #step 1: validate stock adn return validated data 
                    stock, stock_type = OrderUpdateService.get_stock_for_item(item_data, branch_id)
                        
                        
                    

                    


        except ExternalLens.DoesNotExist:
            raise ValueError("Invalid External Lens ID.")
        except Exception as e:
            transaction.set_rollback(True)
            raise ValueError(f"Order update failed: {str(e)}")