from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny, IsAuthenticated
import base64
import hashlib
import os
from datetime import datetime
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
import csv
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
import paramiko
from django.db import connection
from django.utils import timezone
from django.db import transaction

def verify_ssha_password(password, ssha_hash):
    try:
        # Remove the {SSHA} prefix
        if ssha_hash.startswith('{SSHA}'):
            ssha_hash = ssha_hash[6:]
        
        # Decode base64
        decoded = base64.b64decode(ssha_hash)
        
        # Extract the hash and salt
        hash_value = decoded[:20]  # SHA1 hash is 20 bytes
        salt = decoded[20:]        # Rest is the salt
        
        # Create new hash with provided password and extracted salt
        sha1 = hashlib.sha1()
        sha1.update(password.encode('utf-8'))
        sha1.update(salt)
        calculated_hash = sha1.digest()
        
        # Compare the hashes
        return calculated_hash == hash_value
    except Exception as e:
        print(f"Password verification error: {str(e)}")
        return False

def create_ssha_password(password):
    # Generate a random salt (8 bytes)
    salt = os.urandom(8)
    
    # Create SHA1 hash of password + salt
    sha1 = hashlib.sha1()
    sha1.update(password.encode('utf-8'))
    sha1.update(salt)
    hash_value = sha1.digest()
    
    # Combine hash and salt
    hash_plus_salt = hash_value + salt
    
    # Base64 encode and add {SSHA} prefix
    encoded = base64.b64encode(hash_plus_salt).decode('utf-8')
    return f"{{SSHA}}{encoded}"

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    # Add custom claims
    refresh['username'] = user.username
    refresh['fullname'] = user.fullname
    refresh['usercode'] = user.usercode
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class UserListAPIView(APIView):
    """
    API View to list all users with pagination
    """
    
    def get(self, request, format=None):
        # Get query parameters
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        username_filter = request.query_params.get('username', None)
        
        # Build queryset
        queryset = AmUsers.objects.all().order_by('username')
        
        # Optional filtering
        if username_filter:
            queryset = queryset.filter(username__icontains=username_filter)
        
        # Manual pagination
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # Serialization
        serializer = AmUsersSerializer(page_obj, many=True)
        
        # Build response
        response_data = {
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'results': serializer.data,
            'next': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous': page_obj.previous_page_number() if page_obj.has_previous() else None
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

class UserLoginAPIView(APIView):
    """
    API View for user login
    """
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        serializer = UserLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            username = serializer.validated_data['username']
            provided_password = serializer.validated_data['password']
            
            try:
                user = AmUsers.objects.get(username=username)
                stored_password = user.password
                
                # Case 1: User provides the exact SSHA hash
                if provided_password == stored_password:
                    is_valid = True
                # Case 2: User provides plain password
                else:
                    is_valid = verify_ssha_password(provided_password, stored_password)
                
                if is_valid:
                    # Update last login date
                    user.unsuccessful_login_number = 0
                    user.last_login_date = datetime.now()
                    user.save()
                    
                    # Generate tokens
                    tokens = get_tokens_for_user(user)
                    
                    # Return user data and tokens
                    user_data = AmUsersSerializer(user).data
                    
                    # Récupérer les plafonds de l'utilisateur
                    plafonds = UserAppPlafonds.objects.filter(
                        user_id=user.id, 
                        statut='ACTIF'
                    )
                    plafonds_data = UserAppPlafondsSerializer(plafonds, many=True).data
                    
                    return Response({
                        'message': 'Login successful',
                        'user': user_data,
                        'tokens': tokens,
                        'plafonds': plafonds_data  # Ajout des plafonds
                    }, status=status.HTTP_200_OK)
                else:
                    # Increment unsuccessful login attempts
                    user.unsuccessful_login_number += 1
                    user.save()
                    return Response({
                        'message': 'Invalid credentials'
                    }, status=status.HTTP_401_UNAUTHORIZED)
                    
            except AmUsers.DoesNotExist:
                return Response({
                    'message': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class UserLoginAPIView(APIView):
#     """
#     API View for user login
#     """
#     permission_classes = [AllowAny]

#     def post(self, request, format=None):
#         serializer = UserLoginSerializer(data=request.data)
        
#         if serializer.is_valid():
#             username = serializer.validated_data['username']
#             provided_password = serializer.validated_data['password']
            
#             try:
#                 user = AmUsers.objects.get(username=username)
#                 stored_password = user.password
                
#                 # Case 1: User provides the exact SSHA hash
#                 if provided_password == stored_password:
#                     is_valid = True
#                 # Case 2: User provides plain password
#                 else:
#                     is_valid = verify_ssha_password(provided_password, stored_password)
                
#                 if is_valid:
#                     # Update last login date
#                     user.unsuccessful_login_number = 0
#                     user.last_login_date = datetime.now()
#                     user.save()
                    
#                     # Generate tokens
#                     tokens = get_tokens_for_user(user)
                    
#                     # Return user data and tokens
#                     user_data = AmUsersSerializer(user).data
                    
#                     return Response({
#                         'message': 'Login successful',
#                         'user': user_data,
#                         'tokens': tokens
#                     }, status=status.HTTP_200_OK)
#                 else:
#                     # Increment unsuccessful login attempts
#                     user.unsuccessful_login_number += 1
#                     user.save()
#                     return Response({
#                         'message': 'Invalid credentials'
#                     }, status=status.HTTP_401_UNAUTHORIZED)
                    
#             except AmUsers.DoesNotExist:
#                 return Response({
#                     'message': 'Invalid credentials'
#                 }, status=status.HTTP_401_UNAUTHORIZED)
        
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

class UserAppPlafondsAPIView(APIView):
    """
    API pour récupérer les plafonds de l'utilisateur connecté par application
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            # L'utilisateur est authentifié via le token JWT
            user = request.user
            
            # Récupérer tous les plafonds actifs de l'utilisateur
            plafonds = UserAppPlafonds.objects.filter(
                user_id=user.id, 
                statut='ACTIF'
            ).select_related('app_id')  # Optimisation pour joindre la table application
            
            # Sérialiser les données
            serializer = UserAppPlafondsSerializer(plafonds, many=True)
            
            return Response({
                'success': True,
                'user_id': user.id,
                'username': user.username,
                'plafonds': serializer.data,
                'count': plafonds.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Erreur lors de la récupération des plafonds'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PasswordResetAPIView(APIView):
    """
    API View for password reset
    """
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            username = serializer.validated_data['username']
            new_password = serializer.validated_data['new_password']
            
            try:
                user = AmUsers.objects.get(username=username)
                
                # Create new SSHA hash for the new password
                new_ssha_hash = create_ssha_password(new_password)
                
                # Update user password and related fields
                user.password = new_ssha_hash
                user.last_password_change_date = datetime.now()
                user.unsuccessful_login_number = 0
                user.save()
                
                # Generate tokens for automatic login after reset
                tokens = get_tokens_for_user(user)
                
                # Return success response with new hash and tokens
                return Response({
                    'message': 'Password reset successful',
                    'username': username,
                    'new_password_hash': new_ssha_hash,
                    'tokens': tokens
                }, status=status.HTTP_200_OK)
                    
            except AmUsers.DoesNotExist:
                return Response({
                    'message': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


############ integration de salaire ###############
@method_decorator(csrf_exempt, name='dispatch')
class FileUploadView(View):
    def _archive_previous_data(self):
        """
        Moves data from Archive and Archive_Status to history tables if they contain data.
        This assumes 'Historique_Archive' and 'Historique_Archive_Status' tables exist
        with the same structure as the original ones.
        """
        if not Archive.objects.exists():
            return  # Nothing to do

        with transaction.atomic():
            with connection.cursor() as cursor:
                # 1. Copy data to history tables
                # Note: This assumes columns are in the same order.
                # It's safer to list columns explicitly if you can.
                cursor.execute("INSERT INTO Historique_Archive SELECT * FROM Archive")
                cursor.execute("INSERT INTO Historique_Archive_Status SELECT * FROM Archive_Status")

                # 2. Delete from original tables (delete from child table first)
                cursor.execute("DELETE FROM Archive_Status")
                cursor.execute("DELETE FROM Archive")

    def post(self, request):
        # --- Etape d'archivage ajoutée ---
        try:
            self._archive_previous_data()
        except Exception as e:
            # If archiving fails, stop the process and return an error
            return JsonResponse({'message': 'Erreur lors de l''archivage des anciennes données', 'error': str(e)}, status=500)
        # --- Fin de l'étape d'archivage ---

        # Vérifier si le fichier est dans la requête
        if 'file' not in request.FILES:
            return JsonResponse({'message': 'No file part'}, status=400)

        file = request.FILES['file']

        # Vérifier si le fichier est un fichier CSV
        file_extension = os.path.splitext(file.name)[1]
        if file_extension != '.csv':
            return JsonResponse({'message': 'Only CSV files are allowed'}, status=400)

        # Sauvegarder le fichier temporairement
        fs = FileSystemStorage(location=settings.MEDIA_ROOT)
        filename = fs.save(file.name, file)
        file_path = os.path.join(settings.MEDIA_ROOT, filename)

        # Lire et sauvegarder les données dans le modèle après le transfert
        try:
            # Transférer le fichier via SFTP
            success = transfer_file_to_remote(file_path, filename)

            if success:
                # Lire le fichier CSV et sauvegarder les données
                self.save_csv_data_to_model(file_path)
                return JsonResponse({'message': 'File successfully uploaded, transferred, and data saved'}, status=200)
            else:
                return JsonResponse({'message': 'File transfer failed'}, status=500)

            def check_and_move_existing_files(self):
                # Créer une instance de CheckAndMoveFilesView et appeler la méthode POST
                move_view = CheckAndMoveFilesView()
                request = None  # Vous pouvez simuler une requête si nécessaire, ici on passe None
                response = move_view.post(request)

                # Vérifier la réponse
                if response.status_code == 200:
                    return True
                else:
                    return False
        except UnicodeDecodeError as e:
            return JsonResponse({'message': f'File encoding error: {e}'}, status=500)
        except Exception as e:
            return JsonResponse({'message': f'Error processing file: {e}'}, status=500)
        finally:
            # Supprimer le fichier temporaire
            if os.path.exists(file_path):
                os.remove(file_path)

    def save_csv_data_to_model(self, file_path):
        """
        Lire le fichier CSV et enregistrer les données dans le modèle FileData.
        """
        with open(file_path, encoding='windows-1252') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Enregistrer chaque ligne dans le modèle FileData
                Archive.objects.create(
                    doc_type=row.get('DOC_TYPE', '').strip(),
                    doc_id=row.get('DOC_ID', '').strip(),
                    doc_date=row.get('DOC_DATE', '').strip() or None,  # Convertir en None si vide
                    debtor_account=row.get('DEBTOR_ACCOUNT', '').strip(),
                    c_branch=row.get('C_BRANCH', '').strip(),
                    creditor_account=row.get('CREDITOR_ACCOUNT', '').strip(),
                    c_name=row.get('C_NAME', '').strip(),
                    type_dc=row.get('TYPE_DC', '').strip(),
                    summa=row.get('SUMMA', '0').strip() or None,  # Valeur par défaut 0 pour les nombres
                    kod=row.get('KOD', '').strip(),
                    beneficiary_bic=row.get('Beneficiary Bic', '').strip(),
                    description=row.get('Description', '').strip(),
                    posted = True
                )



def transfer_file_to_remote(local_path, remote_filename):
    try:
        # Initialiser le client SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Se connecter au serveur distant
        ssh.connect(SERVER_NAME, username=SERVER_USER, password=SERVER_PASSWORD)

        # Utiliser SFTP pour accéder aux fichiers à distance
        sftp = ssh.open_sftp()

        # Transférer le fichier en mode binaire
        with open(local_path, 'rb') as file:
            # Transférer vers le premier répertoire
            sftp.putfo(file, f'/export/home2/aubpre/home/{remote_filename}')
            # Réinitialiser le curseur à 0 avant de transférer à nouveau
            file.seek(0)
            # Transférer vers le deuxième répertoire
            sftp.putfo(file, f'/export/home2/aubpre/exfiles/{remote_filename}')

        # Fermer les connexions SFTP et SSH
        sftp.close()
        ssh.close()

        print(f"File {remote_filename} transferred successfully!")
        return True
    except Exception as e:
        print(f"Failed to transfer file: {e}")
        return False


#deplacer le fichier 
@method_decorator(csrf_exempt, name='dispatch')
class CheckAndMoveFilesView(View):
    def post(self, request):
        # Définir les répertoires distants
        directories = ['/export/home2/aubpre/exfiles/','/export/home2/aubpre/home/']
        oldfile_dir = '/export/home2/aubpre/oldfile/'
        files_moved = []

        try:
            # Connexion au serveur distant via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SERVER_NAME, username=SERVER_USER, password=SERVER_PASSWORD)

            sftp = ssh.open_sftp()

            # Vérification des fichiers dans chaque répertoire
            for directory in directories:
                try:
                    # Liste des fichiers dans le répertoire
                    file_list = sftp.listdir(directory)
                except UnicodeDecodeError:
                    # Erreur d'encodage, essayer de lister avec une autre méthode
                    return JsonResponse({'error': f"Erreur d'encodage lors de la vérification des fichiers dans {directory}."}, status=500)

                print(f"Files in {directory}: {file_list}")  # Pour le débogage

                for filename in file_list:
                    if filename.startswith('salary'):
                        # Construire les chemins de manière sécurisée
                        src_path = os.path.join(directory, filename)  # Chemin source
                        dest_path = os.path.join(oldfile_dir, filename)  # Chemin de destination

                        # Déplacer le fichier vers le répertoire 'oldfile'
                        try:
                            sftp.rename(src_path, dest_path)
                            files_moved.append(filename)
                        except Exception as move_error:
                            print(f"Erreur lors du déplacement de {filename}: {str(move_error)}")  # Pour le débogage

            # Fermeture de la connexion SFTP et SSH
            sftp.close()
            ssh.close()

            # Retourner un message en fonction des fichiers déplacés
            if files_moved:
                return JsonResponse({
                    'message': f"Les fichiers suivants ont été déplacés : {', '.join(files_moved)}"
                }, status=200)
            else:
                return JsonResponse({
                    'message': "Aucun fichier commençant par 'salary' n'a été trouvé."
                }, status=200)

        except Exception as e:
            # En cas d'erreur, renvoyer un message d'erreur
            return JsonResponse({'error': f"Erreur lors de la vérification et du déplacement des fichiers: {str(e)}"}, status=500)



class ExecuteCommandView(APIView):
    def post(self, request):
        # Informations de connexion
        hostname = SERVER_NAME  # Adresse IP de votre serveur
        username = SERVER_USER          # Nom d'utilisateur
        password = SERVER_PASSWORD     # Mot de passe

        # Commandes à exécuter
        commands = [
            'cd /export/home2/aubpre/home && bash -l -c "/export/home1/cgb/util/sh/dobatch virpain.sh"'
        ]

        try:
            # Création d'une instance SSHClient
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connexion au serveur
            client.connect(hostname, username=username, password=password)

            # Exécution des commandes
            output_data = {}
            for command in commands:
                stdin, stdout, stderr = client.exec_command(command)
                output = stdout.read().decode().strip()  # Lire la sortie standard
                error = stderr.read().decode().strip()   # Lire la sortie d'erreur

                output_data[command] = {
                    'output': output,
                    'error': error
                }

            # Fermer la connexion
            client.close()

            # Vérification si les commandes ont réussi
            if all(not cmd['error'] for cmd in output_data.values()):
                # Mettre à jour les objets FileData
                Archive.objects.filter(posted=True).update(posted=False)
                # MERGE Oracle pour insérer ou mettre à jour les statuts
                with connection.cursor() as cursor:
                    cursor.execute("""
                        MERGE INTO Archive_Status s
                        USING (
                            SELECT 
                                id AS archive_id,
                                CASE WHEN POSTED = 0 THEN 'confirmed' ELSE 'rejected' END AS status,
                                CASE WHEN POSTED = 0 THEN NULL ELSE 'Motif de rejet à préciser' END AS motif
                            FROM Archive
                        ) a
                        ON (s.archive_id = a.archive_id)
                        WHEN MATCHED THEN
                            UPDATE SET s.status = a.status, s.motif = a.motif
                        WHEN NOT MATCHED THEN
                            INSERT (archive_id, status, motif) VALUES (a.archive_id, a.status, a.motif)
                    """)
                return JsonResponse({'message': 'Salaires intégrés avec succès', 'data': output_data}, status=200)
            else:
                return JsonResponse({'message': 'Erreur', 'data': output_data}, status=400)

        except Exception as e:
            return JsonResponse({'message': 'Erreur', 'error': str(e)}, status=500)


class ArchiveListAPIView(APIView):
    """
    API View to list all archives with posted=True
    """
    # permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        archives = Archive.objects.filter().order_by('-created_at')
        serializer = ArchiveSerializer(archives, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ApplicationListAPIView(APIView):
    """
    API View to list all application with optional title search
    """
    # permission_classes = [IsAuthenticated]
    # permission_classes = [AllowAny]
    def get(self, request, format=None):
        title_filter = request.query_params.get('title', None)
        if title_filter:
            applications = Application.objects.filter(title__icontains=title_filter)
        else:
            applications = Application.objects.all()
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AssignApplicationsAPIView(APIView):
    """
    API View to assign one or more applications to a user
    """
    def post(self, request, format=None):
        serializer = AssignApplicationsSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            application_ids = serializer.validated_data['application_ids']
            try:
                # On suppose que la clé primaire de AM_USERS_LOCAL est id (numérique)
                # On récupère l'id numérique à partir du username
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id FROM AM_USERS_LOCAL WHERE username = :username", {'username': username})
                    row = cursor.fetchone()
                    if not row:
                        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
                    user_id = row[0]
            except Exception:
                return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            created = []
            for app_id in application_ids:
                with connection.cursor() as cursor:
                    # Vérifier que l'application existe
                    cursor.execute("SELECT COUNT(*) FROM Application WHERE id = :app_id", {'app_id': app_id})
                    app_exists = cursor.fetchone()[0]
                    if not app_exists:
                        continue
                    cursor.execute(
                        "SELECT COUNT(*) FROM User_Applications WHERE user_id = :user_id AND application_id = :app_id",
                        {'user_id': user_id, 'app_id': app_id}
                    )
                    exists = cursor.fetchone()[0]
                    if not exists:
                        cursor.execute(
                            "INSERT INTO User_Applications (user_id, application_id) VALUES (:user_id, :app_id)",
                            {'user_id': user_id, 'app_id': app_id}
                        )
                        created.append(app_id)
            return Response({'message': 'Applications assigned', 'assigned_ids': created}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserApplicationsListAPIView(APIView):
    """
    API View to list all applications assigned to a user, with optional title search
    """
    def get(self, request, username, format=None):
        title_filter = request.query_params.get('title', None)
        # Récupérer l'id numérique de l'utilisateur
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM AM_USERS_LOCAL WHERE username = :username", {'username': username})
            row = cursor.fetchone()
            if not row:
                return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            user_id = row[0]
            # Préparer la requête SQL avec ou sans filtre sur le titre
            base_query = """
                SELECT a.id, a.title, a.description, a.date_creation, a.date_update, a.version
                FROM Application a
                JOIN User_Applications ua ON a.id = ua.application_id
                WHERE ua.user_id = :user_id
            """
            params = {'user_id': user_id}
            if title_filter:
                base_query += " AND LOWER(a.title) LIKE :title"
                params['title'] = f"%{title_filter.lower()}%"
            cursor.execute(base_query, params)
            columns = [col[0].lower() for col in cursor.description]
            applications = []
            for row in cursor.fetchall():
                app = {}
                for col, value in zip(columns, row):
                    if hasattr(value, 'read'):
                        value = value.read()
                    if value is not None and not isinstance(value, (str, int, float, bool)):
                        value = str(value)
                    app[col] = value
                applications.append(app)
        return Response(applications, status=status.HTTP_200_OK)

        

from rest_framework import generics
from .models import ArchiveStatus
from .serializers import ArchiveStatusSerializer

class ArchiveStatusListCreateView(generics.ListCreateAPIView):
    queryset = ArchiveStatus.objects.all()
    serializer_class = ArchiveStatusSerializer

class ArchiveStatusRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = ArchiveStatus.objects.all()
    serializer_class = ArchiveStatusSerializer

class RejectArchiveSerializer(serializers.Serializer):
    archive_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    motif = serializers.CharField()

class RejectArchiveAPIView(APIView):
    def post(self, request):
        serializer = RejectArchiveSerializer(data=request.data)
        if serializer.is_valid():
            archive_ids = serializer.validated_data['archive_ids']
            motif = serializer.validated_data['motif']
            from django.utils import timezone
            updated = []
            errors = []
            for archive_id in archive_ids:
                try:
                    obj, created = ArchiveStatus.objects.update_or_create(
                        archive_id=archive_id,
                        defaults={
                            'status': 'rejected',
                            'motif': motif,
                            'updated_at': timezone.now()
                        }
                    )
                    updated.append(archive_id)
                except Exception as e:
                    errors.append({'archive_id': archive_id, 'error': str(e)})
            return Response({
                'message': 'Archives rejetées',
                'rejected': updated,
                'errors': errors
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)        

class RemoveApplicationAPIView(APIView):
    """
    API View to remove one or more applications from a user
    """
    def post(self, request, format=None):
        serializer = RemoveApplicationSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            application_ids = serializer.validated_data['application_ids']

            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id FROM AM_USERS_LOCAL WHERE username = :username", {'username': username})
                    row = cursor.fetchone()
                    if not row:
                        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
                    user_id = row[0]
            except Exception as e:
                return Response({'message': f'Error finding user: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            deleted_count = 0
            errors = []

            with connection.cursor() as cursor:
                for app_id in application_ids:
                    try:
                        cursor.execute(
                            "DELETE FROM User_Applications WHERE user_id = :user_id AND application_id = :app_id",
                            {'user_id': user_id, 'app_id': app_id}
                        )
                        if cursor.rowcount > 0:
                            deleted_count += cursor.rowcount
                    except Exception as e:
                        errors.append({'application_id': app_id, 'error': str(e)})

            return Response({
                'message': 'Application assignments removed.',
                'removed_count': deleted_count,
                'errors': errors
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)        


###### ------ update user status  -------- ########
from django.db import connection

class UpdateStatusAPI(APIView):
    def put(self, request):
        username = request.data.get('username')
        status_code = request.data.get('status_code')

        if not username or not status_code:
            return Response(
                {"error": "Les champs 'username' et 'status_code' sont obligatoires"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Requête SQL brute pour UPDATE
            with connection.cursor() as cursor:
                query = """
                UPDATE AM_USERS_LOCAL
                SET STATUS_CODE = %s
                WHERE USERNAME = %s
                """
                cursor.execute(query, [status_code, username])

                # Vérifier si une ligne a été mise à jour
                if cursor.rowcount == 0:
                    return Response(
                        {"error": f"Utilisateur {username} non trouvé"},
                        status=status.HTTP_404_NOT_FOUND
                    )

            return Response(
                {"status": "success", "message": f"STATUS_CODE mis à jour pour {username}"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": f"Erreur SQL : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )        