import re
from django.db import connections
from django.http import HttpRequest

class SwitchDatabaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Récupérer le chemin de l'URL de la demande
        path = request.path

        # Déterminer quelle base de données utiliser en fonction de l'endpoint demandé
        # if path in ['/api/createdemande/','/api/types-documents/', '/auth/register/','/auth/me/','/auth/token/refresh/','/auth/allUsers/','/api/archives/credits/','/auth/update-password/' ,'/auth/me/update/','/auth/forget_password/','/api/createdemande/','/api/credits/','/auth/reset_password/<str:token>'] or path.startswith('/admin/')  path.startswith('/documents/') or path.startswith('/credits/') or path.startswith('/stats/') or path.startswith('/notifications/'):
        if path in ['/api/createdemande/','/api/types-documents/','/api/credits/'] or path.startswith('/admin/')  or path.startswith('/credits/') or path.startswith('/stats/') or path.startswith('/notifications/'):    
            # Utiliser la base de données SQLite par défaut pour les endpoints login/ et register/
            using_db = 'sqlite'
        if path in ['/api/comptes-particulier/','/api/comptes-entreprise/', '/auth/register/','/auth/me/','/auth/token/refresh/','/auth/allUsers/','/api/archives/credits/','/auth/update-password/' ,'/auth/me/update/','/auth/forget_password/','/api/createdemande/','/api/credits/','/auth/reset_password/<str:token>',]:    
            using_db = 'PROD'    
        else:
            # Utiliser la base de données Oracle par défaut pour les autres endpoints
            using_db = 'oracle'

        # Modifier la base de données par défaut en fonction de la configuration
        connections['default'].close()  # Fermer la connexion existante
        connections['default'] = connections[using_db]  # Modifier la base de données par défaut
        connections['default'].ensure_connection()  # Réouvrir la connexion

        return self.get_response(request)       
    


# import re
# from django.conf import settings
# from django.db import connections
# from django.http import HttpRequest


# class SwitchDatabaseMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request: HttpRequest):
#         path = request.path

#         # Choisir la DB par défaut
#         using_db = "oracle"

#         # Routes qui utilisent SQLite
#         sqlite_routes = [
#             "/api/createdemande/",
#             "/api/types-documents/",
#             "/api/credits/",
#         ]

#         # Routes qui utilisent PROD
#         prod_routes = [
#             "/api/comptes-particulier/",
#             "/api/comptes-entreprise/",
#             "/auth/register/",
#             "/auth/me/",
#             "/auth/token/refresh/",
#             "/auth/allUsers/",
#             "/api/archives/credits/",
#             "/auth/update-password/",
#             "/auth/me/update/",
#             "/auth/forget_password/",
#             "/auth/reset_password/",
#         ]

#         # Condition SQLite
#         if path in sqlite_routes or path.startswith(("/admin/", "/credits/", "/stats/", "/notifications/")):
#             using_db = "sqlite"

#         # Condition PROD
#         elif any(path.startswith(route.rstrip("/")) for route in prod_routes):
#             using_db = "PROD"

#         # Basculer la DB par défaut
#         try:
#             connections["default"].close()
#             settings.DATABASES["default"] = settings.DATABASES[using_db]
#             connections["default"].ensure_connection()
#         except Exception as e:
#             print(f"[SwitchDatabaseMiddleware] Erreur changement DB vers {using_db} : {e}")

#         return self.get_response(request)
 