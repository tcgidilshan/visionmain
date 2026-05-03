from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import timedelta
import uuid
import random
from ..models import CustomUser
from ..services.send_sms_service import SMSService


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

        if not user.mobile:
            return Response(
                {"error": "No mobile number registered for this account. Contact your administrator."},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp = str(random.randint(1000, 9999))
        user.reset_token = otp
        user.reset_token_expiry = timezone.now() + timedelta(minutes=10)
        user.save()

        try:
            SMSService.send_sms(
                mobile_numbers=[user.mobile],
                message=f"Your VisionPlus password reset OTP is: {otp}. Valid for 10 minutes. Do not share this code."
            )
        except Exception:
            return Response(
                {"error": "Failed to send OTP. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        mobile_hint = f"****{user.mobile[-4:]}" if len(user.mobile) >= 4 else "****"

        return Response({
            "message": "OTP sent to your registered mobile number",
            "mobile_hint": mobile_hint,
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_code = request.data.get('user_code')
        otp = request.data.get('otp')

        if not user_code or not otp:
            return Response(
                {"error": "user_code and otp are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(user_code=user_code)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Invalid user code"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not user.reset_token or user.reset_token != str(otp):
            return Response(
                {"error": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.reset_token_expiry and user.reset_token_expiry < timezone.now():
            return Response(
                {"error": "OTP has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST
            )

        verified_token = str(uuid.uuid4())
        user.reset_token = verified_token
        user.reset_token_expiry = timezone.now() + timedelta(minutes=5)
        user.save()

        return Response({"verified_token": verified_token}, status=status.HTTP_200_OK)


class ResetPasswordConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        verified_token = request.data.get('reset_token')
        new_password = request.data.get('new_password')

        if not all([verified_token, new_password]):
            return Response(
                {"error": "Both reset_token and new_password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(reset_token=verified_token)

            if user.reset_token_expiry and user.reset_token_expiry < timezone.now():
                return Response(
                    {"error": "Session expired. Please start the reset process again."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(new_password)
            user.reset_token = None
            user.reset_token_expiry = None
            user.save()

            return Response({"message": "Password has been reset successfully"}, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Invalid or expired session. Please start the reset process again."},
                status=status.HTTP_404_NOT_FOUND
            )
