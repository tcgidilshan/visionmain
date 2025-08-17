from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import timedelta
import uuid
from ..models import CustomUser

class RestPasswordView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        user_code = request.data.get('user_code')
        
        if not user_code:
            return Response(
                {"error": "user_code is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(user_code=user_code)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Invalid user code"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate a secure UUID4 token
        token = str(uuid.uuid4())
        
        # Set token and expiry (24 hours from now)
        user.reset_token = token
        user.reset_token_expiry = timezone.now() + timedelta(hours=24)
        user.save()
        
        return Response({
            "message": "Password reset token generated successfully",
            "reset_token": token,
            "expires_at": user.reset_token_expiry.isoformat()
        }, status=status.HTTP_200_OK)
    
    def get(self, request):
        reset_token = request.query_params.get('token')
        
        if not reset_token:
            return Response(
                {"error": "Reset token is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(reset_token=reset_token)
            
            # Check if token is expired
            if user.reset_token_expiry and user.reset_token_expiry < timezone.now():
                return Response(
                    {"error": "Reset token has expired"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            return Response({
                "valid": True,
                "user_id": user.id,
                "user_code": user.user_code,
                "email": user.email,
                "expires_at": user.reset_token_expiry.isoformat() if user.reset_token_expiry else None
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Invalid or expired reset token"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class ResetPasswordConfirmView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        reset_token = request.data.get('reset_token')
        new_password = request.data.get('new_password')
        
        if not all([reset_token, new_password]):
            return Response(
                {"error": "Both reset_token and new_password are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            user = CustomUser.objects.get(reset_token=reset_token)
            
            # Check if token is expired
            if user.reset_token_expiry and user.reset_token_expiry < timezone.now():
                return Response(
                    {"error": "Reset token has expired"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Update password and clear reset token
            user.set_password(new_password)
            user.reset_token = None
            user.reset_token_expiry = None
            user.save()
            
            return Response({
                "message": "Password has been reset successfully"
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Invalid or expired reset token"}, 
                status=status.HTTP_404_NOT_FOUND
            )