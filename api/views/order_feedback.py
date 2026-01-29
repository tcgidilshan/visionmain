from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from ..models import OrderFeedback, Order, Invoice
from ..serializers import OrderFeedbackSerializer
from ..services.time_zone_convert_service import TimezoneConverterService

class OrderFeedbackCreateView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = OrderFeedback.objects.all()
    serializer_class = OrderFeedbackSerializer

    def create(self, request, *args, **kwargs):
        # Get the order_id from the request data
        order_id = request.data.get('order')
        
        # Check if feedback already exists for this order
        if order_id and OrderFeedback.objects.filter(order_id=order_id).exists():
            return Response(
                {"error": "Feedback already exists for this order"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If user is not provided in the request, try to get it from the order's issued_by
        if not request.data.get('user') and order_id:
            try:
                order = Order.objects.get(id=order_id)
                if order.issued_by:
                    # Create a mutable copy of the request data
                    data = request.data.copy()
                    data['user'] = order.issued_by.id
                    request._full_data = data
            except Order.DoesNotExist:
                pass
                
        return super().create(request, *args, **kwargs)


class OrderFeedbackByInvoiceView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        invoice_number = request.query_params.get('invoice_number')
        user_id = request.query_params.get('user_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')
        
        # If invoice_number is provided, return feedback for that specific invoice
        if invoice_number:
            return self._get_feedback_by_invoice(invoice_number, branch_id)
            
        # If user_id with date range is provided, return all feedback for that user in the date range
        elif user_id and start_date and end_date:
            try:
                # Convert string dates to timezone-aware datetime objects
                start_dt, end_dt = TimezoneConverterService.format_date_with_timezone(
                    start_date, end_date
                )
                
                if not start_dt or not end_dt:
                    return Response(
                        {"error": "Invalid date format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get all feedback for the user in the date range
                feedbacks = OrderFeedback.objects.filter(
                    user_id=user_id,
                    created_at__range=(start_dt, end_dt)
                ).select_related('order__invoice', 'order__branch')
                
                # Filter by branch_id if provided
                if branch_id:
                    try:
                        branch_id_int = int(branch_id)
                        feedbacks = feedbacks.filter(order__branch_id=branch_id_int)
                    except ValueError:
                        return Response(
                            {"error": "Invalid branch_id. Must be a valid integer"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Prepare response data
                feedbacks_data = []
                for feedback in feedbacks:
                    feedback_data = OrderFeedbackSerializer(feedback).data
                    # Add invoice number if available
                    if hasattr(feedback.order, 'invoice') and feedback.order.invoice:
                        feedback_data['invoice_number'] = feedback.order.invoice.invoice_number
                    feedbacks_data.append(feedback_data)
                
                return Response({
                    "user_id": user_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "branch_id": int(branch_id) if branch_id else None,
                    "count": len(feedbacks_data),
                    "feedbacks": feedbacks_data
                })
                
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {"error": "Either invoice_number or (user_id with start_date and end_date) is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_feedback_by_invoice(self, invoice_number, branch_id=None):
        try:
            # First find the invoice with the given invoice number
            invoice = Invoice.objects.get(invoice_number=invoice_number, is_deleted=False)
            
            # Then get the order from the invoice
            order = invoice.order
            
            # Filter by branch_id if provided
            if branch_id:
                try:
                    branch_id_int = int(branch_id)
                    if order.branch_id != branch_id_int:
                        return Response(
                            {"detail": "Invoice not found for the specified branch"},
                            status=status.HTTP_404_NOT_FOUND
                        )
                except ValueError:
                    return Response(
                        {"error": "Invalid branch_id. Must be a valid integer"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Then get the feedback for this order
            feedback = OrderFeedback.objects.filter(order=order).first()
            
            # Prepare the response data
            response_data = {
                "order_id": order.id,
                "invoice_number": invoice_number,
                "branch_id": int(branch_id) if branch_id else None,
                "feedback_status": feedback is not None,
            }
            
            # Add feedback data if it exists
            if feedback:
                feedback_data = OrderFeedbackSerializer(feedback).data
                response_data["feedback"] = feedback_data
            
            return Response(response_data)
            
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "No invoice found with this invoice number"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )