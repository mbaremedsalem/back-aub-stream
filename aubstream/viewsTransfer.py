from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
from django.db import transaction
from .serializersTransfere import *
from django.core.files.storage import FileSystemStorage
from datetime import datetime
import os
from django.http import HttpResponse
from django.db import connection
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from .email import send_validation_email






@api_view(['GET'])
def list_beneficiaires(request):
    beneficiaires = Beneficiaire.objects.all()
    serializer = BeneficiaireSerializer(beneficiaires, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def list_banques(request, type_banque=None):
    banques = Banque.objects.all()
    if type_banque:
        banques = banques.filter(type=type_banque)
    serializer = BanqueSerializer(banques, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def list_transfers1(request):
    transfers = Transfer.objects.all()
    serializer = TransferSerializer1(transfers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def list_transfers(request):
    try:
        # Explicitly select only the fields that exist
        transfers = Transfer.objects.raw("""
            SELECT ID_TRANSFER, DATE_ORDRE, NOM_CHARGEUR, 
                   MONTANT_EN_LETTRE, DEVISE, MONTANT_CHIFFRE,
                   FRAIS_MRU, FRAIS_ETRANGER, DATE_CREATION,
                   DATE_MODIFICATION, FILES, PLAFOND,
                   CURRENT_APPROVAL_LEVEL, OBSERVATION, STATUS,
                   CREATED_BY, NOM_BENEFICIAIRE, ADRESSE_BENEFICIAIRE,
                   IBAN_BENEFICIAIRE, NOM_BANQUE_BENEFICIAIRE,
                   CODE_SWIFT_BANQUE_BENEFICIAIRE,
                   NOM_BANQUE_INTERMEDIAIRE,
                   CODE_SWIFT_BANQUE_INTERMEDIAIRE,
                   ID_CLIENT, TYPE_CLIENT
            FROM TRANSFER
        """)
        serializer = TransferSerializer1(transfers, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def list_transfers_by_user(request, user_id):
    # Récupérer tous les transferts créés par l'utilisateur
    transfers = Transfer.objects.filter(created_by_id=user_id)
    result = []
    for transfer in transfers:
        transfer_data = TransferSerializer(transfer).data
        # Niveau d'approbation au moment de la création (toujours 1 à la création)
        transfer_data['niveau_creation'] = 1
        result.append(transfer_data)
    return Response(result)


from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response
from math import ceil

@api_view(['GET'])
def list_compte(request):
    try:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 100))
        offset = (page - 1) * per_page

        with connection.cursor() as cursor:
            # Requête pour obtenir le nombre total d'enregistrements
            cursor.execute("SELECT COUNT(*) FROM CPT_LOCAL")
            total_records = cursor.fetchone()[0]
            total_pages = ceil(total_records / per_page)

            # Requête paginée
            cursor.execute(
                "SELECT * FROM CPT_LOCAL OFFSET %s ROWS FETCH NEXT %s ROWS ONLY",
                [offset, per_page]
            )
            
            columns = [col[0].lower() for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response({
            'data': data,
            'pagination': {
                'total_records': total_records,
                'total_pages': total_pages,
                'current_page': page,
                'per_page': per_page,
                'next_page': page + 1 if page < total_pages else None,
                'prev_page': page - 1 if page > 1 else None
            }
        })

    except Exception as e:
        return Response({"error": str(e)}, status=500)




from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.core.mail import EmailMessage
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime
import smtplib
import logging
import time
import random
from threading import Thread
import json

# Configuration du logging
logger = logging.getLogger(__name__)

# Configuration des emails
EMAIL_CONFIG = {
    'max_retries': 2,
    'base_delay': 60,  # 60 secondes entre les emails
    'max_delay': 300,  # 5 minutes maximum
    'retry_delay': 120,  # 2 minutes pour les réessais
}

class EmailService:
    """Service dédié à l'envoi d'emails avec gestion des taux"""
    
    @staticmethod
    def send_email_safe(subject, message, recipient_list, max_retries=None):
        """
        Fonction sécurisée pour envoyer des emails avec gestion intelligente des erreurs
        """
        if max_retries is None:
            max_retries = EMAIL_CONFIG['max_retries']
            
        recipient = recipient_list[0] if recipient_list else ""
        
        for attempt in range(max_retries):
            try:
                # Délai exponentiel entre les tentatives
                if attempt > 0:
                    delay = (EMAIL_CONFIG['retry_delay'] * attempt) + random.randint(10, 30)
                    logger.info(f"Tentative {attempt + 1}/{max_retries} pour {recipient} dans {delay} secondes...")
                    time.sleep(delay)
                
                # Vérifier si c'est Gmail pour adapter la stratégie
                if recipient.endswith('@gmail.com'):
                    logger.info(f"Envoi à Gmail détecté: {recipient}")
                
                email = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipient_list,
                )
                
                # Envoyer avec timeout
                email.timeout = 30
                email.send(fail_silently=False)
                
                logger.info(f"✅ Email envoyé avec succès à: {recipient}")
                return True
                
            except smtplib.SMTPDataError as e:
                error_code = e.smtp_code
                error_message = str(e)
                
                # Gestion spécifique de l'erreur 450 (taux de réception)
                if error_code == 450 and "receiving mail at a rate" in error_message:
                    logger.warning(f"🚨 Destinataire {recipient} saturé (erreur 450).")
                    
                    if attempt < max_retries - 1:
                        # Attendre plus longtemps pour cette erreur spécifique
                        long_delay = EMAIL_CONFIG['max_delay']
                        logger.info(f"⏳ Attente de {long_delay} secondes avant nouvelle tentative...")
                        time.sleep(long_delay)
                        continue
                    else:
                        logger.error(f"❌ Échec définitif: destinataire {recipient} toujours saturé après {max_retries} tentatives")
                        return False
                
                # Autres erreurs SMTPDataError
                logger.error(f"❌ Erreur SMTPDataError {error_code} pour {recipient}: {error_message}")
                return False
                
            except smtplib.SMTPServerDisconnected as e:
                logger.warning(f"🔌 Connexion SMTP perdue. Tentative {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    continue
                else:
                    logger.error(f"❌ Échec après {max_retries} tentatives (connexion perdue)")
                    return False
                    
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"🔐 Erreur d'authentification SMTP: {str(e)}")
                return False
                
            except smtplib.SMTPException as e:
                logger.error(f"⚠️ Erreur SMTP générique pour {recipient}: {str(e)}")
                if attempt < max_retries - 1:
                    continue
                else:
                    return False
                    
            except Exception as e:
                logger.error(f"💥 Erreur inattendue pour {recipient}: {str(e)}")
                return False
        
        return False
    
    @staticmethod
    def send_confirmation_email(user_email, ref_fac, user_fullname):
        """Envoyer l'email de confirmation au créateur"""
        try:
            subject = f"Confirmation de création de transfert - Référence {ref_fac}"
            message = (
                f"Bonjour {user_fullname},\n\n"
                f"Votre demande de transfert portant la référence {ref_fac} a été créée avec succès.\n"
                f"Elle sera traitée prochainement par nos services.\n\n"
                f"Cordialement,\nVotre équipe de support"
            )
            
            return EmailService.send_email_safe(
                subject=subject,
                message=message,
                recipient_list=[user_email]
            )
            
        except Exception as e:
            logger.error(f"💥 Erreur dans send_confirmation_email: {str(e)}")
            return False
    
    @staticmethod
    def send_validation_email(user_email, ref_fac, validateur_info):
        """Envoyer l'email de notification au validateur"""
        try:
            subject = f"Demande de validation - Transfert {ref_fac}"
            message = (
                f"Bonjour {validateur_info['post']} ({validateur_info['fullname']}),\n\n"
                f"Vous avez une nouvelle demande de validation pour le Transfert portant la référence {ref_fac}.\n"
                f"Merci de vous connecter à la plateforme pour examiner et traiter cette demande.\n\n"
                f"Cordialement,\nVotre équipe de support"
            )
            
            return EmailService.send_email_safe(
                subject=subject,
                message=message,
                recipient_list=[user_email]
            )
            
        except Exception as e:
            logger.error(f"💥 Erreur dans send_validation_email: {str(e)}")
            return False

class EmailThread(Thread):
    """Thread pour l'envoi asynchrone des emails"""
    
    def __init__(self, emails_data):
        super().__init__()
        self.emails_data = emails_data
        self.daemon = True
    
    def run(self):
        """Méthode exécutée dans le thread"""
        try:
            logger.info(f"📧 Début de l'envoi asynchrone de {len(self.emails_data)} emails")
            
            for i, email_data in enumerate(self.emails_data):
                # Délai progressif entre les emails
                if i > 0:
                    delay = min(EMAIL_CONFIG['base_delay'] * i, EMAIL_CONFIG['max_delay'])
                    logger.info(f"⏳ Délai de {delay} secondes avant l'email {i+1}/{len(self.emails_data)}...")
                    time.sleep(delay)
                
                try:
                    if email_data['type'] == 'confirmation':
                        success = EmailService.send_confirmation_email(
                            email_data['user_email'],
                            email_data['ref_fac'],
                            email_data['user_fullname']
                        )
                    elif email_data['type'] == 'validation':
                        success = EmailService.send_validation_email(
                            email_data['user_email'],
                            email_data['ref_fac'],
                            email_data['validateur_info']
                        )
                    
                    if success:
                        logger.info(f"✅ Email {i+1}/{len(self.emails_data)} traité avec succès")
                    else:
                        logger.error(f"❌ Échec de l'email {i+1}/{len(self.emails_data)}")
                        
                except Exception as e:
                    logger.error(f"💥 Erreur lors du traitement de l'email {i+1}: {str(e)}")
            
            logger.info("✅ Envoi asynchrone des emails terminé")
            
        except Exception as e:
            logger.error(f"💥 Erreur critique dans EmailThread: {str(e)}")

@api_view(['POST'])
def create_transfer(request):
    try:
        # Récupération des données avec support pour JSON et form-data
        data = request.data.dict() if hasattr(request.data, 'dict') else request.data.copy()
        files = request.FILES.get('files')

        # Validation des champs obligatoires
        required_fields = [
            'nom_chargeur', 'montant_en_lettre', 'devise', 'montant_chiffre',
            'frais_MRU', 'frais_etranger',
            'nom_beneficiaire', 'adresse_beneficiaire', 'iban_beneficiaire',
            'nom_banque_beneficiaire', 'code_swift_banque_beneficiaire',
            'created_by_id', 'id_client', 'type_client',
            'code_swift_banque_intermediaire', 'nom_banque_intermediaire', 'ref_fac'
        ]

        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return Response({'error': f'Champs manquants: {", ".join(missing_fields)}'}, status=400)

        # Valeur par défaut pour status
        status_value = data.get('status', 'EN_ATTENTE')

        # Vérification de l'utilisateur
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT POID, EMAIL, FULLNAME, USERNAME, POST, BRANCH_CODE FROM AM_USERS_LOCAL WHERE ID = :user_id",
                    {'user_id': int(data['created_by_id'])}
                )
                
                user_row = cursor.fetchone()
                if not user_row:
                    return Response({'error': 'Utilisateur non trouvé'}, status=404)
                
                poid = user_row[0]
                user_email = user_row[1]
                user_fullname = user_row[2] if user_row[2] else user_row[3]
                user_agence = user_row[5]
                    
        except (ValueError, TypeError):
            return Response({'error': 'ID utilisateur invalide'}, status=400)

        # Gestion des fichiers
        file_path = None
        if files:
            try:
                fs = FileSystemStorage(location='media/Transfer')
                filename = f"transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{files.name}"
                saved_file = fs.save(filename, files)
                file_path = f"Transfer/{saved_file}"
            except Exception as file_error:
                return Response({'error': f'Erreur lors du traitement du fichier: {str(file_error)}'}, status=400)
        else:
            file_path = data.get('file_path')

        # Conversion des types de données
        try:
            montant_chiffre = float(data['montant_chiffre'])
            id_client = int(data['id_client'])
            created_by_id = int(data['created_by_id'])
        except (ValueError, TypeError) as conv_error:
            if file_path:
                try:
                    fs = FileSystemStorage()
                    fs.delete(file_path)
                except:
                    pass
            return Response({'error': f'Erreur de conversion des données: {str(conv_error)}'}, status=400)

        # Insertion dans la base de données
        with connection.cursor() as cursor:
            try:
                # Insertion du transfert
                transfer_id_var = cursor.var(int)
                sql = """
                    INSERT INTO TRANSFER (
                        DATE_ORDRE, NOM_CHARGEUR, MONTANT_EN_LETTRE, DEVISE,
                        MONTANT_CHIFFRE, FRAIS_MRU, FRAIS_ETRANGER, PLAFOND,
                        CURRENT_APPROVAL_LEVEL, OBSERVATION, STATUS,
                        NOM_BENEFICIAIRE, ADRESSE_BENEFICIAIRE, IBAN_BENEFICIAIRE,
                        NOM_BANQUE_BENEFICIAIRE, NOM_BANQUE_INTERMEDIAIRE,
                        CODE_SWIFT_BANQUE_BENEFICIAIRE, CODE_SWIFT_BANQUE_INTERMEDIAIRE,
                        CREATED_BY, FILES, ID_CLIENT, TYPE_CLIENT, REF_FAC
                    ) VALUES (
                        SYSDATE, :nom_chargeur, :montant_en_lettre, :devise,
                        :montant_chiffre, :frais_MRU, :frais_etranger, :plafond,
                        1, :observation, :status,
                        :nom_beneficiaire, :adresse_beneficiaire, :iban_beneficiaire,
                        :nom_banque_beneficiaire, :nom_banque_intermediaire,
                        :code_swift_banque_beneficiaire, :code_swift_banque_intermediaire,
                        :created_by_id, :file_path, :id_client, :type_client, :ref_fac
                    )
                    RETURNING ID_TRANSFER INTO :transfer_id
                """
                params = {
                    'nom_chargeur': data['nom_chargeur'],
                    'montant_en_lettre': data['montant_en_lettre'],
                    'devise': data['devise'],
                    'montant_chiffre': montant_chiffre,
                    'frais_MRU': data['frais_MRU'],
                    'frais_etranger': data['frais_etranger'],
                    'plafond': poid,
                    'observation': data.get('observation', ''),
                    'status': status_value,
                    'nom_beneficiaire': data['nom_beneficiaire'],
                    'adresse_beneficiaire': data['adresse_beneficiaire'],
                    'iban_beneficiaire': data['iban_beneficiaire'],
                    'nom_banque_beneficiaire': data['nom_banque_beneficiaire'],
                    'nom_banque_intermediaire': data['nom_banque_intermediaire'],
                    'code_swift_banque_beneficiaire': data['code_swift_banque_beneficiaire'],
                    'code_swift_banque_intermediaire': data['code_swift_banque_intermediaire'],
                    'created_by_id': created_by_id,
                    'file_path': file_path,
                    'id_client': id_client,
                    'type_client': data['type_client'],
                    'ref_fac': data['ref_fac'],
                    'transfer_id': transfer_id_var,
                }
                cursor.execute(sql, params)
                transfer_id = transfer_id_var.getvalue()

                # Insertion dans l'historique
                if transfer_id:
                    cursor.execute(
                        """
                        INSERT INTO HISTORIQUE_TRANSFER
                        (TRANSFER_ID, USER_ID, ACTION_TYPE, OBSERVATION, PLAFOND, CURRENT_APPROVAL_LEVEL, STATUS)
                        VALUES (:transfer_id, :user_id, 'CREATION', '', :plafond, 1, 'EN_ATTENTE')
                        """,
                        {
                            'transfer_id': transfer_id[0],
                            'user_id': created_by_id,
                            'plafond': poid
                        }
                    )

                # Récupérer les validateurs suivants (avec filtre par agence)
                cursor.execute(
                    """
                    SELECT ID, EMAIL, FULLNAME, USERNAME, POST 
                    FROM AM_USERS_LOCAL 
                    WHERE POID = :poid AND BRANCH_CODE = :branch_code
                    """,
                    {'poid': 12, 'branch_code': user_agence}
                )
                validateurs_suivants = cursor.fetchall()

                # Préparer les données pour les emails
                emails_data = []

                # Email de confirmation au créateur
                if user_email:
                    emails_data.append({
                        'type': 'confirmation',
                        'user_email': user_email,
                        'ref_fac': data['ref_fac'],
                        'user_fullname': user_fullname
                    })

                # Emails de notification aux validateurs
                for validateur in validateurs_suivants:
                    if validateur[1]:  # Vérifier que l'email existe
                        validateur_info = {
                            'post': validateur[4],
                            'fullname': validateur[2] if validateur[2] else validateur[3]
                        }
                        
                        emails_data.append({
                            'type': 'validation',
                            'user_email': validateur[1],
                            'ref_fac': data['ref_fac'],
                            'validateur_info': validateur_info
                        })

                # Lancer l'envoi asynchrone des emails
                if emails_data:
                    email_thread = EmailThread(emails_data)
                    email_thread.start()
                    email_message = f"{len(emails_data)} emails programmés pour envoi différé"
                    logger.info(f"🎯 {email_message}")
                else:
                    email_message = "Aucun email à envoyer"

                # Préparer les informations pour la réponse
                validateurs_info = []
                for validateur in validateurs_suivants:
                    validateurs_info.append({
                        'id': validateur[0],
                        'email': validateur[1],
                        'fullname': validateur[2] if validateur[2] else validateur[3],
                        'username': validateur[3],
                        'post': validateur[4]
                    })

                response_data = {
                    'success': True,
                    'transfer_id': transfer_id[0] if transfer_id else None,
                    'created_by_id': created_by_id,
                    'file_path': file_path,
                    'validateurs': validateurs_info,
                    'agence': user_agence,
                    'email_status': email_message,
                    'message': 'Transfert créé avec succès'
                }

                return Response(response_data, status=201)

            except Exception as db_error:
                if file_path:
                    try:
                        fs = FileSystemStorage()
                        fs.delete(file_path)
                    except:
                        pass
                return Response({
                    'error': 'Erreur base de données',
                    'details': str(db_error)
                }, status=500)

    except Exception as e:
        return Response({
            'error': 'Erreur serveur',
            'details': str(e),
            'type': type(e).__name__
        }, status=500)

# Route pour vérifier le statut des emails (optionnel)
@api_view(['GET'])
def email_status(request):
    """Endpoint pour vérifier la configuration email"""
    try:
        # Tester la connexion SMTP
        import smtplib
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=10)
        server.starttls()
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.quit()
        
        return Response({
            'status': 'success',
            'message': 'Configuration email fonctionnelle',
            'config': {
                'host': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT,
                'user': settings.EMAIL_HOST_USER,
                'from_email': settings.DEFAULT_FROM_EMAIL
            }
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': 'Erreur de configuration email',
            'error': str(e)
        }, status=500)

