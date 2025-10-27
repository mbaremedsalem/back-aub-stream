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


@api_view(['POST'])
def create_transfer(request):
    try:
        data = request.POST.dict()
        files = request.FILES.get('files')

        # Validation des champs obligatoires (status supprimé)
        required_fields = [
            'nom_chargeur', 'montant_en_lettre', 'devise', 'montant_chiffre',
            'frais_MRU', 'frais_etranger',
            'nom_beneficiaire', 'adresse_beneficiaire', 'iban_beneficiaire',
            'nom_banque_beneficiaire', 'code_swift_banque_beneficiaire',
            'created_by_id', 'id_client', 'type_client','code_swift_banque_intermediaire','nom_banque_intermediaire'
        ]
        for field in required_fields:
            if field not in data:
                return Response({'error': f'Champ {field} manquant'}, status=400)
        # Valeur par défaut pour status si non fourni
        status_value = data.get('status', 'EN_ATTENTE')

        # Vérification que l'utilisateur existe et récupération du POID
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT POID FROM AM_USERS_LOCAL WHERE ID = :user_id",
                {'user_id': int(data['created_by_id'])}
            )
            user_row = cursor.fetchone()
            if not user_row:
                return Response({'error': 'Utilisateur non trouvé'}, status=404)
            poid = user_row[0]

        # Gestion du fichier
        file_path = None
        if files:
            fs = FileSystemStorage(location='media/Transfer')
            filename = f"transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{files.name}"
            saved_file = fs.save(filename, files)
            file_path = f"Transfer/{saved_file}"
        else:
            file_path = data.get('file_path', None)

        # Construction de la requête SQL (current_approval_level fixé à 1)
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO TRANSFER (
                    DATE_ORDRE,
                    NOM_CHARGEUR,
                    MONTANT_EN_LETTRE,
                    DEVISE,
                    MONTANT_CHIFFRE,
                    FRAIS_MRU,
                    FRAIS_ETRANGER,
                    PLAFOND,
                    CURRENT_APPROVAL_LEVEL,
                    OBSERVATION,
                    STATUS,
                    NOM_BENEFICIAIRE,
                    ADRESSE_BENEFICIAIRE,
                    IBAN_BENEFICIAIRE,
                    NOM_BANQUE_BENEFICIAIRE,
                    NOM_BANQUE_INTERMEDIAIRE,
                    CODE_SWIFT_BANQUE_BENEFICIAIRE,
                    CODE_SWIFT_BANQUE_INTERMEDIAIRE,
                    CREATED_BY,
                    FILES,
                    ID_CLIENT,
                    TYPE_CLIENT
                ) VALUES (
                    SYSDATE,
                    :nom_chargeur,
                    :montant_en_lettre,
                    :devise,
                    :montant_chiffre,
                    :frais_MRU,
                    :frais_etranger,
                    :plafond,
                    1,
                    :observation,
                    :status,
                    :nom_beneficiaire,
                    :nom_banque_intermediaire,
                    :adresse_beneficiaire,
                    :iban_beneficiaire,
                    :nom_banque_beneficiaire,
                    :code_swift_banque_beneficiaire,
                    :code_swift_banque_intermediaire,
                    :created_by_id,
                    :file_path,
                    :id_client,
                    :type_client
                )
                RETURNING ID_TRANSFER INTO :transfer_id
            """
            transfer_id_var = cursor.var(int)
            params = {
                'nom_chargeur': data['nom_chargeur'],
                'montant_en_lettre': data['montant_en_lettre'],
                'devise': data['devise'],
                'montant_chiffre': float(data['montant_chiffre']),
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
                'created_by_id': int(data['created_by_id']),
                'file_path': file_path,
                'id_client': int(data['id_client']),
                'type_client': data['type_client'],
                'transfer_id': transfer_id_var
            }
            cursor.execute(sql, params)
            transfer_id = transfer_id_var.getvalue()

            # Insertion dans l'historique (valeurs fixes)
            cursor.execute(
                """
                INSERT INTO HISTORIQUE_TRANSFER
                (TRANSFER_ID, USER_ID, ACTION_TYPE, OBSERVATION, PLAFOND, CURRENT_APPROVAL_LEVEL, STATUS)
                VALUES (:transfer_id, :user_id, :action_type, '', :plafond, 1, 'EN_ATTENTE')
                """,
                {
                    'transfer_id': transfer_id[0] if transfer_id else None,
                    'user_id': int(data['created_by_id']),
                    'action_type': 'CREATION',
                    'plafond': poid
                }
            )

        return Response({
            'success': True,
            'transfer_id': transfer_id[0] if transfer_id else None,
            'created_by_id': data['created_by_id'],
            'file_path': file_path,
            'message': 'Transfert créé avec succès'
        }, status=201)

    except Exception as e:
        if 'file_path' in locals() and file_path:
            try:
                fs = FileSystemStorage()
                fs.delete(file_path)
            except:
                pass
        return Response({
            'error': 'Erreur lors de la création',
            'details': str(e),
            'type': type(e).__name__
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


@api_view(['POST'])
@csrf_exempt
def approve_transfer(request, transfer_id):
    """
    Ajoute le POID de l'utilisateur au plafond du transfert, ajoute une observation,
    incrémente current_approval_level, et met à jour le status selon la logique métier.
    """
    try:
        user_id = request.data.get('user_id')
        observation = request.data.get('observation', '')
        if not user_id:
            return Response({'error': 'user_id requis'}, status=400)
        with connection.cursor() as cursor:
            # Récupérer le POID de l'utilisateur
            cursor.execute("SELECT POID FROM AM_USERS_LOCAL WHERE ID = :user_id", {'user_id': int(user_id)})
            user_row = cursor.fetchone()
            if not user_row:
                return Response({'error': 'Utilisateur non trouvé'}, status=404)
            poid = user_row[0]
            # Récupérer plafond et current_approval_level actuels du transfert
            cursor.execute("SELECT PLAFOND, CURRENT_APPROVAL_LEVEL FROM TRANSFER WHERE ID_TRANSFER = :transfer_id", {'transfer_id': int(transfer_id)})
            plafond_row = cursor.fetchone()
            if not plafond_row:
                return Response({'error': 'Transfert non trouvé'}, status=404)
            plafond = plafond_row[0] or 0
            current_approval_level = plafond_row[1] or 0
            # Ajouter le poid, sans dépasser 72
            new_plafond = plafond + poid
            if new_plafond > 72:
                new_plafond = 72
            # Incrémenter le niveau d'approbation
            new_approval_level = current_approval_level + 1
            # Déterminer le statut
            if new_plafond == 72:
                status = 'VALIDE'
            else:
                status = 'EN_ATTENTE'
            # Mettre à jour le transfert
            cursor.execute("""
                UPDATE TRANSFER SET PLAFOND = :new_plafond, observation = :observation, current_approval_level = :new_approval_level, status = :status WHERE ID_TRANSFER = :transfer_id
            """, {
                'new_plafond': new_plafond,
                'observation': observation,
                'new_approval_level': new_approval_level,
                'status': status,
                'transfer_id': int(transfer_id)
            })

            # Insertion dans l'historique pour l'approbation
            cursor.execute(
                """
                INSERT INTO HISTORIQUE_TRANSFER
                (TRANSFER_ID, USER_ID, ACTION_TYPE, OBSERVATION, PLAFOND, CURRENT_APPROVAL_LEVEL, STATUS)
                VALUES (:transfer_id, :user_id, :action_type, :observation, :plafond, :current_approval_level, :status)
                """,
                {
                    'transfer_id': int(transfer_id),
                    'user_id': int(user_id),
                    'action_type': 'APPROBATION',
                    'observation': observation,
                    'plafond': new_plafond,
                    'current_approval_level': new_approval_level,
                    'status': status
                }
            )
            # Commit explicite pour garantir l'insertion
            connection.commit()
        
        return Response({
            'success': True,
            'transfer_id': transfer_id,
            'new_plafond': new_plafond,
            'current_approval_level': new_approval_level,
            'status': status
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

# fait par medos ici 
#   ---------------------    1 er choix -----
# @api_view(['POST'])
# @csrf_exempt
# def reject_transfer(request, transfer_id):
#     """
#     Rejette le transfert en décrémentant le current_approval_level et garde le statut EN_ATTENTE.
#     Ajoute une observation dans l'historique.
#     """
#     try:
#         user_id = request.data.get('user_id')
#         observation = request.data.get('observation', '')
#         if not user_id:
#             return Response({'error': 'user_id requis'}, status=400)
        
