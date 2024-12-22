from django.urls import path
from .views import LoginView, AdminOnlyView, SuperAdminOnlyView
from .views import UserRegistrationView, AdminRegistrationView
from .views import (
    BranchListCreateAPIView,
    BranchRetrieveUpdateDestroyAPIView,
    RefractionCreateAPIView,
    RefractionListAPIView,
    RefractionUpdateAPIView,
    RefractionDeleteAPIView,
    RefractionDetailCreateAPIView,
    BrandListCreateView,
    BrandRetrieveUpdateDeleteView,
    ColorListCreateView,
    ColorRetrieveUpdateDeleteView,
    CodeListCreateView,
    CodeRetrieveUpdateDeleteView,
    FrameStockListCreateView,
    FrameStockRetrieveUpdateDeleteView,
    FrameListCreateView,
    FrameRetrieveUpdateDeleteView,
    PowerListCreateView,
    PowerRetrieveUpdateDeleteView,
    LensListCreateView,
    LensRetrieveUpdateDeleteView,
    LensPowerListCreateView,
    LensPowerRetrieveUpdateDeleteView
    
)
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
    path('brands/', BrandListCreateView.as_view(), name='brand-list-create'),
    path('brands/<int:pk>/', BrandRetrieveUpdateDeleteView.as_view(), name='brand-detail'),
    path('colors/', ColorListCreateView.as_view(), name='color-list-create'),
    path('colors/<int:pk>/', ColorRetrieveUpdateDeleteView.as_view(), name='color-detail'),
    path('codes/', CodeListCreateView.as_view(), name='code-list-create'),
    path('codes/<int:pk>/', CodeRetrieveUpdateDeleteView.as_view(), name='code-detail'),
    path('frame-stocks/', FrameStockListCreateView.as_view(), name='frame-stock-list-create'),
    path('frame-stocks/<int:pk>/', FrameStockRetrieveUpdateDeleteView.as_view(), name='frame-stock-detail'),
    path('frames/', FrameListCreateView.as_view(), name='frame-list-create'),
    path('frames/<int:pk>/', FrameRetrieveUpdateDeleteView.as_view(), name='frame-detail'),
    path('powers/', PowerListCreateView.as_view(), name='power-list-create'),
    path('powers/<int:pk>/', PowerRetrieveUpdateDeleteView.as_view(), name='power-detail'),
    path('lenses/', LensListCreateView.as_view(), name='lens-list-create'),
    path('lenses/<int:pk>/', LensRetrieveUpdateDeleteView.as_view(), name='lens-detail'),
    path('lens-powers/', LensPowerListCreateView.as_view(), name='lens-power-list-create'),
    path('lens-powers/<int:pk>/', LensPowerRetrieveUpdateDeleteView.as_view(), name='lens-power-detail'),

    ]
    # path('api-token-auth/', CustomAuthToken.as_view(), name='api-token-auth'),

 