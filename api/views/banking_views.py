from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError, ObjectDoesNotExist
import logging

from api.services.banking_service import BankingService

logger = logging.getLogger(__name__)


class BankingReportView(APIView):
    """
    Get banking report for a specific branch within date range
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get banking report for a specific branch within date range
        
        Query Parameters:
            - branch_id (required): Branch ID
            - start_date (required): Start date (YYYY-MM-DD)
            - end_date (required): End date (YYYY-MM-DD)
            - is_confirmed (optional): Filter by confirmation status (true/false)
        
        Example: GET /api/banking-report/?branch_id=1&start_date=2024-01-01&end_date=2024-01-31
        """
        try:
            # Extract and validate query parameters
            branch_id = request.query_params.get('branch_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            is_confirmed = request.query_params.get('is_confirmed')
            
            # Validate required parameters
            if not branch_id:
                return Response(
                    {'error': 'branch_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not start_date:
                return Response(
                    {'error': 'start_date is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not end_date:
                return Response(
                    {'error': 'end_date is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert branch_id to integer
            try:
                branch_id = int(branch_id)
            except ValueError:
                return Response(
                    {'error': 'branch_id must be a valid integer'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert is_confirmed to boolean if provided
            confirmed_filter = None
            if is_confirmed is not None:
                if is_confirmed.lower() in ['true', '1', 'yes']:
                    confirmed_filter = True
                elif is_confirmed.lower() in ['false', '0', 'no']:
                    confirmed_filter = False
                else:
                    return Response(
                        {'error': 'is_confirmed must be true or false'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get banking report using service
            report_data = BankingService.get_banking_report(
                branch_id=branch_id,
                start_date=start_date,
                end_date=end_date,
                is_confirmed=confirmed_filter
            )
            
            return Response(
                {
                    'success': True,
                    'message': 'Banking report retrieved successfully',
                    'data': report_data
                },
                status=status.HTTP_200_OK
            )
            
        except ObjectDoesNotExist as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"Banking report error: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfirmDepositView(APIView):
    """
    Confirm or unconfirm a bank deposit (Banking Confirm Action)
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, deposit_id):
        """
        Confirm or unconfirm a bank deposit
        
        URL: PATCH /api/banking-report/confirm/{deposit_id}/
        
        Body:
            {
                "is_confirmed": true/false
            }
        """
        try:
            # Validate deposit_id
            try:
                deposit_id = int(deposit_id)
            except ValueError:
                return Response(
                    {'error': 'deposit_id must be a valid integer'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get confirmation status from request body
            is_confirmed = request.data.get('is_confirmed')
            
            if is_confirmed is None:
                return Response(
                    {'error': 'is_confirmed field is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not isinstance(is_confirmed, bool):
                return Response(
                    {'error': 'is_confirmed must be a boolean value'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update deposit confirmation using service
            updated_deposit = BankingService.confirm_deposit(
                deposit_id=deposit_id,
                confirm_status=is_confirmed
            )
            
            action = "confirmed" if is_confirmed else "unconfirmed"
            message = f"Deposit {action} successfully"
            
            return Response(
                {
                    'success': True,
                    'message': message,
                    'data': updated_deposit
                },
                status=status.HTTP_200_OK
            )
            
        except ObjectDoesNotExist as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            logger.error(f"Confirm deposit error: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )