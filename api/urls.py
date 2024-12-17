from django.urls import path
from .views import LoginView, AdminOnlyView, SuperAdminOnlyView
from .views import UserRegistrationView, AdminRegistrationView
from .views import BranchListCreateAPIView, BranchRetrieveUpdateDestroyAPIView, RefractionCreateAPIView, RefractionListAPIView, RefractionUpdateAPIView,RefractionDeleteAPIView,RefractionDetailCreateAPIView
# from .views import CustomAuthToken

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('admin-only/', AdminOnlyView.as_view(), name='admin-only'),
    path('super-admin/', SuperAdminOnlyView.as_view(), name='super-admin-only'),
    path('register/user/', UserRegistrationView.as_view(), name='user-registration'),
    path('register/admin/', AdminRegistrationView.as_view(), name='admin-registration'),
    path('branches/', BranchListCreateAPIView.as_view(), name='branch-list-create'),
    path('branches/<int:pk>/', BranchRetrieveUpdateDestroyAPIView.as_view(), name='branch-detail'),
    path('refractions/create/', RefractionCreateAPIView.as_view(), name='refraction-create'),
    path('refractions/', RefractionListAPIView.as_view(), name='refraction-list'),
    path('refractions/<int:pk>/update/', RefractionUpdateAPIView.as_view(), name='refraction-update'),
    path('refractions/<int:pk>/delete/', RefractionDeleteAPIView.as_view(), name='refraction-delete'),
    path('refraction-details/create/', RefractionDetailCreateAPIView.as_view(), name='refraction-details-create'),
    ]
    # path('api-token-auth/', CustomAuthToken.as_view(), name='api-token-auth'),

 