from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
def get_transfer_stats(request):
    """
    API pour récupérer les statistiques des transferts
    Retourne le nombre de dossiers validés, rejetés et le temps moyen de traitement
    """
    try:
        with connection.cursor() as cursor:
            # Compter les dossiers par statut
            cursor.execute("""
                SELECT 
                    STATUS,
                    COUNT(*) as count
                FROM TRANSFER 
                WHERE STATUS IN ('VALIDÉ', 'REJETÉ')
                GROUP BY STATUS
            """)
            
            status_rows = cursor.fetchall()
            
            stats = {
                'valides': 0,
                'rejetes': 0,
                'total_traites': 0,
                'temps_moyen_traitement_jours': 0,
                'temps_moyen_traitement_heures': 0
            }
            
            for status, count in status_rows:
                if status == 'VALIDÉ':
                    stats['valides'] = count
                elif status == 'REJETÉ':
                    stats['rejetes'] = count
            
            stats['total_traites'] = stats['valides'] + stats['rejetes']
            
            # Calculer le temps moyen de traitement - CORRECTION ICI
            cursor.execute("""
                SELECT 
                    AVG(
                        CASE 
                            WHEN DATE_MODIFICATION IS NOT NULL AND DATE_ORDRE IS NOT NULL 
                            THEN EXTRACT(DAY FROM (DATE_MODIFICATION - DATE_ORDRE)) 
                                 + EXTRACT(HOUR FROM (DATE_MODIFICATION - DATE_ORDRE)) / 24
                                 + EXTRACT(MINUTE FROM (DATE_MODIFICATION - DATE_ORDRE)) / (24 * 60)
                                 + EXTRACT(SECOND FROM (DATE_MODIFICATION - DATE_ORDRE)) / (24 * 60 * 60)
                            ELSE NULL 
                        END
                    ) as temps_moyen_jours
                FROM TRANSFER 
                WHERE STATUS IN ('VALIDÉ', 'REJETÉ')
                AND DATE_MODIFICATION IS NOT NULL
                AND DATE_ORDRE IS NOT NULL
            """)
            
            temps_result = cursor.fetchone()
            temps_moyen_jours = temps_result[0] if temps_result[0] is not None else 0
            
            stats['temps_moyen_traitement_jours'] = round(temps_moyen_jours, 2)
            stats['temps_moyen_traitement_heures'] = round(temps_moyen_jours * 24, 2)
            
            return Response({
                'success': True,
                'statistiques': stats,
                'date_calcul': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des statistiques',
            'details': str(e)
        }, status=500)

@api_view(['GET'])
def get_detailed_transfer_stats(request):
    """
    API pour récupérer des statistiques détaillées avec filtres optionnels
    """
    try:
        # Récupération des paramètres de filtre
        date_debut = request.GET.get('date_debut')
        date_fin = request.GET.get('date_fin')
        created_by = request.GET.get('created_by')
        
        where_conditions = ["STATUS IN ('VALIDÉ', 'REJETÉ')"]
        params = {}
        
        if date_debut:
            where_conditions.append("TRUNC(DATE_ORDRE) >= TO_DATE(:date_debut, 'YYYY-MM-DD')")
            params['date_debut'] = date_debut
            
        if date_fin:
            where_conditions.append("TRUNC(DATE_ORDRE) <= TO_DATE(:date_fin, 'YYYY-MM-DD')")
            params['date_fin'] = date_fin
            
        if created_by:
            where_conditions.append("CREATED_BY = :created_by")
            params['created_by'] = int(created_by)
        
        where_clause = " AND ".join(where_conditions)
        
        with connection.cursor() as cursor:
            # Statistiques par statut
            cursor.execute(f"""
                SELECT 
                    STATUS,
                    COUNT(*) as count,
                    AVG(
                        CASE 
                            WHEN DATE_MODIFICATION IS NOT NULL AND DATE_ORDRE IS NOT NULL 
                            THEN (DATE_MODIFICATION - DATE_ORDRE) 
                            ELSE NULL 
                        END
                    ) as temps_moyen_jours
                FROM TRANSFER 
                WHERE {where_clause}
                GROUP BY STATUS
            """, params)
            
            status_details = cursor.fetchall()
            
            # Statistiques générales
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    AVG(
                        CASE 
                            WHEN DATE_MODIFICATION IS NOT NULL AND DATE_ORDRE IS NOT NULL 
                            THEN (DATE_MODIFICATION - DATE_ORDRE) 
                            ELSE NULL 
                        END
                    ) as temps_moyen_total_jours
                FROM TRANSFER 
                WHERE {where_clause}
            """, params)
            
            general_stats = cursor.fetchone()
            
            # Préparation des données de réponse
            details = []
            total_valides = 0
            total_rejetes = 0
            
            for status, count, temps_moyen in status_details:
                temps_jours = round(temps_moyen if temps_moyen is not None else 0, 2)
                details.append({
                    'status': status,
                    'nombre': count,
                    'temps_moyen_jours': temps_jours,
                    'temps_moyen_heures': round(temps_jours * 24, 2)
                })
                
                if status == 'VALIDÉ':
                    total_valides = count
                elif status == 'REJETÉ':
                    total_rejetes = count
            
            total_traites, temps_moyen_total = general_stats
            temps_moyen_total_jours = round(temps_moyen_total if temps_moyen_total is not None else 0, 2)
            
            # Calcul du taux de validation
            taux_validation = 0
            if total_traites > 0:
                taux_validation = round((total_valides / total_traites) * 100, 2)
            
            return Response({
                'success': True,
                'periode': {
                    'date_debut': date_debut,
                    'date_fin': date_fin
                },
                'statistiques_generales': {
                    'total_dossiers_traites': total_traites,
                    'dossiers_valides': total_valides,
                    'dossiers_rejetes': total_rejetes,
                    'taux_validation': taux_validation,
                    'temps_moyen_traitement_jours': temps_moyen_total_jours,
                    'temps_moyen_traitement_heures': round(temps_moyen_total_jours * 24, 2)
                },
                'details_par_statut': details,
                'date_calcul': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques détaillées: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des statistiques détaillées',
            'details': str(e)
        }, status=500)

@api_view(['GET'])
def get_transfer_timeline_stats(request):
    """
    API pour récupérer les statistiques de timeline des transferts
    """
    try:
        with connection.cursor() as cursor:
            # Temps moyen par étape de traitement
            cursor.execute("""
                SELECT 
                    STATUS,
                    AVG(
                        CASE 
                            WHEN DATE_MODIFICATION IS NOT NULL AND DATE_ORDRE IS NOT NULL 
                            THEN (DATE_MODIFICATION - DATE_ORDRE) 
                            ELSE NULL 
                        END
                    ) as temps_moyen,
                    MIN(
                        CASE 
                            WHEN DATE_MODIFICATION IS NOT NULL AND DATE_ORDRE IS NOT NULL 
                            THEN (DATE_MODIFICATION - DATE_ORDRE) 
                            ELSE NULL 
                        END
                    ) as temps_min,
                    MAX(
                        CASE 
                            WHEN DATE_MODIFICATION IS NOT NULL AND DATE_ORDRE IS NOT NULL 
                            THEN (DATE_MODIFICATION - DATE_ORDRE) 
                            ELSE NULL 
                        END
                    ) as temps_max
                FROM TRANSFER 
                WHERE STATUS IN ('VALIDÉ', 'REJETÉ')
                AND DATE_MODIFICATION IS NOT NULL
                AND DATE_ORDRE IS NOT NULL
                GROUP BY STATUS
            """)
            
            timeline_stats = cursor.fetchall()
            
            # Préparation des données
            timeline_data = []
            for status, moyen, minimum, maximum in timeline_stats:
                timeline_data.append({
                    'status': status,
                    'temps_moyen_jours': round(moyen if moyen is not None else 0, 2),
                    'temps_min_jours': round(minimum if minimum is not None else 0, 2),
                    'temps_max_jours': round(maximum if maximum is not None else 0, 2),
                    'temps_moyen_heures': round((moyen if moyen is not None else 0) * 24, 2),
                    'temps_min_heures': round((minimum if minimum is not None else 0) * 24, 2),
                    'temps_max_heures': round((maximum if maximum is not None else 0) * 24, 2)
                })
            
            return Response({
                'success': True,
                'timeline_statistiques': timeline_data,
                'unites': {
                    'jours': 'Temps en jours calendaires',
                    'heures': 'Temps en heures (jours * 24)'
                }
            })
            
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques de timeline: {str(e)}")
        return Response({
            'error': 'Erreur lors de la récupération des statistiques de timeline',
            'details': str(e)
        }, status=500)


@api_view(['PUT'])
def update_transfer(request, transfer_id):
    try:
        data = request.POST.dict()
        files = request.FILES.get('files')

        # Vérification que le transfert existe
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT ID_TRANSFER, FILES FROM TRANSFER WHERE ID_TRANSFER = :transfer_id",
                {'transfer_id': transfer_id}
            )
            transfer = cursor.fetchone()
            if not transfer:
                return Response({'error': 'Transfert non trouvé'}, status=404)

            current_file_path = transfer[1]

        # Gestion du fichier
        file_path = current_file_path  # Conserver le fichier existant par défaut
        if files:
            fs = FileSystemStorage(location='media/Transfer')
            # Supprimer l'ancien fichier s'il existe
            if current_file_path:
                try:
                    fs.delete(current_file_path)
                except:
                    pass
            # Sauvegarder le nouveau fichier
            filename = f"transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{files.name}"
            saved_file = fs.save(filename, files)
            file_path = f"Transfer/{saved_file}"

        # Construction dynamique de la requête SQL
        # update_fields = []
        # Construction de la requête SQL avec PLAFOND fixé à 4
        update_fields = ["PLAFOND = 4"]  # Ajout direct du plafond

        params = {'transfer_id': transfer_id}

        # Liste des champs modifiables
        updatable_fields = [
            'nom_chargeur', 'montant_en_lettre', 'devise', 'montant_chiffre',
            'frais_MRU', 'frais_etranger', 'observation', 'nom_beneficiaire',
            'adresse_beneficiaire', 'iban_beneficiaire', 'nom_banque_beneficiaire',
            'code_swift_banque_beneficiaire', 'nom_banque_intermediaire',
            'code_swift_banque_intermediaire', 'id_client', 'type_client', 'status'
        ]

        # Ajouter seulement les champs fournis dans la requête
        for field in updatable_fields:
            if field in data:
                update_fields.append(f"{field.upper()} = :{field}")
                params[field] = data[field] if field != 'montant_chiffre' else float(data[field])

        # Ajouter le fichier si modifié
        if files or 'file_path' in data:
            update_fields.append("FILES = :file_path")
            params['file_path'] = file_path

        if not update_fields:
            return Response({'error': 'Aucun champ à mettre à jour'}, status=400)

        # Exécution de la mise à jour
        with connection.cursor() as cursor:
            sql = f"""
                UPDATE TRANSFER SET
                {', '.join(update_fields)}
                WHERE ID_TRANSFER = :transfer_id
            """
            cursor.execute(sql, params)

            # Insertion dans l'historique
            cursor.execute(
                """
                INSERT INTO HISTORIQUE_TRANSFER
                (TRANSFER_ID, USER_ID, ACTION_TYPE, OBSERVATION, STATUS)
                VALUES (:transfer_id, :user_id, 'MODIFICATION', :observation, :status)
                """,
                {
                    'transfer_id': transfer_id,
                    'user_id': int(data.get('created_by_id', 0)),
                    'observation': data.get('observation_historique', 'Mise à jour partielle du transfert'),
                    'status': data.get('status', 'EN_ATTENTE')
                }
            )

        return Response({
            'success': True,
            'transfer_id': transfer_id,
            'message': 'Transfert mis à jour avec succès',
            'updated_fields': update_fields,
            'file_updated': bool(files or 'file_path' in data)
        }, status=200)

    except Exception as e:
        if 'file_path' in locals() and file_path and file_path != current_file_path:
            try:
                fs = FileSystemStorage()
                fs.delete(file_path)
            except:
                pass
        return Response({
            'error': 'Erreur lors de la mise à jour',
            'details': str(e),
            'type': type(e).__name__
        }, status=500)


# @api_view(['PUT'])
# def update_transfer(request, transfer_id):
#     try:
#         data = request.POST.dict()
#         files = request.FILES.get('files')

#         # Vérification que le transfert existe
#         with connection.cursor() as cursor:
#             cursor.execute(
#                 "SELECT ID_TRANSFER, FILES FROM TRANSFER WHERE ID_TRANSFER = :transfer_id",
#                 {'transfer_id': transfer_id}
#             )
#             transfer = cursor.fetchone()
#             if not transfer:
#                 return Response({'error': 'Transfert non trouvé'}, status=404)
            
#             current_file_path = transfer[1]

#         # Gestion du fichier
#         file_path = current_file_path  # Conserver le fichier existant par défaut
#         if files:
#             fs = FileSystemStorage(location='media/Transfer')
#             # Supprimer l'ancien fichier s'il existe
#             if current_file_path:
#                 try:
#                     fs.delete(current_file_path)
#                 except:
#                     pass
#             # Sauvegarder le nouveau fichier
#             filename = f"transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{files.name}"
#             saved_file = fs.save(filename, files)
#             file_path = f"Transfer/{saved_file}"

#         # Construction dynamique de la requête SQL
#         # update_fields = []
#         # Construction de la requête SQL avec PLAFOND fixé à 4
#         update_fields = ["PLAFOND = 4"]  # Ajout direct du plafond

#         params = {'transfer_id': transfer_id}
        
#         # Liste des champs modifiables
#         updatable_fields = [
#             'nom_chargeur', 'montant_en_lettre', 'devise', 'montant_chiffre',
#             'frais_MRU', 'frais_etranger', 'observation', 'nom_beneficiaire',
#             'adresse_beneficiaire', 'iban_beneficiaire', 'nom_banque_beneficiaire',
#             'code_swift_banque_beneficiaire', 'nom_banque_intermediaire',
#             'code_swift_banque_intermediaire', 'id_client', 'type_client', 'status'
#         ]
        
#         # Ajouter seulement les champs fournis dans la requête
#         for field in updatable_fields:
#             if field in data:
#                 update_fields.append(f"{field.upper()} = :{field}")
#                 params[field] = data[field] if field != 'montant_chiffre' else float(data[field])
        
#         # Ajouter le fichier si modifié
#         if files or 'file_path' in data:
#             update_fields.append("FILES = :file_path")
#             params['file_path'] = file_path

#         if not update_fields:
#             return Response({'error': 'Aucun champ à mettre à jour'}, status=400)

#         # Exécution de la mise à jour
#         with connection.cursor() as cursor:
#             sql = f"""
#                 UPDATE TRANSFER SET
#                 {', '.join(update_fields)}
#                 WHERE ID_TRANSFER = :transfer_id
#             """
#             cursor.execute(sql, params)

#             # Insertion dans l'historique
#             cursor.execute(
#                 """
#                 INSERT INTO HISTORIQUE_TRANSFER
#                 (TRANSFER_ID, USER_ID, ACTION_TYPE, OBSERVATION, STATUS)
#                 VALUES (:transfer_id, :user_id, 'MODIFICATION', :observation, :status)
#                 """,
#                 {
#                     'transfer_id': transfer_id,
#                     'user_id': int(data.get('created_by_id', 0)),
#                     'observation': data.get('observation_historique', 'Mise à jour partielle du transfert'),
#                     'status': data.get('status', 'EN_ATTENTE')
#                 }
#             )

#         return Response({
#             'success': True,
#             'transfer_id': transfer_id,
#             'message': 'Transfert mis à jour avec succès',
#             'updated_fields': update_fields,
#             'file_updated': bool(files or 'file_path' in data)
#         }, status=200)

#     except Exception as e:
#         if 'file_path' in locals() and file_path and file_path != current_file_path:
#             try:
#                 fs = FileSystemStorage()
#                 fs.delete(file_path)
#             except:
#                 pass
#         return Response({
#             'error': 'Erreur lors de la mise à jour',
#             'details': str(e),
#             'type': type(e).__name__
#         }, status=500)

@api_view(['GET'])
def get_transfer_by_id(request, transfer_id):
    """
    Récupère tous les attributs d'un transfert spécifique par son ID
    """
    try:
        # Conversion et validation de l'ID
        try:
            transfer_id = int(transfer_id)
        except ValueError:
            return Response({
                'error': 'ID doit être un nombre entier',
                'received_id': transfer_id,
                'type_received': str(type(transfer_id))
            }, status=400)

        with connection.cursor() as cursor:
            # 1. Vérification de l'existence du transfert
            cursor.execute("""
                SELECT COUNT(*) 
                FROM TRANSFER 
                WHERE ID_TRANSFER = :transfer_id
            """, {'transfer_id': transfer_id})
            
            if cursor.fetchone()[0] == 0:
                # Diagnostic avancé
                cursor.execute("SELECT MIN(ID_TRANSFER), MAX(ID_TRANSFER) FROM TRANSFER")
                min_id, max_id = cursor.fetchone()
                return Response({
                    'error': f'Transfert {transfer_id} non trouvé',
                    'diagnostic': {
                        'plage_ids_existants': f'{min_id} à {max_id}',
                        'votre_id': transfer_id,
                        'suggestions': [
                            'Vérifiez que l\'ID existe dans cette plage',
                            'Confirmez que le transfert n\'a pas été supprimé'
                        ]
                    }
                }, status=404)

            # 2. Requête complète avec tous les attributs
            cursor.execute("""
                SELECT 
                    t.ID_TRANSFER,
                    TO_CHAR(t.DATE_ORDRE, 'YYYY-MM-DD HH24:MI:SS') as DATE_ORDRE,
                    t.NOM_CHARGEUR,
                    dbms_lob.substr(t.MONTANT_EN_LETTRE, 4000, 1) as MONTANT_EN_LETTRE,
                    t.DEVISE,
                    t.MONTANT_CHIFFRE,
                    t.FRAIS_MRU,
                    t.FRAIS_ETRANGER,
                    TO_CHAR(t.DATE_CREATION, 'YYYY-MM-DD HH24:MI:SS') as DATE_CREATION,
                    TO_CHAR(t.DATE_MODIFICATION, 'YYYY-MM-DD HH24:MI:SS') as DATE_MODIFICATION,
                    t.FILES,
                    t.FILESSWIFT,  -- Champ complet
                    t.PLAFOND,
                    t.CURRENT_APPROVAL_LEVEL,
                    t.OBSERVATION,
                    t.STATUS,
                    t.CREATED_BY,
                    TO_CHAR(t.CREATION_DATE, 'YYYY-MM-DD HH24:MI:SS') as CREATION_DATE,
                    t.MODIFIED_BY,
                    TO_CHAR(t.MODIFICATION_DATE, 'YYYY-MM-DD HH24:MI:SS') as MODIFICATION_DATE,
                    t.NOM_BENEFICIAIRE,
                    t.ADRESSE_BENEFICIAIRE,
                    t.IBAN_BENEFICIAIRE,
                    t.NOM_BANQUE_BENEFICIAIRE,
                    t.CODE_SWIFT_BANQUE_BENEFICIAIRE,
                    t.NOM_BANQUE_INTERMEDIAIRE,
                    t.CODE_SWIFT_BANQUE_INTERMEDIAIRE,
                    t.ID_CLIENT,
                    t.TYPE_CLIENT,
                    t.REF_FAC,
                    u.USERNAME as CREATED_BY_USERNAME
                FROM TRANSFER t
                LEFT JOIN AM_USERS_LOCAL u ON t.CREATED_BY = u.ID
                WHERE t.ID_TRANSFER = :transfer_id
            """, {'transfer_id': transfer_id})

            # 3. Formatage des résultats
            columns = [col[0].lower() for col in cursor.description]
            row = cursor.fetchone()
            transfer_data = dict(zip(columns, row))

            # 4. Gestion du fichier PDF principal (FILES)
            file_url = None
            if transfer_data.get('files'):
                try:
                    fs = FileSystemStorage()
                    file_path = transfer_data['files']
                    if fs.exists(file_path):
                        file_url = request.build_absolute_uri(fs.url(file_path))
                        transfer_data['file_url'] = file_url
                    else:
                        transfer_data['file_error'] = f"Fichier principal non trouvé: {file_path}"
                except Exception as file_error:
                    transfer_data['file_error'] = str(file_error)

            # 5. Gestion spécifique du FILESSWIFT (qui est un chemin vers un fichier PDF)
            filesswift_url = None
            filesswift_content = None
            
            if transfer_data.get('filesswift'):
                try:
                    fs = FileSystemStorage()
                    filesswift_path = transfer_data['filesswift']
                    
                    # Vérifier si c'est un chemin de fichier valide
                    if fs.exists(filesswift_path):
                        # Générer l'URL pour le fichier SWIFT
                        filesswift_url = request.build_absolute_uri(fs.url(filesswift_path))
                        transfer_data['filesswift_url'] = filesswift_url
                        
                        # Optionnel : lire le contenu du fichier PDF SWIFT si nécessaire
                        # (mais pour un PDF, on retourne généralement l'URL plutôt que le contenu)
                        try:
                            with fs.open(filesswift_path) as f:
                                # Si vous voulez extraire du texte du PDF, vous pouvez utiliser PyPDF2 ou pdfplumber
                                # Mais attention, cela peut être lourd pour de gros fichiers
                                filesswift_content = "Contenu PDF SWIFT - Utilisez l'URL pour télécharger le fichier"
                        except Exception as read_error:
                            filesswift_content = f"Impossible de lire le fichier SWIFT: {str(read_error)}"
                    
                    else:
                        transfer_data['filesswift_error'] = f"Fichier SWIFT non trouvé: {filesswift_path}"
                        
                except Exception as swift_error:
                    transfer_data['filesswift_error'] = f"Erreur traitement SWIFT: {str(swift_error)}"

            # 6. Ajout des métadonnées
            transfer_data['metadata'] = {
                'retrieved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'api_version': '1.0',
                'file_available': bool(file_url),
                'filesswift_available': bool(filesswift_url)
            }

            return Response({
                'success': True,
                'transfer': transfer_data,
                'files': {
                    'principal_pdf_url': file_url,
                    'swift_pdf_url': filesswift_url
                }
            })

    except cx_Oracle.DatabaseError as db_err:
        error_obj, = db_err.args
        return Response({
            'error': 'Erreur Oracle',
            'code': error_obj.code,
            'message': error_obj.message,
            'context': 'Vérifiez les permissions et la connexion à la base'
        }, status=500)

    except Exception as e:
        return Response({
            'error': 'Erreur technique',
            'details': str(e),
            'type': type(e).__name__,
            'traceback': traceback.format_exc() if settings.DEBUG else None
        }, status=500)

@api_view(['GET'])
def transfer_detail(request, pk):
    try:
        transfer = Transfer.objects.get(pk=pk)
    except Transfer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    transfer_data = TransferSerializer(transfer).data
    # Ajout des infos client selon type_client
    client_info = None
    if transfer.type_client == 'PHYSIQUE':
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM CLIENT_PHYSIQUE WHERE ID_CLIENT_PHYSIQUE = :id", {'id': transfer.id_client})
            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                client_dict = dict(zip(columns, row))
                client_info = client_dict
    elif transfer.type_client == 'MORAL':
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM CLIENT_MORAL WHERE ID_CLIENT_MORAL = :id", {'id': transfer.id_client})
            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                client_dict = dict(zip(columns, row))
                client_info = client_dict
    transfer_data['client_info'] = client_info
    return Response(transfer_data)



@api_view(['GET'])
def get_transfer_file(request, transfer_id):
    try:
        with connection.cursor() as cursor:
            # Récupérer le fichier depuis Oracle
            cursor.execute("""
                SELECT files FROM SYSTEM.TRANSFER 
                WHERE id_transfer = :transfer_id
            """, {'transfer_id': transfer_id})
            
            row = cursor.fetchone()
            
            if not row or not row[0]:
                return HttpResponse(
                    'Fichier non trouvé',
                    status=404,
                    content_type='text/plain'
                )
            
            file_content = row[0]
            
            # Si c'est un CLOB (texte)
            if isinstance(file_content, str):
                response = HttpResponse(
                    file_content,
                    content_type='application/octet-stream'
                )
            # Si c'est un BLOB (binaire)
            else:
                response = HttpResponse(
                    file_content.read(),
                    content_type='application/octet-stream'
                )
            
            # Nom du fichier pour le téléchargement
            response['Content-Disposition'] = f'attachment; filename="transfer_{transfer_id}_file"'
            return response
            
    except Exception as e:
        return HttpResponse(
            f'Erreur: {str(e)}',
            status=500,
            content_type='text/plain'
        )    

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.db import connection

