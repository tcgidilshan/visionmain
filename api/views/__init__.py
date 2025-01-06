from .branch_views import BranchListCreateAPIView, BranchRetrieveUpdateDestroyAPIView
from .auth_views import LoginView, AdminOnlyView, SuperAdminOnlyView, UserRegistrationView, AdminRegistrationView, IsAdminOrSuperAdmin, IsSuperAdmin, AdminRegistrationView
from .refraction_views import RefractionCreateAPIView, RefractionListAPIView, RefractionUpdateAPIView, RefractionDeleteAPIView
from .refraction_detail_views import RefractionDetailCreateAPIView
from .brand_views import BrandListCreateView,BrandRetrieveUpdateDeleteView
from .color_views import ColorListCreateView,ColorRetrieveUpdateDeleteView
from .code_views import CodeListCreateView,CodeRetrieveUpdateDeleteView
from .frames_stock_views import FrameStockListCreateView,FrameStockRetrieveUpdateDeleteView
from .frame_views import FrameListCreateView,FrameRetrieveUpdateDeleteView
from .power_views import PowerListCreateView,PowerRetrieveUpdateDeleteView
from .lens_views import LensListCreateView,LensRetrieveUpdateDeleteView
from .lens_power_views import LensPowerListCreateView,LensPowerRetrieveUpdateDeleteView
from .lens_cleaner_views import LensCleanerListCreateView,LensCleanerRetrieveUpdateDeleteView
from .lens_cleaner_stock_views import LensCleanerStockListCreateView,LensCleanerStockRetrieveUpdateDeleteView
from .order_views import OrderCreateView
from .doctor_views import  DoctorListCreateView,DoctorRetrieveUpdateDeleteView
from .patient_views import PatientListView
from .channel_views import ChannelAppointmentView,ChannelListView