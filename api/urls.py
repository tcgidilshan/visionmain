from django.urls import path
from .views import LoginView, AdminOnlyView, SuperAdminOnlyView
from .views import UserRegistrationView, AdminRegistrationView
from django.conf import settings
from django.conf.urls.static import static
from .views.inventory_transfer import LensTransferView
from .views import (
    BranchListCreateAPIView,OrderRefundView,FactoryOrderReportView,
    BranchRetrieveUpdateDestroyAPIView,NormalOrderReportView,
    RefractionCreateAPIView,ChannelOrderReportView,
    RefractionListAPIView,BranchAppointmentCountView,
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
    PatientUpdateView,
    ChannelAppointmentView,
    ChannelListView,RefundChannelView,
    DoctorAppointmentTimeListView,
    AppointmentRetrieveUpdateDeleteView,
    LensStockListCreateView,CancelChannelView,
    LensStockRetrieveUpdateDeleteView,ChannelUpdateView,
    LensTypeListCreateView,SafeTransactionView,OrderSoftDeleteView,
    LensTypeRetrieveUpdateDeleteView,ExternalLensCoatingListCreateView,
    ExternalLensCoatingRetrieveUpdateDeleteView,SafeAll,
    LensCoatingListCreateView,ExternalLensBrandListCreateView,
    ExternalLensBrandRetrieveUpdateDeleteView,SafeIncomeTotalView,StockAdjustmentView,
    LensCoatingRetrieveUpdateDeleteView,FrameOnlyOrderCreateView,CreateSolderingOrderView,
   ChannelRepaymentView,ManualOrderCreateView,DoctorAppointmentTransferView,ChannelRepaymentView,AppointmentStatusListView,
    InvoiceDetailView,BankDepositListCreateView,BankDepositRetrieveUpdateView,
    OrderUpdateView,DailyFinanceSummaryView,FrameReportView,
    RefractionDetailRetrieveUpdateDeleteView,BusSystemSettingListCreateView,BusSystemSettingRetrieveUpdateDeleteView,
    LensSearchView,OtherIncomeListCreateView,OtherIncomeRetrieveUpdateDeleteView,OtherIncomeCategoryListCreateView,
    OtherIncomeCategoryRetrieveUpdateView,DailySummaryView,
    PaymentView,ExternalLensListCreateView,ExternalLensRetrieveUpdateDeleteView,
    OtherItemListCreateView,BankAccountListCreateView,BankAccountRetrieveUpdateDeleteView,
    OtherItemRetrieveUpdateDeleteView,ExpenseCreateView,ExpenseUpdateView,
    CreateUserView,ExpenseMainCategoryListCreateView, ExpenseMainCategoryRetrieveUpdateDestroyView,
    ExpenseSubCategoryListCreateView, ExpenseSubCategoryRetrieveUpdateDestroyView,ExpenseRetrieveView,
    UserCodeCheckView,ChannelTransferView,DoctorAbsenceRescheduleView,ExpenseReportView,FrameOnlyOrderUpdateView,
    AdminCodeCheckView,ChannelReportView,DoctorScheduleCreateView,DoctorUpcomingScheduleView,DoctorScheduleTransferView,AllRoleCheckView,
    UpdateUserView,GetAllUsersView,GetSingleUserView,FactoryInvoiceSearchView,InvoiceProgressUpdateView,InvoiceReportView,BulkUpdateOrderProgressStatus,FactoryInvoiceExternalLenseSearchView,BulkOrderWhatsAppLogView,
    DoctorClaimInvoiceListCreateView,DoctorClaimInvoiceRetrieveUpdateDestroyView,
    DoctorClaimChannelListCreateView,DoctorClaimChannelRetrieveUpdateDestroyView,
    SolderingOrderProgressUpdateView,SolderingInvoiceSearchView,SolderingOrderEditView,InvoiceNumberSearchView,OrderUpdateFitStatusView,FittingStatusReportView,OrderDeliveryMarkView,
    GlassSenderReportView,OrderDeleteRefundListView,OrderProgressStatusListView,OrderAuditHistoryView,MntOrderReportView,
    ArrivalStatusBulkCreateView,DailyOrderAuditReportView,FrameTransferView,FrameFilterView,
    FrameHistoryReportView,FrameSaleReportView,LensSaleReportView,OrderImageListCreateView, OrderImageDetailView,OtherIncomeReportView,SafeTransactionReportView,SolderingOrderReportView,
    PaymentSummaryReportView,DoctorBranchChannelFeesCreateView,DoctorBranchChannelFeesListView,DoctorBranchChannelFeesUpdateView,OrderFeedbackCreateView,
    LensHistoryReportView,FrameBrandReportView
)
from .views.customer_report_views import BestCustomersReportView
from .views.employee_report_views import EmployeeHistoryReportView
from .views.banking_views import BankingReportView,ConfirmDepositView
from .views.customer_report_views import CustomerLocationStatisticsView,CustomerLocationTableView
from .views.order_feedback import OrderFeedbackCreateView, OrderFeedbackByInvoiceView