#         with connection.cursor() as cursor:
#             # Récupérer les informations actuelles du transfert
#             cursor.execute("""
#                 SELECT PLAFOND, CURRENT_APPROVAL_LEVEL 
#                 FROM TRANSFER 
#                 WHERE ID_TRANSFER = :transfer_id
#             """, {'transfer_id': int(transfer_id)})
#             transfer_row = cursor.fetchone()
            
#             if not transfer_row:
#                 return Response({'error': 'Transfert non trouvé'}, status=404)
                
#             plafond = transfer_row[0] or 0
#             current_approval_level = transfer_row[1] or 0
            
#             # Décrémenter le niveau d'approbation (mais pas en dessous de 1)
#             new_approval_level = max(1, current_approval_level - 1)
            
#             # Le statut reste toujours EN_ATTENTE pour un rejet
#             status = 'EN_ATTENTE'
            
#             # Mettre à jour le transfert (on ne modifie pas le plafond)
#             cursor.execute("""
#                 UPDATE TRANSFER 
#                 SET observation = :observation, 
#                     current_approval_level = :new_approval_level, 
#                     status = :status 
#                 WHERE ID_TRANSFER = :transfer_id
#             """, {
#                 'observation': observation,
#                 'new_approval_level': new_approval_level,
#                 'status': status,
#                 'transfer_id': int(transfer_id)
#             })

#             # Insertion dans l'historique pour le rejet
#             cursor.execute(
#                 """
#                 INSERT INTO HISTORIQUE_TRANSFER
#                 (TRANSFER_ID, USER_ID, ACTION_TYPE, OBSERVATION, PLAFOND, CURRENT_APPROVAL_LEVEL, STATUS)
#                 VALUES (:transfer_id, :user_id, :action_type, :observation, :plafond, :current_approval_level, :status)
#                 """,
#                 {
#                     'transfer_id': int(transfer_id),
#                     'user_id': int(user_id),
#                     'action_type': 'REJET',
#                     'observation': observation,
#                     'plafond': plafond,  # On garde le plafond actuel
#                     'current_approval_level': new_approval_level,
#                     'status': status
#                 }
#             )
#             connection.commit()
        
#         return Response({
#             'success': True,
#             'transfer_id': transfer_id,
#             'current_approval_level': new_approval_level,
#             'status': status
#         })
#     except Exception as e:
#         return Response({'error': str(e)}, status=500)


#-------------------------- 2nd choix : -------

@api_view(['POST'])
@csrf_exempt
def reject_transfer(request, transfer_id):
    """
    Rejette le transfert en décrémentant le current_approval_level et en soustrayant le POID de l'utilisateur du plafond.
    Ajoute une observation dans l'historique.
    """
    try:
        user_id = request.data.get('user_id')
        observation = request.data.get('observation', '')
        if not user_id:
            return Response({'error': 'user_id requis'}, status=400)
        
        with connection.cursor() as cursor:
            # Récupérer le POID de l'utilisateur
            cursor.execute("SELECT POID FROM AM_USERS_LOCAL WHERE ID = :user_id", {'user_id': int(user_id)})
            user_row = cursor.fetchone()
            if not user_row:
                return Response({'error': 'Utilisateur non trouvé'}, status=404)
            poid = user_row[0]
            print("poit ici ",poid)
            
            # Récupérer les informations actuelles du transfert
            cursor.execute("""
                SELECT PLAFOND, CURRENT_APPROVAL_LEVEL 
                FROM TRANSFER 
                WHERE ID_TRANSFER = :transfer_id
            """, {'transfer_id': int(transfer_id)})
            transfer_row = cursor.fetchone()
            
            if not transfer_row:
                return Response({'error': 'Transfert non trouvé'}, status=404)
                
       
            plafond = transfer_row[0] or 0
            print("plafond : ", plafond)
            current_approval_level = transfer_row[1] or 0
            
            # Soustraire le poid, sans descendre en dessous de 4 (valeur initiale)
            # new_plafond = max(4, plafond - poid)
            new_plafond = 0
            if(poid == 36):
                new_plafond = 16
            
            elif poid== 12:
                new_plafond = 0

            else:
                new_plafond = poid - plafond
            
            
            # Décrémenter le niveau d'approbation (mais pas en dessous de 1)
            new_approval_level = max(1, current_approval_level - 1)
            
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
                    'plafond': new_plafond,  # On utilise le nouveau plafond
                    'current_approval_level': new_approval_level,
                    'status': status
                }
            )
            connection.commit()
        
        return Response({
            'success': True,
            'transfer_id': transfer_id,
            'new_plafond': new_plafond,
            'current_approval_level': new_approval_level,
            'status': status
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


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