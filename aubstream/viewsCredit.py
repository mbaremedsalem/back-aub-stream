from django.shortcuts import render
from .models import *
from .serializersCredit import *
from .filters import *
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view ,permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# from account.authenticated_validateur import *
# from account.authenticated_createur import *
from rest_framework.exceptions import ValidationError
from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.db.models import Count
from .email import send_validation_email
# import qrcode # type: ignore
from io import BytesIO
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from django.http import HttpResponse


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# -------------------------- lautorization -------------------------------
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

# --------------------------GET CLIENT INFORMATION 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection


#--------------- views.py ----------------
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, F
from .models import Credit
from datetime import timedelta

from django.db.models import OuterRef, Subquery, ExpressionWrapper, F, DurationField, Avg, Count, Sum
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import timedelta

class CreateDemandeAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        try:
            user_id = request.data.get('user_id')
            agnece = request.data.get('agnece')
            type_credit = request.data.get('type_credit')
            nature_credit = request.data.get('nature_credit')
            type_dossier = request.data.get('type_dossier')

            if not user_id:
                return Response({"error": "user_id est requis."}, status=400)
            elif not agnece:
                return Response({"error": "agence est requis."}, status=400)
            elif not type_credit:
                return Response({"error": "Type Crédit est requis."}, status=400)
            elif not type_dossier:
                return Response({"error": "Type Dossier est requis."}, status=400)
            elif not nature_credit:
                return Response({"error": "Nature Credit est requis."}, status=400)
            try:
                user = AmUsers.objects.get(id=user_id, agnece=agnece)
                
            except AmUsers.DoesNotExist:
                return Response({"error": "Utilisateur non trouvé."}, status=404)

            client_code = request.data.get('CLIENT')
            if not client_code:
                return Response({"error": "Le champ CLIENT (code client) est requis."}, status=400)

            # 🔍 Vérifier si le client existe déjà
            client_exist = Client.objects.filter(client_code=client_code).first()
            if client_exist:
                # 🔍 Vérifier s'il a au moins un crédit non rejeté
                non_rejete_exist = client_exist.credits.exclude(status='REJETÉ').exists()
                if non_rejete_exist:
                    return Response(
                        {"error": "Une demande pour ce client existe déjà et n'est pas rejetée."},
                        status=400
                    )
                else:
                    client = client_exist
            else:
                # 🔹 Création du client
                print("adress : ", request.data.get('Address'))
                client = Client.objects.create(
                    client_code=client_code,
                    identifiant=request.data.get('IDENTIFIENT'),
                    pays_naissance=request.data.get('PAYSNAIS'),
                    date_naissance=(request.data.get('DATNAIS')),

                    nom=request.data.get('NOM'),
                    prenom=request.data.get('PRENOM'),
                    tel=request.data.get('TEL'),
                    sexe=request.data.get('SEXE'),
                    type_document=request.data.get('TYPE_DOCUMENT'),

                    date_expiration=request.data.get('DATE_EXPIRATION'),
                    nni=request.data.get('NNI'),
                    date_creation=request.data.get('DATE_CREATION'),
                    agence=request.data.get('AGENCE'),
                    type_client=request.data.get('TYPE_CLIENT'),

                    NIF=request.data.get('NIF'),
                    Address=request.data.get('Address'),   
                )

            # 🔹 Création du crédit
            credit = Credit.objects.create(
                client=client,
                montant=request.data.get('montant'),
                duree=request.data.get('duree'),
                avis=request.data.get('avis'),
                memo=request.data.get('memo'),
                agence=request.data.get('agnece'),
                type_credit=request.data.get('type_credit'),
                type_dossier=request.data.get('type_dossier'),
                nature_credit=request.data.get('nature_credit'),
                
                
            )

            # 🔹 Upload des documents
            # for f in request.FILES.getlist('documents'):
            #     Document.objects.create(credit=credit, fichier=f)
            # document_types = request.data.getlist('document_types')
            # for idx, f in enumerate(request.FILES.getlist('documents')):
            #     type_doc = document_types[idx] if idx < len(document_types) else "Inconnu"
            #     Document.objects.create(credit=credit, fichier=f, type_document=type_doc)


            documents = request.FILES.getlist('documents[]') or request.FILES.getlist('documents')
            types = request.POST.getlist('type_document[]') or request.POST.getlist('type_document')
            
            print("document : ", documents)
            print("types : ", types)

            for i in range(len(documents)):
                doc = documents[i]
                doc_type = types[i] if i < len(types) else 'Non spécifié'
                Document.objects.using('sqlite').create(
                    credit=credit,
                    fichier=doc,
                    type_document=doc_type,
                    createur=user
                )
            # 🔹 Attribution de points si c’est le bon poste
            poste = user.post
            points = POSTE_POINTS.get(poste, 0)

            if poste == "Chargé de clientèle":
                credit.points_valides += points
                credit.save()

                ValidationCredit.objects.create(
                    credit=credit,
                    validateur=user,
                    points=points,
                    poste=poste, 
                    motiv=request.data.get('avis'),
                    memo=request.data.get('memo'),
                    date_creation=timezone.now(),
                    status="Créé"
                )
            ag = request.data.get('agnece')
            print ( " agence :  ",ag)
            validateurs_suivants = AmUsers.objects.using('sqlite').filter(poit=4 , is_active=True, agnece=request.data.get('agnece'))
            print("validateurs_suivants : ", validateurs_suivants)
            for validateur in validateurs_suivants:
            # send_validation_email(validateur.email, credit.reference)
                send_validation_email(validateur.email, credit.reference, validateur)
            # Facultatif : ajouter aussi une notification en base
            # Notification.objects.using('sqlite').create(
            #     user=validateur,
            #     message=f"Vous avez une nouvelle demande de validation pour le crédit {credit.reference}"
            # )
            Notification.objects.using('sqlite').create(
                user=validateur,
                message=(
                    f"Bonjour {validateur.post} ({validateur.nom} {validateur.prenom}),\n\n"
                    f"Vous avez une nouvelle demande de validation pour le crédit {credit.reference}.\n"
                    f"Cordialement."
                ),
                objet=f"Nouvelle demande de validation - Crédit {credit.reference}"
            )
                
        #           ValidationCredit.objects.using('sqlite').create(
        #     credit=credit,
        #     validateur=user,
        #     points=points,
        #     poste=poste,
        #     motiv=motiv,
        #     memo=memo,
            
        # )

            return Response({"message": "Demande créée avec succès."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.utils import timezone

  # assure-toi d’avoir ce mapping
import uuid


class UpdateDemandeAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request, credit_id, *args, **kwargs):
        try:
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({"error": "user_id est requis."}, status=400)

            

            try:
                credit = Credit.objects.using('sqlite').get(id=credit_id)
            except Credit.DoesNotExist:
                return Response({"error": "Crédit non trouvé."}, status=404)

            credit.montant = request.data.get('montant', credit.montant)
            credit.duree = request.data.get('duree', credit.duree)
            credit.avis = request.data.get('avis', credit.avis)
            credit.memo = request.data.get('memo', credit.memo)
            credit.agence = request.data.get('agnece', credit.agence)
            credit.type_credit = request.data.get('type_credit', credit.type_credit)
            credit.type_dossier = request.data.get('type_dossier', credit.type_dossier)

            user = NewUser.objects.using('sqlite').get(id=user_id)
            poste = user.post
            credit.points_valides =2
            credit.save()

            ValidationCredit.objects.using('sqlite').create(
                    credit=credit,
                    validateur=user,
                    points=2,
                    poste=poste,
                    motiv=request.data.get('avis', credit.avis),
                    memo=request.data.get('memo', credit.memo),
                    date_validation=timezone.now(),
                    status="Validé"
             )
            
            credit.save()
            validateurs_suivants = NewUser.objects.using('sqlite').filter(poit=4 , is_active=True, agnece=credit.agence)
            for validateur in validateurs_suivants:
                send_validation_email(validateur.email, credit.reference, validateur)
           
            Notification.objects.using('sqlite').create(
                user=validateur,
                message=(
                    f"Bonjour {validateur.post} ({validateur.nom} {validateur.prenom}),\n\n"
                    f"Vous avez une nouvelle demande de validation pour le crédit {credit.reference}.\n"
                    f"Cordialement."
                ),
                objet=f"Nouvelle demande de validation - Crédit {credit.reference}"
                )
       
            documents = request.FILES.getlist('documents[]') or request.FILES.getlist('documents')
            types = request.POST.getlist('type_document[]') or request.POST.getlist('type_document')

            
            document_messages = []

            if documents:
                for i in range(len(documents)):
                    doc = documents[i]
                    doc_type = types[i] if i < len(types) else 'Non spécifié'

                    existing_doc = Document.objects.using('sqlite').filter(credit=credit, type_document=doc_type,createur=user).first()

                    if existing_doc:
                        document_messages.append({
                            "message": f"Document de type '{doc_type}' déjà existant.",
                            "type_document": doc_type,
                            "url": existing_doc.fichier.url
                        })
                    else:
                        new_doc = Document.objects.using('sqlite').create(
                        credit=credit,
                        fichier=doc,
                        type_document=doc_type,
                        createur=user
                    )
                        document_messages.append({
                        "message": f"Nouveau document de type '{doc_type}' ajouté.",
                        "type_document": doc_type,
                        "url": new_doc.fichier.url
                    })
            
            credit.save()
            
            
            return Response({
            "message": "Crédit validé et remonté.",
            "points_cumulés": credit.points_valides,
            "statut": credit.status
            }, status=200)


        except Exception as e:
            return Response({"error": str(e)}, status=400)

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import OuterRef, Subquery, Min, Count

class RepartitionPremiersValidateursView(APIView):
    def get(self, request):
        db = 'sqlite'

        # 1. Subquery pour trouver la plus petite date de validation pour chaque crédit
        first_validation_dates = ValidationCredit.objects.using(db).filter(
            credit=OuterRef('pk'),
            status__in=["Validé", "Rejeté"],
            date_validation__isnull=False
        ).order_by('date_validation')

        # 2. Annoter chaque crédit avec la date de première validation
        credits = Credit.objects.using(db).annotate(
            first_validation_date=Subquery(
                first_validation_dates.values('date_validation')[:1]
            )
        )

        # 3. Obtenir les validateurs correspondants à cette première validation
        premiers_validateurs = (
            ValidationCredit.objects.using(db)
            .filter(
                date_validation__isnull=False,
                status__in=["Validé", "Rejeté"]
            )
            .filter(
                date_validation=Subquery(
                    ValidationCredit.objects.using(db)
                    .filter(
                        credit=OuterRef('credit_id'),
                        status__in=["Validé", "Rejeté"],
                        date_validation__isnull=False
                    )
                    .order_by('date_validation')
                    .values('date_validation')[:1]
                )
            )
            .values('poste')  # ou 'validateur__username' si tu préfères par utilisateur
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return Response({
            "repartition_premiers_validateurs": list(premiers_validateurs)
        })


from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from collections import defaultdict
from django.db.models import Prefetch

from .models import Credit, ValidationCredit


# class ValidationEfficiencyAPIView(APIView):
#     # permission_classes = [IsAuthenticated]

#     def get(self, request):
#         # Structure: {poste: {validateur: [durées]}}
#         temps_validations = defaultdict(lambda: defaultdict(list))

#         # Précharger validations liées à chaque crédit
#         credits = Credit.objects.using('sqlite').prefetch_related(
#             Prefetch('validations', queryset=ValidationCredit.objects.order_by('date_validation', 'date_creation'))
#         )

#         for credit in credits:
#             validations = list(credit.validations.all())

#             for i in range(1, len(validations)):
#                 curr_val = validations[i]
#                 prev_val = validations[i - 1]

#                 if curr_val.status not in ['Validé', 'Rejeté']:
#                     continue

#                 if curr_val.date_validation and (prev_val.date_validation or prev_val.date_creation):
#                     date_prev = prev_val.date_validation or prev_val.date_creation
#                     delta = curr_val.date_validation - date_prev

#                     temps_validations[curr_val.poste][curr_val.validateur.username].append(delta.total_seconds())

#         result = []

#         for poste, validateurs,agnece in temps_validations.items():
#             for validateur, deltas in validateurs.items():
#                 moyenne = sum(deltas) / len(deltas)
#                 result.append({
#                     'poste': poste,
#                     'agnece': agnece,
#                     'validateur': validateur,
#                     'moyenne_temps_validation': moyenne,  # en secondes
#                     'nb_validations': len(deltas),
#                     'poste': poste,

#                 })

#         # Trier les validateurs du plus rapide au plus lent
#         result_sorted = sorted(result, key=lambda x: x['moyenne_temps_validation'])

#         # Ajouter le classement
#         for index, item in enumerate(result_sorted, start=1):
#             item['rang'] = index

#         return Response(result_sorted)


from collections import defaultdict
from django.db.models import Prefetch
from rest_framework.response import Response
from rest_framework.views import APIView
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.response import Response

from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.response import Response

class ValidationEfficiencyAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        temps_validations = defaultdict(lambda: defaultdict(lambda: {
            'deltas': [],
            'agnece': None,
            'nom': '',
            'prenom': '',
            'nb_rejets': 0
        }))

        credits = Credit.objects.using('sqlite').prefetch_related(
            Prefetch(
                'validations',
                queryset=ValidationCredit.objects.select_related('validateur').order_by('date_validation', 'date_creation')
            )
        )

        for credit in credits:
            validations = list(credit.validations.all())
            if not validations:
                continue

            # TRAITEMENT DU PREMIER VALIDATEUR (s'il rejette)
            first_val = validations[0]
            if first_val.status in ['Validé', 'Rejeté']:
                username = first_val.validateur.username
                poste = first_val.poste
                temps_validations[poste][username]['agnece'] = first_val.validateur.agnece
                temps_validations[poste][username]['nom'] = first_val.validateur.nom
                temps_validations[poste][username]['prenom'] = first_val.validateur.prenom

                if first_val.status == 'Rejeté':
                    temps_validations[poste][username]['nb_rejets'] += 1

            # TRAITEMENT DES VALIDATIONS RESTANTES
            for i in range(1, len(validations)):
                curr_val = validations[i]
                prev_val = validations[i - 1]

                if curr_val.status not in ['Validé', 'Rejeté']:
                    continue

                username = curr_val.validateur.username
                poste = curr_val.poste

                # Calcul du temps écoulé
                if curr_val.date_validation and (prev_val.date_validation or prev_val.date_creation):
                    date_prev = prev_val.date_validation or prev_val.date_creation
                    delta = curr_val.date_validation - date_prev
                    temps_validations[poste][username]['deltas'].append(delta.total_seconds())

                # Infos générales
                temps_validations[poste][username]['agnece'] = curr_val.validateur.agnece
                temps_validations[poste][username]['nom'] = curr_val.validateur.nom
                temps_validations[poste][username]['prenom'] = curr_val.validateur.prenom

                if curr_val.status == 'Rejeté':
                    temps_validations[poste][username]['nb_rejets'] += 1

        # Construction de la réponse
        result = []

        for poste, validateurs in temps_validations.items():
            for username, data in validateurs.items():
                deltas = data['deltas']
                moyenne = sum(deltas) / len(deltas) if deltas else 0
                result.append({
                    'poste': poste,
                    'validateur': username,
                    'agnece': data['agnece'],
                    'nom': data['nom'],
                    'prenom': data['prenom'],
                    'moyenne_temps_validation': moyenne,
                    'nb_validations': len(deltas),
                    'nb_rejete': data['nb_rejets'],
                })

        # Tri et classement
        result_sorted = sorted(result, key=lambda x: x['moyenne_temps_validation'])

        for i, item in enumerate(result_sorted, 1):
            item['rang'] = i

        return Response(result_sorted)


from django.utils.dateparse import parse_date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

class CreditListAPIView(APIView):
    def get(self, request):
        client_code = request.query_params.get('client_code')
        date_min = request.query_params.get('date_min')
        date_max = request.query_params.get('date_max')

        credits = Credit.objects.all()

        if client_code:
            credits = credits.filter(client__client_code=client_code)

        if date_min:
            date_min_parsed = parse_date(date_min.strip())
            if not date_min_parsed:
                return Response({"error": f"Format de date_min invalide : {date_min}. Utiliser YYYY-MM-DD."}, status=400)
            credits = credits.filter(date_demande__date__gte=date_min_parsed)

        if date_max:
            date_max_parsed = parse_date(date_max.strip())
            if not date_max_parsed:
                return Response({"error": f"Format de date_max invalide : {date_max}. Utiliser YYYY-MM-DD."}, status=400)
            credits = credits.filter(date_demande__date__lte=date_max_parsed)

        serializer = CreditSerializer1(credits.order_by('-date_demande'), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
   
class CreditDetailAPIView(APIView):
    def get(self, request, credit_id):
        credit = get_object_or_404(Credit.objects.using('sqlite'), pk=credit_id)
        serializer = CreditSerializer1(credit)
        return Response(serializer.data, status=status.HTTP_200_OK)

import os
from django.conf import settings
from .models import Document

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Document
import os

class DocumentDeleteAPIView(APIView):
    def delete(self, request, pk, format=None):
        try:
            document = Document.objects.using('sqlite').get(pk=pk)
            document.delete()
            return Response({"message": "Document supprimé avec succès"}, status=status.HTTP_204_NO_CONTENT)
        except Document.DoesNotExist:
            return Response({"error": "Document non trouvé"}, status=status.HTTP_404_NOT_FOUND)

# <<<<<<< HEAD
# # class ValiderCreditAPIView(APIView):
# #     def post(self, request, credit_id):
# #         user = request.user
# #         credit = get_object_or_404(Credit, id=credit_id)
# =======


# class ValiderCreditAPIView(APIView):
#     def post(self, request, credit_id):
#         user = request.user
#         credit = get_object_or_404(Credit, id=credit_id)
# >>>>>>> 0dcfb0f70ce8fc24f18cb33183d10368c967ab97

#         try:
#             valider_credit(credit, user)
#             return Response({"message": "Validation enregistrée."}, status=200)
#         except ValueError as e:
#             return Response({"error": str(e)}, status=400)


# --------- views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class CreditHistoriqueCompletAPIView(APIView):
    def get(self, request, credit_id):
        try:
            credit = Credit.objects.using('sqlite').get(id=credit_id)
        except Credit.DoesNotExist:
            return Response({"error": "Crédit introuvable."}, status=404)

        credit_data = CreditSummarySerializer(credit).data
        # validations = ValidationCredit.objects.using('sqlite').filter(credit=credit).order_by('date_validation')
        validations = ValidationCredit.objects.using('sqlite').filter(credit=credit)
        validations_data = ValidationCreditDetailSerializer(validations, many=True).data

        return Response({
            "credit": credit_data,
            "validations": validations_data
        }, status=200)

##### -------- historique complet du demande -------- #### 



from .models import Credit, ValidationCredit




class RemonterCreditAPIView(APIView):
    def post(self, request, credit_id):
        user_id = request.data.get('user_id')
        motiv = request.data.get('motiv')
        memo = request.data.get('memo')

        if not user_id:
            return Response({"error": "user_id est requis."}, status=400)
        elif not motiv:
            return Response({"error": "motiv est requis."}, status=400)
        if not memo:
            return Response({"error": "memo est requis."}, status=400)

        try:
            user = NewUser.objects.using('sqlite').get(id=user_id)
        except NewUser.DoesNotExist:
            return Response({"error": "Utilisateur introuvable."}, status=404)

        try:
            credit = Credit.objects.using('sqlite').get(id=credit_id)
        except Credit.DoesNotExist:
            return Response({"error": "Crédit introuvable."}, status=404)

        poste = user.post
        points = POSTE_POINTS.get(poste, 0)

        # === Cas spécial pour "Analyse de Risque" ===
        if poste == "Analyse de Risque":
            documents = request.FILES.getlist('documents')
            if not documents:
                return Response({"error": "document est requis."}, status=400)
            for fichier in documents:
                Document.objects.using('sqlite').create(
                    credit=credit,
                    fichier=fichier,
                    type_document="analyse",
                    createur=user
                )

        # === Création de la validation ===
        ValidationCredit.objects.using('sqlite').create(
            credit=credit,
            validateur=user,
            points=points,
            poste=poste,
            motiv=motiv,
            memo=memo,
            date_validation=timezone.now(),
            status="Validé"
        )

        # === Mise à jour du crédit ===
        credit.points_valides += points
        if credit.points_valides >= 48 and credit.status != 'VALIDÉ':
            credit.status = 'VALIDÉ'
        credit.save(using='sqlite')

        
        next_poit = {2: 4, 4: 6, 6: 12, 12: 24}.get(user.poit, None)
        if next_poit:
            validateurs_suivants = NewUser.objects.using('sqlite').filter(poit=next_poit, is_active=True)
            for validateur in validateurs_suivants:
                send_validation_email(validateur.email, credit.reference, validateur)
                Notification.objects.using('sqlite').create(
                    user=validateur,
                    message=(
                        f"Bonjour {validateur.post} ({validateur.nom} {validateur.prenom}),\n\n"
                        f"Vous avez une nouvelle demande de validation pour le crédit {credit.reference}.\n"
                        f"Cordialement."
                    ),
                    objet=f"Nouvelle demande de validation - Crédit {credit.reference}"
                )

        return Response({
            "message": "Crédit validé et remonté.",
            "points_cumulés": credit.points_valides,
            "statut": credit.status
        }, status=200)





from rest_framework import generics

#notification
# views.py

class UserNotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get('userid')
        queryset = Notification.objects.using('sqlite').all()
        if user_id is not None:
            queryset = queryset.filter(user__id=user_id)
        return queryset.order_by('-date_created')


class MarkAllNotificationsAsRead(APIView):
    def post(self, request):
        user_id = request.data.get('userid')

        if not user_id:
            return Response({"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        notifications = Notification.objects.using('sqlite').filter(user__id=user_id, lu=False)
        updated_count = notifications.update(lu=True)

        return Response(
            {"message": f"{updated_count} notifications marked as read."},
            status=status.HTTP_200_OK
        )
    

class NotificationDetailView(generics.RetrieveAPIView):
    queryset = Notification.objects.using('sqlite').all()
    serializer_class = NotificationSerializer
    lookup_field = 'pk'



class CreditStatsView(APIView):
    def get(self, request):
        db = 'sqlite'

        total = Credit.objects.using(db).count()
        valides = Credit.objects.using(db).filter(status="VALIDÉ").count()
        rejetes = Credit.objects.using(db).filter(status="REJETÉ").count()
        en_cours = Credit.objects.using(db).filter(status="EN_COURS").count()
        montant_total = Credit.objects.using(db).aggregate(total=Sum("montant"))["total"] or 0
        duree_moyenne = Credit.objects.using(db).aggregate(avg=Avg("duree"))["avg"] or 0

        credits_par_agence = Credit.objects.using(db).values("agence").annotate(count=Count("id"))
        type_credit = Credit.objects.using(db).values("type_dossier").annotate(count=Count("id"))

        latest_validation = ValidationCredit.objects.using(db).filter(
            credit=OuterRef('pk'),
            status="Validé",
            date_validation__isnull=False
        ).order_by('-date_validation')

        

        validated_credits = Credit.objects.using(db).filter(status="VALIDÉ").annotate(
            latest_date_validation=Subquery(latest_validation.values('date_validation')[:1])
        ).annotate(
            delai=ExpressionWrapper(
                F('latest_date_validation') - F('date_demande'),
                output_field=DurationField()
            )
        )

        delai_moyen = validated_credits.aggregate(avg_delai=Avg("delai"))["avg_delai"] or timedelta()


        
        print("delais_moyen : ", delai_moyen)
        print("validated_credits : ", validated_credits)
        return Response({
            "total": total,
            "valides": valides,
            "rejetes": rejetes,
            "en_cours": en_cours,
            "montant_total": montant_total,
            "duree_moyenne": duree_moyenne,
            "credits_par_agence": list(credits_par_agence),
            "repartition_type_dossier": list(type_credit),
            "delai_moyen_traitement_jours": delai_moyen.days if delai_moyen else 0
        })







class RejeterCreditAPIView(APIView):
    def post(self, request, credit_id):
        user_id = request.data.get("user_id")
        motif = request.data.get("motif")

        if not user_id or not motif:
            return Response({"error": "user_id et motif sont requis."}, status=400)

        try:
            user = NewUser.objects.using('sqlite').get(id=user_id)
        except NewUser.DoesNotExist:
            return Response({"error": "Utilisateur introuvable."}, status=404)

        try:
            credit = Credit.objects.using('sqlite').get(id=credit_id)
        except Credit.DoesNotExist:
            return Response({"error": "Crédit introuvable."}, status=404)

        poste = user.post
        points = POSTE_POINTS.get(poste, 0)
        current_poit = user.poit
        credit.points_valides -= points

        REJET_BACKFLOW = {
            24: 12,
            12: 6,
            6: 2,
            4: 0,
            # 2: 0
        }

        POIT_ENVOYE = {
            24:12,
            12:6,
            6:4,
            4:2
        }
        print("poit user : ", user.poit)
        new_poit = REJET_BACKFLOW.get(current_poit, 0)

        new_poit_envoye = POIT_ENVOYE.get(current_poit,0)
       

        if current_poit == 24:
            credit.status = "REJETÉ"
            credit.motif_rejet = motif
            credit.date_rejet = timezone.now()

        ValidationCredit.objects.using('sqlite').create(
            credit=credit,
            validateur=user,
            points=new_poit,
            poste=poste,
            motiv=motif,
            status="Rejeté",
            date_rejet=timezone.now()
        )
        agence_credit = credit.agence
        # print("agence : ", agence_credit)
        print("new_poit else : ", new_poit_envoye)

# Priorité : chercher dans la même agence si poit = 4 ou 2
        if new_poit_envoye in [4, 2]:
            print("  new_poit_envoye  :  ", new_poit_envoye)
            validateurs_suivants = NewUser.objects.using('sqlite') \
                .filter(poit=new_poit_envoye, is_active=True, agnece=agence_credit) \
                .first()
            print("validateurs_suivants : ", validateurs_suivants)
        else:
            validateurs_suivants = None

        # Si pas trouvé via l'agence, fallback vers n'importe quel validateur actif avec ce poit
        if not validateurs_suivants:
            validateurs_suivants = NewUser.objects.using('sqlite') \
                .filter(poit=new_poit_envoye, is_active=True) \
                .first()

        # Envoyer email et notification si validateur trouvé
        if validateurs_suivants:
            print("validateur : ", validateurs_suivants.username)
            send_validation_email(validateurs_suivants.email, credit.reference, validateurs_suivants)
            Notification.objects.using('sqlite').create(
             user=validateurs_suivants,
                message=(
            f"Bonjour {validateurs_suivants.post} ({validateurs_suivants.nom} {validateurs_suivants.prenom}),\n\n"
            f"Vous avez une nouvelle demande de validation pour le crédit {credit.reference}.\n"
            f"Cordialement."
        ),
        objet=f"Nouvelle demande de validation - Crédit {credit.reference}"
            )
        else:
            print("Aucun validateur trouvé pour poit =", new_poit_envoye)

        
        # if new_poit == 2: 
        #     validateurs_suivants = NewUser.objects.using('sqlite').get(poit=4, is_active=True, agnece=agence_credit)
        #     print("validateur : suio : ", validateurs_suivants)
        #     if validateurs_suivants:
        #         print("validateur : ", validateurs_suivants.username)
        #         send_validation_email(validateurs_suivants.email, credit.reference, validateurs_suivants)
        #         Notification.objects.using('sqlite').create(
        #         user=validateurs_suivants,
        #         message=(
        #             f"Bonjour {validateurs_suivants.post} ({validateurs_suivants.nom} {validateurs_suivants.prenom}),\n\n"
        #             f"Vous avez une nouvelle demande de validation pour le crédit {credit.reference}.\n"
        #             f"Cordialement."
        #         ),
        #         objet=f"Nouvelle demande de validation - Crédit {credit.reference}"
        #     )
        # else :
        #     print("--- ici : ", new_poit)
        #     if new_poit == 0:
        #         validateurs_suivants = NewUser.objects.using('sqlite').get(poit=2, is_active=True, agnece=agence_credit)
        #         print("val 2 : ", validateurs_suivants)
        #         if validateurs_suivants:
        #             print("validateur : ", validateurs_suivants.username)
        #             send_validation_email(validateurs_suivants.email, credit.reference, validateurs_suivants)
        #             Notification.objects.using('sqlite').create(
        #             user=validateurs_suivants,
        #             message=(
        #                 f"Bonjour {validateurs_suivants.post} ({validateurs_suivants.nom} {validateurs_suivants.prenom}),\n\n"
        #                 f"Vous avez une nouvelle demande de validation pour le crédit {credit.reference}.\n"
        #                 f"Cordialement."
        #             ),
        #             objet=f"Nouvelle demande de validation - Crédit {credit.reference}"
        #         )
        #     else : 
        #         print("new_poit else : ", new_poit)
        #         validateurs_suivants = NewUser.objects.using('sqlite').get(poit=new_poit, is_active=True, agnece=agence_credit)
        #         print("val 2 : ", validateurs_suivants)
        #         if validateurs_suivants:
        #             print("validateur : ", validateurs_suivants.username)
        #             send_validation_email(validateurs_suivants.email, credit.reference, validateurs_suivants)
        #             Notification.objects.using('sqlite').create(
        #             user=validateurs_suivants,
        #             message=(
        #                 f"Bonjour {validateurs_suivants.post} ({validateurs_suivants.nom} {validateurs_suivants.prenom}),\n\n"
        #                 f"Vous avez une nouvelle demande de validation pour le crédit {credit.reference}.\n"
        #                 f"Cordialement."
        #             ),
        #             objet=f"Nouvelle demande de validation - Crédit {credit.reference}"
        #         )
        credit.save()

        credit.save(using='sqlite')
        
        credit.points_valides = new_poit
        credit.save()
        return Response({
            "message": "Crédit rejeté avec succès.",
            "statut": credit.status,
            "motif": credit.motif_rejet,
            "points_retirés": points
        }, status=200)



class TypeUploadFileListAPIView(APIView):
    def get(self, request, format=None):
        type_client = request.query_params.get("type_client")
        if not type_client:
            return Response({"error": "type_client is required"}, status=400)

        documents = TypeUploadFile.objects.filter(type_client=type_client)
        serializer = TypeUploadFileSerializer(documents, many=True)
        return Response(serializer.data)

    # def post(self, request, format=None):
    #     value = request.data.get("value")
    #     type_client = request.data.get("type_client")

    #     if not value or not type_client:
    #         return Response({"error": "value and type_client are required"}, status=400)

    #     if TypeUploadFile.objects.filter(value=value, type_client=type_client).exists():
    #         return Response(
    #             {"error": f"Un document avec value='{value}' existe déjà pour type_client='{type_client}'"},
    #             status=400
    #         )

    #     serializer = TypeUploadFileSerializer(data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


    def post(self, request, format=None):
        documents = request.data  # expect a list of objects

        if not isinstance(documents, list) or len(documents) == 0:
            return Response({"error": "A non-empty list of documents is required."}, status=400)

        # We assume all documents are for the same type_client
        type_client = documents[0].get("type_client")
        if not type_client:
            return Response({"error": "type_client is missing in one or more documents."}, status=400)

        # Delete existing records for this type_client
        TypeUploadFile.objects.filter(type_client=type_client).delete()

        # Bulk insert new documents
        serializer = TypeUploadFileSerializer(data=documents, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



from django.utils.dateparse import parse_date






from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

class CompteClientView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            client_id = request.query_params.get("client")
            nature_compte = request.query_params.get("nature_compte")

            # Construction de la requête de base
            query = """
                SELECT
                    L.LIBELLE AS Nature_de_compte,
                    C.COMPTE,
                    C.CLIENT,
                    P.IDP AS IDENTIFIANT,
                    P.PAYSNAIS,
                    P.DATNAIS,
                    P.NOM,
                    P.PRENOM,
                    P.TEL,
                    CASE WHEN P.SEXE = 'M' THEN 'HOMME' ELSE 'FEMME' END AS SEXE,
                    P.TYPEID AS TYPE_DOCUMENT,
                    P.NUMID 
                FROM 
                    NCGLIB L,
                    CPT C,
                    TITU T,
                    IDP P 
                WHERE  
                    C.CLIENT = T.CLIENT AND 
                    T.IDP = P.IDP AND 
                    L.NCG = C.NCG AND 
                    C.NCG IN ('210000','210001','210400','210500','210550','210600','210700','210800')
            """

            params = []
            
            # Ajout des conditions de filtrage
            conditions = []
            
            if client_id:
                conditions.append("C.CLIENT = %s")
                params.append(client_id)
                
            if nature_compte:
                conditions.append("L.LIBELLE LIKE %s")
                params.append(f"%{nature_compte}%")
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

            if rows:
                results = []
                for row in rows:
                    results.append({
                        "Nature_de_compte": row[0],
                        "COMPTE": row[1],
                        "CLIENT": row[2],
                        "IDENTIFIANT": row[3],
                        "PAYSNAIS": row[4],
                        "DATNAIS": row[5],
                        "NOM": row[6],
                        "PRENOM": row[7],
                        "TEL": row[8],
                        "SEXE": row[9],
                        "TYPE_DOCUMENT": row[10],
                        "NNI":row[11]
                    })
                return Response(results, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"message": "Aucun résultat trouvé pour les critères de recherche."},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ------ ENTREPRISE 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

class CompteProfessionnelView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            client_id = request.query_params.get("client")
            nature_compte = request.query_params.get("nature_compte")
            nif = request.query_params.get("nif")
            raison_sociale = request.query_params.get("raison_sociale")

            # Requête de base
            query = """
                SELECT 
                    C.CLIENT,
                    L.LIBELLE AS Nature_de_compte,
                    C.COMPTE,
                    C.AGENCE AS Agence,
                    P.jurlib1 AS Raison_sociale,
                    P.tin1 AS NIF,
                    P.rcsno AS RC,
                    (select max(ad.adrl3 || ' ' || ad.adrl4 || ' ' || ad.adrl5) from adr ad where ad.client = C.client ) Adresse,
                    P.TEL
                FROM 
                    NCGLIB L,
                    CPT C,
                    TITU T,
                    IDM P
                WHERE 
                    C.CLIENT = T.CLIENT AND 
                    T.IDM = P.IDM AND 
                    L.NCG = C.NCG AND 
                    C.NCG IN ('210100','210101','210200','210201','210300','210301','210900')
            """

            params = []
            conditions = []

            # Filtres optionnels
            if client_id:
                conditions.append("C.CLIENT = %s")
                params.append(client_id)

            if nature_compte:
                conditions.append("L.LIBELLE LIKE %s")
                params.append(f"%{nature_compte}%")

            if nif:
                conditions.append("P.tin1 = %s")
                params.append(nif)

            if raison_sociale:
                conditions.append("P.jurlib1 LIKE %s")
                params.append(f"%{raison_sociale}%")

            if conditions:
                query += " AND " + " AND ".join(conditions)

            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

            if rows:
                results = []
                for row in rows:
                    results.append({
                        "CLIENT": row[0],
                        "Nature_de_compte": row[1],
                        "COMPTE": row[2],
                        "Agence": row[3],
                        "Raison_sociale": row[4],
                        "NIF": row[5],
                        "RC": row[6],
                        "Address": row[7],
                        "TEL": row[8]
                    })
                return Response(results, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"message": "Aucun compte professionnel trouvé avec ces critères."},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IDMListView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM IDM")
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            if rows:
                results = []
                for row in rows:
                    results.append(dict(zip(columns, row)))
                return Response(results, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"message": "La table IDM est vide."},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

class NcgLibView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Liste des codes NCG à rechercher
            ncg_list = ['203800', '202800', '201280', '204100', '204300', 
                        '204200', '203100', '201300', '203000', '202000', 
                        '201210', '201280', '201805', '201800']
            
            # Convertir la liste en une chaîne formatée pour la requête SQL
            ncg_list_str = ",".join([f"'{ncg}'" for ncg in ncg_list])

            query = f"""
                SELECT NCG, LIBELLE, LIBREL 
                FROM NCGLIB 
                WHERE NCG IN({ncg_list_str})
            """

            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    "ncg": row[0],
                    "libelle": row[1],
                    "librel": row[2],
                })

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)