# from .views import CustomAuthToken

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('admin-only/', AdminOnlyView.as_view(), name='admin-only'),
    path('super-admin/', SuperAdminOnlyView.as_view(), name='super-admin-only'),
    path('register/user/', UserRegistrationView.as_view(), name='user-registration'),
    path('register/admin/', AdminRegistrationView.as_view(), name='admin-registration'),
    path('branches/', BranchListCreateAPIView.as_view(), name='branch-list-create'),
    path('branches/<int:pk>/', BranchRetrieveUpdateDestroyAPIView.as_view(), name='branch-detail'),

    #bank
    path('bank_accounts/', BankAccountListCreateView.as_view(), name='bank_account_list_create'),
    path('bank_accounts/<int:id>/', BankAccountRetrieveUpdateDeleteView.as_view(), name='bank_account_detail_update_delete'),

    #other incomes
    path('other-income-categories/', OtherIncomeCategoryListCreateView.as_view(), name='other-income-category-list'),
    path('other-income-categories/<int:pk>/', OtherIncomeCategoryRetrieveUpdateView.as_view(), name='other-income-category-detail'),

    #finance
    path('finance-summary/', DailyFinanceSummaryView.as_view(), name='daily-finance-summary'),

    path('other-incomes/', OtherIncomeListCreateView.as_view(), name='other-income-list'),
    path('other-incomes/<int:pk>/', OtherIncomeRetrieveUpdateDeleteView.as_view(), name='other-income-detail'),
    path('other-incomes/report/', OtherIncomeReportView.as_view(), name='other-income-report'),

    path("safe/transactions/", SafeTransactionView.as_view(), name="safe-transaction-create"),#safe
    path("safe/transactions/report/", SafeTransactionReportView.as_view(), name="safe-transaction-report"),#safe
    path('safe/income-total/', SafeIncomeTotalView.as_view(), name='safe-income-total'),

    path('safe/balance/', SafeAll.as_view(), name='safe-balance'),

    #bank deposit
    path('bank-deposits/', BankDepositListCreateView.as_view(), name='bank-deposit-list'),
    path('bank-deposits/<int:pk>/', BankDepositRetrieveUpdateView.as_view(), name='bank-deposit-detail'),
    # path('bank-deposits/<int:pk>/confirm/', BankDepositConfirmView.as_view(), name='bank-deposit-confirm'),

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
    path('frames/transfer/', FrameTransferView.as_view(), name='frame-transfer'),
    path('lenses/transfer/', LensTransferView.as_view(), name='lens-transfer'),
    path('frames/<int:pk>/', FrameRetrieveUpdateDeleteView.as_view(), name='frame-detail'),
    path("frames/colors/", FrameColorListView.as_view(), name="frame-colors"),
    path("frames/stocks/adjust", StockAdjustmentView.as_view(), name="frame-stock-adjustment"),
    path("frames/filter", FrameFilterView.as_view(), name="frame-stock-filter"),
    path("report/frames/brand/", FrameBrandReportView.as_view(), name="frame-brand-report"),

    path('frames/report/', FrameReportView.as_view(), name='frames-report'), #frame reports

    path('powers/', PowerListCreateView.as_view(), name='power-list-create'),
    path('powers/<int:pk>/', PowerRetrieveUpdateDeleteView.as_view(), name='power-detail'),
    path('lenses/', LensListCreateView.as_view(), name='lens-list-create'),
    path('lenses/<int:pk>/', LensRetrieveUpdateDeleteView.as_view(), name='lens-detail'),
    path('lens-powers/', LensPowerListCreateView.as_view(), name='lens-power-list-create'),
    path('lens-powers/<int:pk>/', LensPowerRetrieveUpdateDeleteView.as_view(), name='lens-power-detail'),

    #external lenses
    path('external_lenses/', ExternalLensListCreateView.as_view(), name='external_lens_list_create'),
    path('external_lenses/<int:id>/', ExternalLensRetrieveUpdateDeleteView.as_view(), name='external_lens_detail'),

    path('external-lens-coatings/', ExternalLensCoatingListCreateView.as_view(), name='external-lens-coating-list-create'),
    path('external-lens-coatings/<int:id>/', ExternalLensCoatingRetrieveUpdateDeleteView.as_view(), name='external-lens-coating-detail'),

    # External Lens Brand CRUD
    path('external-lens-brands/', ExternalLensBrandListCreateView.as_view(), name='external-lens-brand-list-create'),
    path('external-lens-brands/<int:id>/', ExternalLensBrandRetrieveUpdateDeleteView.as_view(), name='external-lens-brand-detail'),

    path('lens-cleaners/', LensCleanerListCreateView.as_view(), name='lens-cleaner-list-create'),
    path('lens-cleaners/<int:pk>/', LensCleanerRetrieveUpdateDeleteView.as_view(), name='lens-cleaner-detail'),
    path('lens-cleaner-stocks/', LensCleanerStockListCreateView.as_view(), name='lens-cleaner-stock-list-create'),
    path('lens-cleaner-stocks/<int:pk>/', LensCleanerStockRetrieveUpdateDeleteView.as_view(), name='lens-cleaner-stock-detail'),
    path('other-items/', OtherItemListCreateView.as_view(), name='other-item-list-create'),
    path('other-items/<int:pk>/', OtherItemRetrieveUpdateDeleteView.as_view(), name='other-item-detail'),
    path('orders/', OrderCreateView.as_view(), name='order-create'),
    path('orders/<int:pk>/', OrderUpdateView.as_view(), name='order-update'),
    #feature fitting on collection
    path('orders/<int:pk>/update-fit-status/', OrderUpdateFitStatusView.as_view(), name='order-update-fit-status'),
    path('reports/fitting-status/', FittingStatusReportView.as_view(), name='fitting-status-report'),
    # path("manual-orders/", ManualOrderCreateView.as_view(), name="manual-order-create"),
    path('orders/update-payments/', PaymentView.as_view(), name='update-payments'),
    path('orders/payments/', PaymentView.as_view(), name='order-payments'),
    path('orders/<int:pk>/refund/', OrderRefundView.as_view(), name='order-refund'),
    #frame only
    path('orders/frame-only/', FrameOnlyOrderCreateView.as_view(), name='frame-only-order-create'),
    path('orders/frame-only/<int:pk>/update/', FrameOnlyOrderUpdateView.as_view(), name='frame-only-update'),
    path('orders/<int:order_id>/delete/', OrderSoftDeleteView.as_view(), name='order-soft-delete'),
    #Order audit 
    path("orders/status-report/", OrderDeleteRefundListView.as_view(), name="order-status-report"),
    #whatapp msg sent
    path('factory-invoice/external-lense/search/', FactoryInvoiceExternalLenseSearchView.as_view(), name='factory-invoice-external-lense-search'),
    path('factory-invoices/bulk-update-status/', BulkUpdateOrderProgressStatus.as_view(), 
     name='factory-invoice-bulk-status-update'),
    path('progress-status/list/', OrderProgressStatusListView.as_view(), 
     name='order-progress-status-list'),
    path('factory-invoices/bulk-update-whatsapp-sent/', BulkOrderWhatsAppLogView.as_view(), 
     name='factory-invoice-bulk-whatsapp-sent'),
    #invoice
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'), #invoice
    path('invoices/', InvoiceDetailView.as_view(), name='invoice-by-order'),  # Filter by order_id
    # path('factory-invoices/<int:pk>/update-status/', InvoiceProgressUpdateView.as_view(), name='factory-invoice-status-update'), (removed)
   
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
    path('patients/<int:pk>/', PatientUpdateView.as_view(), name='patient-update'),
    path('channel/', ChannelAppointmentView.as_view(), name='channel-appointment'),
    path('channels/', ChannelListView.as_view(), name='channel-list'),
    path('channels/time-slots/', DoctorAppointmentTimeListView.as_view(), name='doctor-appointment-time-list'),#time slots
    path('channels/<int:pk>/', AppointmentRetrieveUpdateDeleteView.as_view(), name='appointment-detail'),
    path("channel/transfer/", ChannelTransferView.as_view(), name="channel-transfer"),
    path('channels/<int:pk>/update/', ChannelUpdateView.as_view(), name='channel-update'),
    path('channel/<int:pk>/cancel/', CancelChannelView.as_view(), name='cancel-channel'), #soft delete
    path('channel/<int:pk>/refund/', RefundChannelView.as_view(), name='refund-channel'),
    path('channels/status/', AppointmentStatusListView.as_view(), name='channel-status-list'),#deleted refunded filter
    path('channels/fees/', DoctorBranchChannelFeesCreateView.as_view(), name='doctor-branch-channel-fees-create'),
    path('channels/fees/<int:pk>/update/', DoctorBranchChannelFeesUpdateView.as_view(), name='doctor-branch-channel-fees-list'),
    path('channels/fees/list/', DoctorBranchChannelFeesListView.as_view(), name='doctor-branch-channel-fees-list'),
    
    #channel repayment
    path('channel/repayments/', ChannelRepaymentView.as_view(), name='channel-repayments'),
    path('doctor/transfer-appointments/', DoctorAppointmentTransferView.as_view(), name='doctor-appointment-transfer'), #appointment trans
    path('branches/appointments/today-count/', BranchAppointmentCountView.as_view(), name='branch-appointments-today-count'),
    path('lens-stocks/', LensStockListCreateView.as_view(), name='lens-stock-list-create'),
    path('lens-stocks/<int:pk>/', LensStockRetrieveUpdateDeleteView.as_view(), name='lens-stock-detail'),
    path("lenses/search/", LensSearchView.as_view(), name="lens-search"),
    path('lens-types/', LensTypeListCreateView.as_view(), name='lens-type-list-create'),
    path('lens-types/<int:pk>/', LensTypeRetrieveUpdateDeleteView.as_view(), name='lens-type-detail'),
    path('lens-coatings/', LensCoatingListCreateView.as_view(), name='lens-coating-list-create'),
    path('lens-coatings/<int:pk>/', LensCoatingRetrieveUpdateDeleteView.as_view(), name='lens-coating-detail'),
    path('summary/daily/', DailySummaryView.as_view(), name='daily-summary'),

    #expenses
    path('expense-categories/', ExpenseMainCategoryListCreateView.as_view(), name='expense-main-category-list-create'),
    path('expense-categories/<int:pk>/', ExpenseMainCategoryRetrieveUpdateDestroyView.as_view(), name='expense-main-category-detail'),

    # Sub Category
    path('expense-subcategories/', ExpenseSubCategoryListCreateView.as_view(), name='expense-sub-category-list-create'),
    path('expense-subcategories/<int:pk>/', ExpenseSubCategoryRetrieveUpdateDestroyView.as_view(), name='expense-sub-category-detail'),
    path('expenses/', ExpenseCreateView.as_view(), name='expense-create'),
    path("expenses/report/", ExpenseReportView.as_view(), name="expense-report"),

    path('expenses/<int:pk>/update/', ExpenseUpdateView.as_view(), name='expense-update'),
    path('expenses/<int:pk>/', ExpenseRetrieveView.as_view(), name='expense-detail'),

    #bus
    path('bus/title/', BusSystemSettingListCreateView.as_view(), name='bus-system-title-list-create'),
    path('bus/title/<int:pk>/', BusSystemSettingRetrieveUpdateDeleteView.as_view(), name='bus-system-title-rud'),

    #doctor-claim
    path('doctor-claims-invoices/', DoctorClaimInvoiceListCreateView.as_view(), name='doctor-claim-invoice-list-create'),
    path('doctor-claims-invoices/<int:pk>/', DoctorClaimInvoiceRetrieveUpdateDestroyView.as_view(), name='doctor-claim-invoice-rud'),

    path('doctor-claims-channels/', DoctorClaimChannelListCreateView.as_view(), name='doctor-claim-channel-list-create'),
    path('doctor-claims-channels/<int:pk>/', DoctorClaimChannelRetrieveUpdateDestroyView.as_view(), name='doctor-claim-channel-rud'),

    #soldering
    path('soldering/orders/create/', CreateSolderingOrderView.as_view(), name='create-soldering-order'),
    path('soldering/orders/<int:pk>/update-progress/', SolderingOrderProgressUpdateView.as_view(), name='soldering-order-progress-update'),
    path('soldering/invoices/search/', SolderingInvoiceSearchView.as_view(), name='soldering-invoice-search'),
    path('soldering/orders/<int:pk>/edit/', SolderingOrderEditView.as_view(), name='soldering-order-edit'),
    path('invoices/search-by-number/', InvoiceNumberSearchView.as_view(), name='invoice-number-mini-search'),
    path('orders/mark-delivered/', OrderDeliveryMarkView.as_view(), name='order-mark-delivered'),
    #user order report 
    path('report/glass-sender-report/', GlassSenderReportView.as_view(), name='glass-sender-report'),
    # order audir hostory 
    path('orders/audit-history/', OrderAuditHistoryView.as_view(), name='order-audit-history'),
    path('report/mnt-order-report/', MntOrderReportView.as_view(), name='mnt-order-report'),
    path("arrival-status/bulk-create/", ArrivalStatusBulkCreateView.as_view(),name="arrival-status-bulk"),
    path("orders/audit-report/", DailyOrderAuditReportView.as_view(), name="daily-order-audit-report"),

    #store report
    path('report/frame-history/',FrameHistoryReportView.as_view(), name='report-frame-history'),
    path('report/lens-history/',LensHistoryReportView.as_view(), name='report-lens-history'),
    #sale report
    path('report/frame-sale/',FrameSaleReportView.as_view(), name='report-frame-sale'),
    path('report/lens-sale/',LensSaleReportView.as_view(), name='report-lens-sale'),
    #reports
    path('reports/factory-orders/', FactoryOrderReportView.as_view(), name='factory-order-report'),
    path('reports/normal-orders/', NormalOrderReportView.as_view(), name='normal-order-report'),
    path('reports/channel-orders/', ChannelOrderReportView.as_view(), name='channel-order-report'),
    path('reports/soldering-orders/', SolderingOrderReportView.as_view(), name='soldering-order-report'),
    path('reports/best-customers/', BestCustomersReportView.as_view(), name='best-customers-report'),
    path('reports/employee-history/', EmployeeHistoryReportView.as_view(), name='employee-history-report'),
    path('reports/payment-method/', PaymentSummaryReportView.as_view(), name='payment-summary-report'),
    path('banking-report/', BankingReportView.as_view(), name='banking-report'),
    # 2. Banking confirm action endpoint
    path('banking-report/confirm/<int:deposit_id>/', ConfirmDepositView.as_view(), name='confirm-deposit'),
    path('reports/customer-location-statistics/', CustomerLocationStatisticsView.as_view(), name='customer-location-statistics-report'),
    path('reports/customer-location-table/', CustomerLocationTableView.as_view(), name='customer-location-table-report'),
    path('orders/<int:order_id>/images/', OrderImageListCreateView.as_view(), name='order-image-list-create'),
    path('orders/<int:order_id>/images/<int:pk>', OrderImageDetailView.as_view(), name='order-image-detail'),
    path('orders/<int:order_id>/images/<int:pk>/', OrderImageDetailView.as_view(), name='order-image-detail-slash'),
    path('order-feedback/by-invoice/', OrderFeedbackByInvoiceView.as_view(), name='order-feedback-by-invoice'),
    path('order-feedback/', OrderFeedbackCreateView.as_view(), name='order-feedback-create'),
    
    ]
    # path('api-token-auth/', CustomAuthToken.as_view(), name='api-token-auth'),