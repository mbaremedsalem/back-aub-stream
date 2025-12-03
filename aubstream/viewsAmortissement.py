# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class PrtcliDossiersAPIView(APIView):
    def post(self, request):
        try:
            # Récupération des paramètres
            client = request.data.get('client')
            nooper = request.data.get('nooper')
            
            # Pagination
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            offset = (page - 1) * page_size

            # Construction de la requête SQL
            base_query = """
                SELECT 
                    Numero_Dossier,
                    Client,
                    Date_Creation,
                    Capital,
                    Marge,
                    Type,
                    Nbr_Echeance
                FROM PRTCLI_DOSSIERS
                WHERE 1=1
            """
            
            params = []
            if client:
                base_query += " AND Client = %s"
                params.append(client)
            if nooper:
                base_query += " AND Numero_Dossier = %s"
                params.append(nooper)

            # Requête pour le count total
            count_query = f"SELECT COUNT(*) FROM ({base_query})"
            
            # Requête paginée
            paginated_query = f"""
                {base_query}
                ORDER BY Numero_Dossier
                OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
            """
            params.extend([offset, page_size])

            # Exécution des requêtes
            with connection.cursor() as cursor:
                # Count total
                cursor.execute(count_query, params[:-2])
                total = cursor.fetchone()[0]

                # Données paginées
                cursor.execute(paginated_query, params)
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            response_data = {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": results
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in PrtcliDossiersAPIView: {str(e)}", exc_info=True)
            return Response(
                {"error": "Une erreur est survenue lors du traitement de la requête"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )





from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connection
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

class entetPostView(APIView):
    def post(self, request):
        # Récupérer les données de la requête
        cliprt = request.data.get('client')
        nooper = request.data.get('nooper')

        if not cliprt or not nooper:
            return Response(
                {'error': 'Les paramètres cliprt et nooper sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Nettoyage des paramètres (strip pour éviter les espaces, cast si besoin)
        cliprt = str(cliprt).strip()
        nooper = str(nooper).strip()

        try:
            # Nouvelle requête SQL
            query = """
                SELECT 
                    pr.nooper AS Numero_Dossier,
                    'Mourabaha ' AS type_mourabaha,
                    pr.datdep AS date_mep,
                    pr.datrmb AS date_1ech,
                    MAX(ech.datrmb) AS date_dern_ech,
                    MAX(pr.mntprt) AS prix_achat,
                    MAX(pr.mntprt) + SUM(ech.mntint) AS prix_vente,
                    MAX(pr.mntprt) + SUM(ech.mntint) + SUM(ech.mnttaxe) AS prix_venteTTC,
                    pr.totrmb,
                    pr.mnttaxdos AS frais_dossier,
                    pr.mntasf AS frais_detude,
                    pr.CLIPRT AS client,
                    c.NOM,
                    c.compte,
                    TRUNC(MONTHS_BETWEEN(derndat, datdep)) AS duree_mourabaha,

                    pr.txtaxe AS TOF
                FROM 
                    PRTCLI_LOCAL pr
                JOIN
                    PRTCAMO_LOCAL ech ON pr.nooper = ech.nooper AND ech.typamo = 'R'
                JOIN 
                    CPT_LOCAL c ON pr.CLIPRT = c.CLIENT AND c.ncg IN ('210001','210101','210201','210301')
                WHERE 
                    pr.cliprt = %s AND pr.nooper = %s
                    AND pr.VALIDE<>'A'
                GROUP BY 
                    pr.nooper,
                    pr.datdep,
                    pr.datrmb,
                    pr.mnttaxdos,
                    pr.mntasf,
                    pr.totrmb,
                    pr.CLIPRT,
                    c.NOM,
                    c.compte,
                    pr.txtaxe,
                    pr.derndat
                    
            """

            with connection.cursor() as cursor:
                cursor.execute(query, [cliprt, nooper])
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()

            if not row:
                return Response(
                    {'error': 'Aucun résultat trouvé pour les critères donnés'},
                    status=status.HTTP_404_NOT_FOUND
                )

            result = dict(zip(columns, row))

            # Convertir les dates en string pour JSON
            date_fields = ['date_mep', 'date_1ech', 'date_dern_ech']
            for field in date_fields:
                if field in result and result[field]:
                    result[field] = result[field].strftime('%Y-%m-%d')

            return Response(result)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

class PrtcamoNOOPERliView(APIView):
    def post(self, request):
        nooper = request.data.get('nooper')
        
        if not nooper:
            return Response(
                {'error': 'Le paramètre nooper est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Requête SQL adaptée aux colonnes de votre table
            query = """
                SELECT 
                    NOOPER, NUMSEQ, NORMB, NOAMO, DATRMB, MNTRMB, 
                    MNTINT, MNTASS, MNTCAP, DATREG, TYPAMO, MNTAGI,
                    MNTDEC, SLDAMO, DATMAJ, DATRMB_X, MNTTAXE, DATDERNC,
                    TXDB, DATREVTX, MNTFRAIS, MNTFRTAX, MNTTIMBRE, 
                    MNTTAXFRAISDIV, MNTFRAISDIV, DATEFFTX, DATTHEORMB,
                    MNTCAP_PART, MNTINT_PART, MNTTAXE_PART, MNT_INTRET_PART,
                    MNTASS_PART, TAXASS, NOOPERVIR, MNTINTMRG, MNTINTIND,
                    MNTINTSPR, MNTINTRET
                FROM 
                    PRTCAMO_LOCAL
                WHERE 
                    NOOPER = %s AND TYPAMO = 'R'
                ORDER BY 
                    NOAMO
            """

            with connection.cursor() as cursor:
                cursor.execute(query, [nooper])
                columns = [col[0] for col in cursor.description]
                results = cursor.fetchall()

            if not results:
                return Response(
                    {'error': f'Aucun amortissement trouvé pour le numéro {nooper}'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Conversion des résultats en format JSON
            data = []
            for row in results:
                row_data = dict(zip(columns, row))
                
                # Conversion des dates
                date_fields = ['DATRMB', 'DATREG', 'DATMAJ', 'DATDERNC', 
                             'DATREVTX', 'DATEFFTX', 'DATTHEORMB']
                for field in date_fields:
                    if field in row_data and row_data[field]:
                        row_data[field] = row_data[field].strftime('%Y-%m-%d')
                
                # Gestion des valeurs NULL
                for key in row_data:
                    if row_data[key] is None:
                        row_data[key] = ""
                
                data.append(row_data)

            return Response(data)

        except Exception as e:
            return Response(
                {'error': f'Erreur serveur: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )