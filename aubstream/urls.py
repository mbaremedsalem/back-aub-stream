from django.urls import path
from .views import *

urlpatterns = [
    path('users/', UserListAPIView.as_view(), name='user-list'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('reset-password/', PasswordResetAPIView.as_view(), name='password-reset'),
    
    ###### integration salaire ##########
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('archives/', ArchiveListAPIView.as_view(), name='archive-list'),
    path('integrer-salaire/', ExecuteCommandView.as_view(), name='execute_command'),

    path('archive-status/', ArchiveStatusListCreateView.as_view(), name='archive-status-list'),
    path('archive-status/<int:pk>/', ArchiveStatusRetrieveUpdateView.as_view(), name='archive-status-detail'),

    ###### droit ##########
    path('application-list/', ApplicationListAPIView.as_view(), name='application-list'),
    path('assign-applications/', AssignApplicationsAPIView.as_view(), name='assign-applications'),
    path('user-applications/<str:username>/', UserApplicationsListAPIView.as_view(), name='user-applications-list'),
    path('reject-archive/', RejectArchiveAPIView.as_view(), name='reject-archive'),
    path('remove-applications/', RemoveApplicationAPIView.as_view(), name='remove-applications'),
]

