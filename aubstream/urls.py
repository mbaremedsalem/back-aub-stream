from django.urls import path
from .views import *
from .viewsTransfer import *
from .viewsAmortissement import *
from .viewsAvis import *
from .viewsCredit import *
from .viewsObjectif import *

urlpatterns = [
    path('users/', UserListAPIView.as_view(), name='user-list'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('reset-password/', PasswordResetAPIView.as_view(), name='password-reset'),
    path('me/', UserAppPlafondsAPIView.as_view(), name='password-reset'),
    
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

    ###### droit consulte ##########
    path('update-consulte/', UpdateConsulteAPI.as_view(), name='update-consulte'),

    ############## transfere  ########
    # Beneficiaires
    path('beneficiaires/',list_beneficiaires, name='beneficiaire-list'),
    
    # Banques
    path('banques/',list_banques, name='banque-list'),
    path('banques/<str:type_banque>/', list_banques, name='banque-by-type'),
    
    # comptes local
    path('comptes/',list_compte, name='comptes-list'),

    
    # Transfers
    path('transfers/',list_transfers, name='transfer-list'),
    path('transfers/create/',create_transfer, name='transfer-create'),
    # path('transfers/<int:pk>/',transfer_detail, name='transfer-detail'),
    
    path('transfers/<int:transfer_id>/', get_transfer_by_id, name='transfer-details'),

    path('transfers/<int:transfer_id>/file/', get_transfer_file, name='get-transfer-file'),
    path('transfers/<int:transfer_id>/approve/', approve_transfer, name='approve-transfer'),
    path('transfers/<int:transfer_id>/rejete/', reject_transfer, name='approve-transfer'),

    path('historique/', get_all_historique, name='get-all-historique'),
    path('transfers/<int:transfer_id>/historique/', get_historique_by_transfer, name='get-historique-by-transfer'),
    path('transfers/<int:transfer_id>/update/', update_transfer, name='update-transfer'),
    path('transfer-stats/', TransferStatsAPI.as_view(), name='transfer-stats'),
    path('transfer-stats-evaluation/', TransferStatisticsView.as_view(), name='transfer-stats-evaluation'),

    path('transfer/stats/', get_transfer_stats, name='transfer-stats'),
    path('transfer/stats/detailed/', get_detailed_transfer_stats, name='transfer-stats-detailed'),
    path('transfer/stats/timeline/', get_transfer_timeline_stats, name='transfer-timeline-stats'),

    ### configure #########
    ### ---- get client ---- ###
    path('client-physique/', ClientPhysiqueView.as_view(), name='client-physique'),
    path('client-moral/', ClientMoralView.as_view(), name='client-moral'),

    ### ---- get client ---- ###
    path('get-pret-cli-compte/', PrtcliDossiersAPIView.as_view(), name='client-physique'),
    path('get-entet-cli/', entetPostView.as_view(), name='get_entet_cli'),
    path('get-amotissement-by-nooper/', PrtcamoNOOPERliView.as_view(), name='get-amortissement-bynooper'),

  

    ##### ---- avis ------ #######
    path('search-guichet/', search_guichet_files, name='search_guichet_files'),
    path('search-virement-intern/', search_virement_intern_files, name='search_virement_intern_files'),
    path('search-virement-extern/', search_virement_extern_files, name='search_virement_extern_files'),
    path('search-transfer/', search_transfer_files, name='search_transfer_files'),


    #### ----- credit ---- #####

    # get clients 
    path('comptes-particulier/', CompteClientView.as_view(), name='compte-list'),
    path('comptes-entreprise/', CompteProfessionnelView.as_view(), name='compte-list'),

    #### ------ create demande ---------  # creation credit 
    path('createdemande/', CreateDemandeAPIView.as_view(), name='create-demande'),

    # update credit 
    path('credits/<int:credit_id>/update/', UpdateDemandeAPIView.as_view(), name='update-demande'),
    path('credits/', CreditListAPIView.as_view(), name='credit-list'),
    path('credits/<int:credit_id>/', CreditDetailAPIView.as_view(), name='credit-detail'),


    # delete document
    path('documents/<int:pk>/delete/', DocumentDeleteAPIView.as_view(), name='document-delete'),
    #----- type docuemnt 
    path('types-documents/', TypeUploadFileListAPIView.as_view(), name='types-documents'),


    path('credits/<int:credit_id>/historiques-complet/', CreditHistoriqueCompletAPIView.as_view(), name='credit-historique-complet'),
    #### ------ remonter credit ---------
    path('credits/<int:credit_id>/remonter/', RemonterCreditAPIView.as_view(), name='remonter-credit'),
    #### ------ remonter credit ---------
    path('credits/<int:credit_id>/rejeter/', RejeterCreditAPIView.as_view(), name='rejeter-credit'),
    

    #notification
    path('notifications/', UserNotificationListView.as_view(), name='user-notifications'),
    path('notifications/<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/mark-all-as-read/', MarkAllNotificationsAsRead.as_view(), name='mark-all-notifications-read'),

    
    # path("stats-par-agence/", CreditStatsViewParAgence.as_view(), name="credit-stats"),
    path("stats/", CreditStatsView.as_view(), name="credit-stats"),
    path("stats/validateurs-premiers/", ValidationEfficiencyAPIView.as_view(), name="validateurs-premiers"),    
    path('ncg-lib/', NcgLibView.as_view(), name='ncg-lib'),


    ###### ------- objectif -------######"
    path('objectives/list/', get_objectives_list, name='get_objectives_list'),
    path('objectives/assign/', assign_objectives, name='assign_objectives'),
    ##### ----- periode ----- #######
    path('periods/create/', create_period, name='create_period'),
    path('periods/list/', get_periods, name='get_periods'),
    path('periods/check/<str:period_id>/', check_period_exists, name='check_period_exists'),
    path('periods/create-bulk/', create_periods_bulk, name='create_periods_bulk'),
    ####----- tache -------######
    path('task-types/create/', create_task_type, name='create_task_type'),
    path('task-types/list/', get_task_types, name='get_task_types'),
    path('api/task-types/create-bulk/', create_task_types_bulk, name='create_task_types_bulk'),

    #####----- APIs de suppression -------- ########
    # APIs TRUNCATE individuelles
    path('truncate/periods/', truncate_periods, name='truncate_periods'),
    path('truncate/task-types/', truncate_task_types, name='truncate_task_types'),
    path('truncate/user-objectives/', truncate_user_objectives, name='truncate_user_objectives'),
    path('truncate/monthly-objectives/', truncate_monthly_objectives, name='truncate_monthly_objectives'),
    path('monthly-objectives/', get_monthly_objectives, name='get_monthly_objectives'),


    
]

