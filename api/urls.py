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
    FrameColorListView,
    PowerListCreateView,
    PowerRetrieveUpdateDeleteView,
    LensListCreateView,
    LensRetrieveUpdateDeleteView,
    LensPowerListCreateView,
    LensPowerRetrieveUpdateDeleteView,
    LensCleanerListCreateView,
    LensCleanerRetrieveUpdateDeleteView,
    LensCleanerStockListCreateView,
    LensCleanerStockRetrieveUpdateDeleteView,
    OrderCreateView,
    DoctorListCreateView,
    DoctorRetrieveUpdateDeleteView,
    PatientListView,
    PatientUpdateView,# Added by Lahiru
    ChannelAppointmentView,
    ChannelListView,
    AppointmentRetrieveUpdateDeleteView,
    LensStockListCreateView,
    LensStockRetrieveUpdateDeleteView,
    LensTypeListCreateView,
    LensTypeRetrieveUpdateDeleteView,
    LensCoatingListCreateView,
    LensCoatingRetrieveUpdateDeleteView,
    ManualOrderCreateView,
    InvoiceDetailView,
    OrderUpdateView,
    RefractionDetailRetrieveUpdateDeleteView,
    LensSearchView,
    PaymentView,
    OtherItemListCreateView,
    OtherItemRetrieveUpdateDeleteView,
    CreateUserView,
    UserCodeCheckView,ChannelTransferView,DoctorAbsenceRescheduleView,
    UpdateUserView,GetAllUsersView,GetSingleUserView,FactoryInvoiceSearchView,InvoiceProgressUpdateView,InvoiceReportView,
    AdminCodeCheckView,ChannelReportView,DoctorScheduleCreateView,DoctorUpcomingScheduleView,DoctorScheduleTransferView,AllRoleCheckView,
    UpdateUserView,GetAllUsersView,GetSingleUserView,FactoryInvoiceSearchView,InvoiceProgressUpdateView,InvoiceReportView,BulkInvoiceProgressUpdateView,
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
    path("users/create/", CreateUserView.as_view(), name="create-user"), 
    path("users/update/<int:user_id>/", UpdateUserView.as_view(), name="update-user"),
    path("users/get/<int:user_id>/", GetSingleUserView.as_view(), name="get-single-user"),
    path("users/", GetAllUsersView.as_view(), name="get-all-users"),
    path("user/check-code/", UserCodeCheckView.as_view(), name="check-user-code"),
    path("admin/check-code/", AdminCodeCheckView.as_view(), name="check-user-code"),
    path("admin-and-user/check-code/", AllRoleCheckView.as_view(), name="check-user-and-admin-code"),
    path('refractions/create/', RefractionCreateAPIView.as_view(), name='refraction-create'),
    path('refractions/', RefractionListAPIView.as_view(), name='refraction-list'),
    path('refractions/<int:pk>/update/', RefractionUpdateAPIView.as_view(), name='refraction-update'),#Update Retrive refraction NUmber
    path('refractions/<int:pk>/delete/', RefractionDeleteAPIView.as_view(), name='refraction-delete'),
    path('refraction-details/create/', RefractionDetailCreateAPIView.as_view(), name='refraction-details-create'),
    path('refraction-details/<int:refraction_id>/', RefractionDetailRetrieveUpdateDeleteView.as_view(), name='refraction-details'),
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
    path("frames/colors/", FrameColorListView.as_view(), name="frame-colors"),
    path('powers/', PowerListCreateView.as_view(), name='power-list-create'),
    path('powers/<int:pk>/', PowerRetrieveUpdateDeleteView.as_view(), name='power-detail'),
    path('lenses/', LensListCreateView.as_view(), name='lens-list-create'),
    path('lenses/<int:pk>/', LensRetrieveUpdateDeleteView.as_view(), name='lens-detail'),
    path('lens-powers/', LensPowerListCreateView.as_view(), name='lens-power-list-create'),
    path('lens-powers/<int:pk>/', LensPowerRetrieveUpdateDeleteView.as_view(), name='lens-power-detail'),
    path('lens-cleaners/', LensCleanerListCreateView.as_view(), name='lens-cleaner-list-create'),
    path('lens-cleaners/<int:pk>/', LensCleanerRetrieveUpdateDeleteView.as_view(), name='lens-cleaner-detail'),
    path('lens-cleaner-stocks/', LensCleanerStockListCreateView.as_view(), name='lens-cleaner-stock-list-create'),
    path('lens-cleaner-stocks/<int:pk>/', LensCleanerStockRetrieveUpdateDeleteView.as_view(), name='lens-cleaner-stock-detail'),
    path('other-items/', OtherItemListCreateView.as_view(), name='other-item-list-create'),
    path('other-items/<int:pk>/', OtherItemRetrieveUpdateDeleteView.as_view(), name='other-item-detail'),
    path('orders/', OrderCreateView.as_view(), name='order-create'),
    path('orders/<int:pk>/', OrderUpdateView.as_view(), name='order-update'),
    # path("manual-orders/", ManualOrderCreateView.as_view(), name="manual-order-create"),
    path('orders/update-payments/', PaymentView.as_view(), name='update-payments'),
    path('orders/payments/', PaymentView.as_view(), name='order-payments'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'), #invoice
    path('invoices/', InvoiceDetailView.as_view(), name='invoice-by-order'),  # ✅ Filter by order_id
    path('factory-invoices/<int:pk>/update-status/', InvoiceProgressUpdateView.as_view(), name='factory-invoice-status-update'),
    path('factory-invoices/bulk-update-status/', BulkInvoiceProgressUpdateView.as_view(), 
     name='factory-invoice-bulk-status-update'),
    path("factory-invoices/search/", FactoryInvoiceSearchView.as_view(), name="factory-invoice-search"),
    path('reports/invoices/', InvoiceReportView.as_view(), name='invoice-report'),

    #accounts
    path('reports/channels/', ChannelReportView.as_view(), name="channel-report"),
    path('doctors/', DoctorListCreateView.as_view(), name='doctor-list-create'),
    path('doctors/<int:pk>/', DoctorRetrieveUpdateDeleteView.as_view(), name='doctor-detail'),
    path('doctor-schedule/create/', DoctorScheduleCreateView.as_view(), name='doctor-schedule-create'),
    path('doctor-schedule/<int:doctor_id>/upcoming/', DoctorUpcomingScheduleView.as_view(), name='doctor-schedule-upcoming'),
    path('doctor-schedule/transfer/', DoctorScheduleTransferView.as_view(), name='doctor-schedule-transfer'),
    path('doctor-absence/reschedule/', DoctorAbsenceRescheduleView.as_view(), name='doctor-absence-reschedule'),
    path('patients/', PatientListView.as_view(), name='patient-list'),
    path('patients/<int:pk>/', PatientUpdateView.as_view(), name='patient-update'),# Added by Lahiru to update patient need review
    path('channel/', ChannelAppointmentView.as_view(), name='channel-appointment'),
    path('channels/', ChannelListView.as_view(), name='channel-list'),
    path('channels/<int:pk>/', AppointmentRetrieveUpdateDeleteView.as_view(), name='appointment-detail'),
    path("channel/transfer/", ChannelTransferView.as_view(), name="channel-transfer"),
    path('lens-stocks/', LensStockListCreateView.as_view(), name='lens-stock-list-create'),
    path('lens-stocks/<int:pk>/', LensStockRetrieveUpdateDeleteView.as_view(), name='lens-stock-detail'),
    path("lenses/search/", LensSearchView.as_view(), name="lens-search"),
    path('lens-types/', LensTypeListCreateView.as_view(), name='lens-type-list-create'),
    path('lens-types/<int:pk>/', LensTypeRetrieveUpdateDeleteView.as_view(), name='lens-type-detail'),
    path('lens-coatings/', LensCoatingListCreateView.as_view(), name='lens-coating-list-create'),
    path('lens-coatings/<int:pk>/', LensCoatingRetrieveUpdateDeleteView.as_view(), name='lens-coating-detail'),
    ]
    # path('api-token-auth/', CustomAuthToken.as_view(), name='api-token-auth'),

 