@api_view(['POST'])
@csrf_exempt
def approve_transfer(request, transfer_id):
    """
    Ajoute le POID de l'utilisateur au plafond du transfert, ajoute une observation,
    incrémente current_approval_level, met à jour le status, et peut sauvegarder un fichier
    dans FILESSWIFT si l'utilisateur a le POST "Charger Des Operation Etrangere".
    """
    try:
        user_id = request.data.get('user_id')
        observation = request.data.get('observation', '')
        if not user_id:
            return Response({'error': 'user_id requis'}, status=400)

        with connection.cursor() as cursor:
               # new update ici medos!

            cursor.execute("""
                SELECT USER_ID, ACTION_DATE, ACTION_TYPE
                FROM (
                    SELECT USER_ID, ACTION_DATE, ACTION_TYPE
                    FROM HISTORIQUE_TRANSFER
                    ORDER BY ACTION_DATE DESC
                )
                WHERE ROWNUM = 1
            """)

            dernier_enregistrement = cursor.fetchone()  # Utiliser fetchone() au lieu de fetchall()

            print("------------- decision ------------------------")
            print("dernier_enregistrement : ", dernier_enregistrement)
            print("ACTION_TYPE : ", dernier_enregistrement[2])
            print("------------- decision ------------------------")

            print("---------------------------------------------------------")
            if dernier_enregistrement:
                dernier_user_id = dernier_enregistrement[0]  # Premier élément = USER_ID
                print("dernier_user_id : ", dernier_user_id)
            else:
                print("Aucun enregistrement trouvé")
                dernier_user_id = None

            print("user_id actuel : ", user_id)
            print("---------------------------------------------------------")

            if dernier_enregistrement and dernier_user_id == int(user_id):
                action_type = dernier_enregistrement[2]

                if action_type == 'REJET':
                    return Response({
                        'error': 'Vous avez déjà rejeté ce dossier',
                        'code': 'ACTION_DUPLIQUEE'
                    }, status=400)
                else:
                    return Response({
                        'error': 'Vous avez déjà validé ce dossier',
                        'code': 'ACTION_DUPLIQUEE'
                    }, status=400)
        #         return Response({
        #     'error': 'Vous avez déjà validé ce dossier',
        #     'code': 'ACTION_DUPLIQUEE'
        # }, status=400)

            # fin update ici medos

            # Vérifier si l'utilisateur a déjà donné son avis sur ce transfert
            cursor.execute("""
                SELECT COUNT(*)
                FROM HISTORIQUE_TRANSFER
                WHERE TRANSFER_ID = :transfer_id AND USER_ID = :user_id AND ACTION_TYPE = 'APPROBATION'
            """, {
                'transfer_id': int(transfer_id),
                'user_id': int(user_id)
            })
            existing_approval_count = cursor.fetchone()[0]

            # Vérifier si le transfert a déjà été rejeté
            cursor.execute("""
                SELECT COUNT(*)
                FROM HISTORIQUE_TRANSFER
                WHERE TRANSFER_ID = :transfer_id AND ACTION_TYPE = 'REJET'
            """, {'transfer_id': int(transfer_id)})
            existing_rejection_count = cursor.fetchone()[0]

            # Bloquer si l'utilisateur a déjà approuvé ET que le transfert n'a jamais été rejeté
            if existing_approval_count > 0 and existing_rejection_count == 0:
                return Response({
                    'error': 'Vous avez déjà ajouté votre avis sur ce transfert',
                    'code': 'ALREADY_APPROVED'
                }, status=400)



            # Récupérer le POID, agence, et POST de l'utilisateur
            cursor.execute("""
                SELECT POID, BRANCH_CODE, POST
                FROM AM_USERS_LOCAL
                WHERE ID = :user_id
            """, {'user_id': int(user_id)})
            user_row = cursor.fetchone()
            if not user_row:
                return Response({'error': 'Utilisateur non trouvé'}, status=404)

            poid = user_row[0]
            user_agence = user_row[1]
            post_user = user_row[2]

            # Déterminer le POID du prochain validateur
            if poid == 12:
                poid_next_validateur = 20
            elif poid == 20:
                poid_next_validateur = 36
            elif poid == 36:
                poid_next_validateur = 56
            elif poid == 56:
                poid_next_validateur = 92
            else:
                poid_next_validateur = 4  # Par défaut

            # Récupérer les données du transfert
            cursor.execute("""
                SELECT PLAFOND, CURRENT_APPROVAL_LEVEL, REF_FAC
                FROM TRANSFER
                WHERE ID_TRANSFER = :transfer_id
            """, {'transfer_id': int(transfer_id)})
            plafond_row = cursor.fetchone()
            if not plafond_row:
                return Response({'error': 'Transfert non trouvé'}, status=404)

            plafond = plafond_row[0] or 0
            current_approval_level = plafond_row[1] or 0
            ref_fac = plafond_row[2]

            # Calculer les nouvelles valeurs
            new_plafond = min(plafond + poid, 220)
            new_approval_level = current_approval_level + 1
            status = 'VALIDE' if new_plafond == 220 else 'EN_ATTENTE'

            # Sauvegarder fichier s'il est requis
            if post_user == "Charger Des Operation Etrangere":
                fichier = request.FILES.get('fichier')
                if not fichier:
                    return Response({'error': "Le fichier FILESSWIFT est requis."}, status=400)

                # Enregistrement du fichier dans le MEDIA folder
                from django.core.files.storage import default_storage

                # Chemin de sauvegarde : media/transfers/<nom_fichier>
                chemin_fichier = default_storage.save(f'transfers/{fichier.name}', fichier)

                # Enregistrer le chemin dans la base
                cursor.execute("""
                    UPDATE TRANSFER
                    SET FILESSWIFT = :chemin_fichier
                    WHERE ID_TRANSFER = :transfer_id
                """, {
                    'chemin_fichier': chemin_fichier,
                    'transfer_id': int(transfer_id)
                })

            # Mise à jour du transfert
            cursor.execute("""
                UPDATE TRANSFER
                SET PLAFOND = :new_plafond,
                    observation = :observation,
                    current_approval_level = :new_approval_level,
                    status = :status
                WHERE ID_TRANSFER = :transfer_id
            """, {
                'new_plafond': new_plafond,
                'observation': observation,
                'new_approval_level': new_approval_level,
                'status': status,
                'transfer_id': int(transfer_id)
            })

            # Historique d'approbation
            cursor.execute("""
                INSERT INTO HISTORIQUE_TRANSFER
                (TRANSFER_ID, USER_ID, ACTION_TYPE, OBSERVATION, PLAFOND, CURRENT_APPROVAL_LEVEL, STATUS)
                VALUES (:transfer_id, :user_id, :action_type, :observation, :plafond, :current_approval_level, :status)
            """, {
                'transfer_id': int(transfer_id),
                'user_id': int(user_id),
                'action_type': 'APPROBATION',
                'observation': observation,
                'plafond': new_plafond,
                'current_approval_level': new_approval_level,
                'status': status
            })

            # Notification si EN_ATTENTE
            validateurs_suivants = []
            if status == 'EN_ATTENTE':
                cursor.execute("""
                    SELECT ID, EMAIL, FULLNAME, USERNAME, POST
                    FROM AM_USERS_LOCAL
                    WHERE POID = :poid AND BRANCH_CODE = :branch_code
                """, {
                    'poid': poid_next_validateur,
                    'branch_code': user_agence
                })
                validateurs_suivants = cursor.fetchall()

                if not validateurs_suivants:
                    cursor.execute("""
                        SELECT ID, EMAIL, FULLNAME, USERNAME, POST
                        FROM AM_USERS_LOCAL
                        WHERE POID = :poid
                    """, {'poid': poid_next_validateur})
                    validateurs_suivants = cursor.fetchall()

                print(f"Nombre de validateurs trouvés: {len(validateurs_suivants)}")

                for validateur in validateurs_suivants:
                    try:
                        class ValidateurObj:
                            def __init__(self, post, fullname):
                                self.post = post
                                self.fullname = fullname

                        validateur_obj = ValidateurObj(
                            post=validateur[4],
                            fullname=validateur[2] if validateur[2] else validateur[3]
                        )

                        send_validation_email(
                            user_email=validateur[1],
                            ref_fac=ref_fac,
                            validateur=validateur_obj
                        )
                        print(f"Email envoyé à {validateur[1]}")
                    except Exception as email_error:
                        print(f"Erreur d'envoi de mail à {validateur[1]}: {str(email_error)}")

            # Commit final
            connection.commit()

        return Response({
            'success': True,
            'transfer_id': transfer_id,
            'new_plafond': new_plafond,
            'current_approval_level': new_approval_level,
            'status': status,
            'next_validator_poid': poid_next_validateur if status == 'EN_ATTENTE' else None,
            'validators_found': len(validateurs_suivants) if status == 'EN_ATTENTE' else 0,
            'was_previously_rejected': existing_rejection_count > 0
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)



#-------------------------- 2nd choix : -------
@api_view(['POST'])
@csrf_exempt
def reject_transfer(request, transfer_id):
    """
    Rejette le transfert en décrémentant le current_approval_level et en soustrayant le POID de l'utilisateur du plafond.
    Ajoute une observation dans l'historique.
    Envoie une notification par email au créateur du transfert.
    """
    try:
        print("ici ici ici !!!!!!!!!!!!!!!!!!!!!!!----")

        user_id = request.data.get('user_id')
        observation = request.data.get('observation', '')
        if not user_id:
            return Response({'error': 'user_id requis'}, status=400)

        with connection.cursor() as cursor:

            # new debi ici medos!

            cursor.execute("""
        SELECT USER_ID, ACTION_DATE, ACTION_TYPE
        FROM (
            SELECT USER_ID, ACTION_DATE, ACTION_TYPE
            FROM HISTORIQUE_TRANSFER
            ORDER BY ACTION_DATE DESC
        )
        WHERE ROWNUM = 1
    """)

            dernier_enregistrement = cursor.fetchone()  # Utiliser fetchone() au lieu de fetchall()
            print("dernier_enregistrement : ", dernier_enregistrement)

            print("---------------------------------------------------------")
            if dernier_enregistrement:
                dernier_user_id = dernier_enregistrement[0]  # Premier élément = USER_ID
                print("dernier_user_id : ", dernier_user_id)
            else:
                print("Aucun enregistrement trouvé")
                dernier_user_id = None

            print("user_id actuel : ", user_id)
            print("---------------------------------------------------------")

            if dernier_enregistrement and dernier_user_id == int(user_id):
                action_type = dernier_enregistrement[2]

                if action_type == 'REJET':
                    return Response({
                        'error': 'Vous avez déjà rejeté ce dossier',
                        'code': 'ACTION_DUPLIQUEE'
                    }, status=400)
                else:
                    return Response({
                        'error': 'Vous avez déjà validé ce dossier',
                        'code': 'ACTION_DUPLIQUEE'
                    }, status=400)

            # fin update ici medos

            # Vérifier si l'utilisateur a déjà donné son avis sur ce transfert
            cursor.execute("""
                SELECT COUNT(*)
                FROM HISTORIQUE_TRANSFER
                WHERE TRANSFER_ID = :transfer_id AND USER_ID = :user_id AND ACTION_TYPE = 'REJET'
            """, {
                'transfer_id': int(transfer_id),
                'user_id': int(user_id)
            })
            existing_rejection_count = cursor.fetchone()[0]

            # Vérifier si le transfert a déjà été approuvé après le dernier rejet
            cursor.execute("""
                SELECT COUNT(*)
                FROM HISTORIQUE_TRANSFER
                WHERE TRANSFER_ID = :transfer_id AND ACTION_TYPE = 'APPROBATION'
            """, {'transfer_id': int(transfer_id)})
            existing_approval_count = cursor.fetchone()[0]

            # Bloquer si l'utilisateur a déjà rejeté ET que le transfert n'a jamais été approuvé après
            if existing_rejection_count > 0 and existing_approval_count == 0:
                return Response({
                    'error': 'Vous avez déjà ajouté votre avis sur ce transfert',
                    'code': 'ALREADY_REJECTED'
                }, status=400)

            # Récupérer le POID et les infos de l'utilisateur qui rejette
            cursor.execute("SELECT POID, FULLNAME, USERNAME FROM AM_USERS_LOCAL WHERE ID = :user_id", {'user_id': int(user_id)})
            user_row = cursor.fetchone()
            if not user_row:
                return Response({'error': 'Utilisateur non trouvé'}, status=404)

            poid = user_row[0]
            rejecter_name = user_row[1] if user_row[1] else user_row[2]

            # Récupérer les informations actuelles du transfert et du créateur
            cursor.execute("""
                SELECT t.PLAFOND, t.CURRENT_APPROVAL_LEVEL, t.REF_FAC, t.CREATED_BY,
                       u.EMAIL, u.FULLNAME, u.USERNAME, u.BRANCH_CODE
                FROM TRANSFER t
                LEFT JOIN AM_USERS_LOCAL u ON t.CREATED_BY = u.ID
                WHERE t.ID_TRANSFER = :transfer_id
            """, {'transfer_id': int(transfer_id)})
            transfer_row = cursor.fetchone()

            if not transfer_row:
                return Response({'error': 'Transfert non trouvé'}, status=404)

            plafond = transfer_row[0] or 0
            current_approval_level = transfer_row[1] or 0
            ref_fac = transfer_row[2]
            created_by_id = transfer_row[3]
            creator_email = transfer_row[4]  # Peut être None
            creator_name = transfer_row[5] if transfer_row[5] else (transfer_row[6] if transfer_row[6] else "Utilisateur")
            creator_branch = transfer_row[7]  # Agence du créateur

            # Si l'email du créateur n'est pas disponible, chercher un administrateur ou responsable
            if not creator_email:
                print("Email du créateur non trouvé, recherche d'un administrateur...")

                # Chercher un utilisateur avec un rôle spécifique (par exemple POID = 99 pour les admins)
                cursor.execute("""
                    SELECT EMAIL, FULLNAME, USERNAME
                    FROM AM_USERS_LOCAL
                    WHERE POID = 99 AND BRANCH_CODE = :branch_code
                    AND ROWNUM = 1
                """, {'branch_code': creator_branch})

                admin_row = cursor.fetchone()
                if admin_row:
                    creator_email = admin_row[0]
                    creator_name = admin_row[1] if admin_row[1] else admin_row[2]
                    print(f"Administrateur trouvé: {creator_email}")
                else:
                    # Si aucun admin n'est trouvé, chercher n'importe quel utilisateur de la même agence
                    cursor.execute("""
                        SELECT EMAIL, FULLNAME, USERNAME
                        FROM AM_USERS_LOCAL
                        WHERE BRANCH_CODE = :branch_code AND EMAIL IS NOT NULL
                        AND ROWNUM = 1
                    """, {'branch_code': creator_branch})

                    user_row = cursor.fetchone()
                    if user_row:
                        creator_email = user_row[0]
                        creator_name = user_row[1] if user_row[1] else user_row[2]
                        print(f"Utilisateur de l'agence trouvé: {creator_email}")
                    else:
                        print("Aucun utilisateur trouvé pour notifier")

            # Calculer le nouveau plafond selon la logique spécifique
            new_plafond = 0
            if plafond == 4:
                new_plafond = 0
            elif plafond == 16:
                new_plafond = 4
            elif poid == 36:
                new_plafond = 16
            elif plafond == 72:
                new_plafond = 36
            elif plafond == 128:
                new_plafond = 72
            elif plafond == 220:
                new_plafond = 128
            else:
                new_plafond = plafond - poid

            # Décrémenter le niveau d'approbation (mais pas en dessous de 1)
            new_approval_level = max(0, current_approval_level - 1)

            # Le statut reste toujours EN_ATTENTE pour un rejet
            status = 'EN_ATTENTE'

            # Mettre à jour le transfert (on modifie le plafond cette fois)
            cursor.execute("""
                UPDATE TRANSFER
                SET observation = :observation,
                    current_approval_level = :new_approval_level,
                    status = :status,
                    PLAFOND = :new_plafond
                WHERE ID_TRANSFER = :transfer_id
            """, {
                'observation': observation,
                'new_approval_level': new_approval_level,
                'status': status,
                'new_plafond': new_plafond,
                'transfer_id': int(transfer_id)
            })

            # Insertion dans l'historique pour le rejet
            cursor.execute(
                """
                INSERT INTO HISTORIQUE_TRANSFER
                (TRANSFER_ID, USER_ID, ACTION_TYPE, OBSERVATION, PLAFOND, CURRENT_APPROVAL_LEVEL, STATUS)
                VALUES (:transfer_id, :user_id, :action_type, :observation, :plafond, :current_approval_level, :status)
                """,
                {
                    'transfer_id': int(transfer_id),
                    'user_id': int(user_id),
                    'action_type': 'REJET',
                    'observation': observation,
                    'plafond': new_plafond,
                    'current_approval_level': new_approval_level,
                    'status': status
                }
            )

            # Envoyer un email de notification si un destinataire a été trouvé
            if creator_email:
                try:
                    print(f"Tentative d'envoi d'email à: {creator_email}")
                    send_rejection_email(
                        creator_email=creator_email,
                        ref_fac=ref_fac,
                        creator_name=creator_name,
                        rejecter_name=rejecter_name,
                        observation=observation
                    )
                    print(f"Email de rejet envoyé à: {creator_email}")
                except Exception as email_error:
                    print(f"Erreur lors de l'envoi de l'email de rejet: {str(email_error)}")
                    import traceback
                    traceback.print_exc()
            else:
                print("Aucun email de destinataire trouvé, impossible d'envoyer la notification")

            connection.commit()

        return Response({
            'success': True,
            'transfer_id': transfer_id,
            'new_plafond': new_plafond,
            'current_approval_level': new_approval_level,
            'status': status,
            'was_previously_approved': existing_approval_count > 0
        })
    except Exception as e:
        print(f"Erreur générale dans reject_transfer: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)

# Fonction pour envoyer l'email de notification de rejet
def send_rejection_email(creator_email, ref_fac, creator_name, rejecter_name, observation):
    subject = f"Transfert rejeté - Référence {ref_fac}"
    message = (
        f"Bonjour {creator_name},\n\n"
        f"Votre transfert portant la référence {ref_fac} a été rejeté par {rejecter_name}.\n"
        f"Observation: {observation}\n\n"
        f"Merci de vous connecter à la plateforme pour plus de détails.\n\n"
        f"Cordialement,\n"
    )

    # Afficher le contenu de l'email pour le débogage
    print(f"Contenu de l'email:\nSujet: {subject}\nMessage: {message}")

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[creator_email],
        fail_silently=False,
    )




# fin function par medos
@api_view(['GET'])
def get_all_historique(request):
    with connection.cursor() as cursor:
        # Get all transfer IDs
        cursor.execute("SELECT ID_TRANSFER FROM TRANSFER")
        transfer_ids = [row[0] for row in cursor.fetchall()]

    result = []
    for transfer_id in transfer_ids:
        with connection.cursor() as cursor:
            # Get transfer details
            cursor.execute("SELECT * FROM TRANSFER WHERE ID_TRANSFER = :transfer_id", {'transfer_id': int(transfer_id)})
            transfer_row = cursor.fetchone()
            transfer_columns = [col[0].lower() for col in cursor.description]
            transfer_data = dict(zip(transfer_columns, transfer_row)) if transfer_row else None
            # Convert LOBs in transfer_data
            if transfer_data:
                for key, value in transfer_data.items():
                    if hasattr(value, 'read'):
                        try:
                            transfer_data[key] = value.read().decode('utf-8')
                        except Exception:
                            transfer_data[key] = None
                    elif str(type(value)).endswith("LOB'>"):
                        try:
                            transfer_data[key] = str(value)
                        except Exception:
                            transfer_data[key] = None
            # Get parcours/history with user details
            cursor.execute("""
                SELECT h.USER_ID, u.USERNAME, u.FULLNAME, h.ACTION_DATE, h.ACTION_TYPE, h.OBSERVATION, h.CURRENT_APPROVAL_LEVEL, h.STATUS
                FROM HISTORIQUE_TRANSFER h
                LEFT JOIN AM_USERS_LOCAL u ON h.USER_ID = u.ID
                WHERE h.TRANSFER_ID = :transfer_id
                ORDER BY h.ACTION_DATE ASC
            """, {'transfer_id': int(transfer_id)})
            columns = [col[0].lower() for col in cursor.description]
            parcours = []
            etape = 1
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                # Convert LOBs in parcours
                for key, value in row_dict.items():
                    if hasattr(value, 'read'):
                        try:
                            row_dict[key] = value.read().decode('utf-8')
                        except Exception:
                            row_dict[key] = None
                    elif str(type(value)).endswith("LOB'>"):
                        try:
                            row_dict[key] = str(value)
                        except Exception:
                            row_dict[key] = None
                parcours.append({
                    "etape": etape,
                    "utilisateur_id": row_dict['user_id'],
                    "username": row_dict.get('username'),
                    "fullname": row_dict.get('fullname'),
                    "action": row_dict['action_type'],
                    "date": row_dict['action_date'],
                    "niveau": row_dict['current_approval_level'],
                    "statut": row_dict['status'],
                    "observation": row_dict['observation'],
                })
                etape += 1
        result.append({
            "transfer_id": transfer_id,
            "details": transfer_data,
            "parcours": parcours
        })
    return Response(result)

@api_view(['GET'])
def get_historique_by_transfer(request, transfer_id):
    with connection.cursor() as cursor:
        # 1. Get transfer details
        cursor.execute("""
            SELECT * FROM TRANSFER WHERE ID_TRANSFER = :transfer_id
        """, {'transfer_id': int(transfer_id)})
        transfer_row = cursor.fetchone()
        transfer_columns = [col[0].lower() for col in cursor.description]
        transfer_data = dict(zip(transfer_columns, transfer_row)) if transfer_row else None

        # 2. Get parcours/history with user details
        cursor.execute("""
            SELECT h.USER_ID, u.USERNAME, u.FULLNAME, h.ACTION_DATE, h.ACTION_TYPE, h.OBSERVATION, h.CURRENT_APPROVAL_LEVEL, h.STATUS
            FROM HISTORIQUE_TRANSFER h
            LEFT JOIN AM_USERS_LOCAL u ON h.USER_ID = u.ID
            WHERE h.TRANSFER_ID = :transfer_id
            ORDER BY h.ACTION_DATE ASC
        """, {'transfer_id': int(transfer_id)})
        columns = [col[0].lower() for col in cursor.description]
        parcours = []
        etape = 1
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            parcours.append({
                "etape": etape,
                "utilisateur_id": row_dict['user_id'],
                "username": row_dict.get('username'),
                "fullname": row_dict.get('fullname'),
                "action": row_dict['action_type'],
                "date": row_dict['action_date'],
                "niveau": row_dict['current_approval_level'],
                "statut": row_dict['status'],
                "observation": row_dict['observation'],
            })
            etape += 1

    # Convert LOBs in transfer_data
    if transfer_data:
        for key, value in transfer_data.items():
            if hasattr(value, 'read'):  # BLOB
                try:
                    transfer_data[key] = value.read().decode('utf-8')
                except Exception:
                    transfer_data[key] = None
            elif str(type(value)).endswith("LOB'>"):
                try:
                    transfer_data[key] = str(value)
                except Exception:
                    transfer_data[key] = None
    # Convert LOBs in parcours
    for step in parcours:
        for key, value in step.items():
            if hasattr(value, 'read'):
                try:
                    step[key] = value.read().decode('utf-8')
                except Exception:
                    step[key] = None
            elif str(type(value)).endswith("LOB'>"):
                try:
                    step[key] = str(value)
                except Exception:
                    step[key] = None

    remonteur_username = None
    remonteur_fullname = None
    # Find the last user who is not the creator
    for step in reversed(parcours):
        if step.get('action') and step['action'].upper() != 'CREATION':
            remonteur_username = step.get('username')
            remonteur_fullname = step.get('fullname')
            break

    return Response({
        "transfer": transfer_data,
        "niveau_actuel": transfer_data.get('current_approval_level') if transfer_data else None,
        "statut_actuel": transfer_data.get('status') if transfer_data else None,
        "parcours": parcours,
        "remonteur_username": remonteur_username,
        "remonteur_fullname": remonteur_fullname
    })



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

class ClientPhysiqueView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            # Récupérer les paramètres de requête
            params = request.query_params
            client = params.get('client')
            nom = params.get('nom')
            prenom = params.get('prenom')
            
            # Construire la requête SQL de base
            query = "SELECT * FROM CLIENT_PHYSIQUE WHERE 1=1"
            query_params = {}
            
            # Ajouter les filtres selon les paramètres fournis
            if client:
                query += " AND client = :client"
                query_params['client'] = client
            if nom:
                query += " AND UPPER(NOM) LIKE UPPER(:nom)"
                query_params['nom'] = f'%{nom}%'
            if prenom:
                query += " AND UPPER(PRENOM) LIKE UPPER(:prenom)"
                query_params['prenom'] = f'%{prenom}%'
            
            with connection.cursor() as cursor:
                cursor.execute(query, query_params)
                columns = [col[0].lower() for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClientMoralView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            # Récupérer les paramètres de requête
            params = request.query_params
            client = params.get('client')
            raison_sociale = params.get('raison_sociale')
            nom_representant = params.get('nom_representant')
            
            # Construire la requête SQL de base
            query = "SELECT * FROM CLIENT_MORAL WHERE 1=1"
            query_params = {}
            
            # Ajouter les filtres selon les paramètres fournis
            if client:
                query += " AND client = :client"
                query_params['client'] = client
            if raison_sociale:
                query += " AND UPPER(RAISON_SOCIALE) LIKE UPPER(:raison_sociale)"
                query_params['raison_sociale'] = f'%{raison_sociale}%'
            if nom_representant:
                query += " AND UPPER(NOM_REPRESENTANT) LIKE UPPER(:nom_representant)"
                query_params['nom_representant'] = f'%{nom_representant}%'
            
            with connection.cursor() as cursor:
                cursor.execute(query, query_params)
                columns = [col[0].lower() for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def transfer_by_user_and_id(request, user_id, transfer_id):
    try:
        transfer = Transfer.objects.get(pk=transfer_id, created_by_id=user_id)
    except Transfer.DoesNotExist:
        return Response({'error': 'Aucun transfert trouvé pour cet utilisateur et cet ID.'}, status=404)
    transfer_data = TransferSerializer(transfer).data
    transfer_data['niveau_creation'] = 1
    return Response(transfer_data)



# transfer status 
class TransferStatsAPI(APIView):
    def get(self, request, *args, **kwargs):
        try:
            # Récupérer les paramètres de requête optionnels
            params = request.query_params
            status_filter = params.get('status')
            date_from = params.get('date_from')
            date_to = params.get('date_to')
            
            # Construire la requête SQL de base
            query = """
            SELECT 
                (SELECT COUNT(*) FROM TRANSFER) AS total_transfers,
                status,
                COUNT(*) AS status_count
            FROM TRANSFER
            WHERE 1=1
            """
            
            query_params = {}
            
            # Ajouter les filtres optionnels
            if status_filter:
                query += " AND status = :status"
                query_params['status'] = status_filter
                
            if date_from:
                query += " AND transfer_date >= :date_from"
                query_params['date_from'] = date_from
                
            if date_to:
                query += " AND transfer_date <= :date_to"
                query_params['date_to'] = date_to
            
            # Ajouter le GROUP BY
            query += " GROUP BY status"
            
            # Exécuter la requête
            with connection.cursor() as cursor:
                cursor.execute(query, query_params)
                columns = [col[0].lower() for col in cursor.description]
                rows = cursor.fetchall()

            # Formater les résultats
            result = [dict(zip(columns, row)) for row in rows]
            
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  


###### ---- evaluation transfer status ---- ######


class TransferStatisticsView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            query = """
            WITH 
            daily_stats AS (
                SELECT 
                    TRUNC(CREATION_DATE) AS day,
                    COUNT(*) AS daily_count
                FROM TRANSFER
                GROUP BY TRUNC(CREATION_DATE)
            ),
            monthly_stats AS (
                SELECT 
                    TO_CHAR(CREATION_DATE, 'YYYY-MM') AS month,
                    COUNT(*) AS monthly_count
                FROM TRANSFER
                GROUP BY TO_CHAR(CREATION_DATE, 'YYYY-MM')
            ),
            yearly_stats AS (
                SELECT 
                    EXTRACT(YEAR FROM CREATION_DATE) AS year,
                    COUNT(*) AS yearly_count
                FROM TRANSFER
                GROUP BY EXTRACT(YEAR FROM CREATION_DATE)
            )

            SELECT 
                'daily' AS period_type,
                TO_CHAR(day, 'YYYY-MM-DD') AS period_value,
                daily_count AS transfer_count,
                1 AS sort_order
            FROM daily_stats

            UNION ALL

            SELECT 
                'monthly' AS period_type,
                month AS period_value,
                monthly_count AS transfer_count,
                2 AS sort_order
            FROM monthly_stats

            UNION ALL

            SELECT 
                'yearly' AS period_type,
                TO_CHAR(year) AS period_value,
                yearly_count AS transfer_count,
                3 AS sort_order
            FROM yearly_stats

            UNION ALL

            SELECT 
                'total' AS period_type,
                NULL AS period_value,
                COUNT(*) AS transfer_count,
                4 AS sort_order
            FROM TRANSFER

            ORDER BY 
                sort_order,
                period_value
            """
            
            with connection.cursor() as cursor:
                cursor.execute(query)
                columns = [col[0].lower() for col in cursor.description]
                rows = cursor.fetchall()

            # Retirer sort_order du résultat final
            result = [dict(zip(columns[:-1], row[:-1])) for row in rows]
            
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)                  



#--------- AFFECTER UN DROIT ------------------

class UpdateConsulteAPI(APIView):
    def put(self, request):
        username = request.data.get('username')
        consulte = request.data.get('consulte')

        if not username or consulte is None:
            return Response(
                {"error": "Les champs 'username' et 'consulte' sont obligatoires"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Requête SQL brute
            with connection.cursor() as cursor:
                query = """
                UPDATE AM_USERS_LOCAL
                SET CONSULTE = %s
                WHERE USERNAME = %s
                """
                cursor.execute(query, [consulte, username])

                # Vérifier si une ligne a été mise à jour
                if cursor.rowcount == 0:
                    return Response(
                        {"error": f"Utilisateur {username} non trouvé"},
                        status=status.HTTP_404_NOT_FOUND
                    )

            return Response(
                {"status": "success", "message": f"CONSULTE mis à jour pour {username}"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": f"Erreur SQL : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )