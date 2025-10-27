from django.http import JsonResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
@require_http_methods(["GET", "POST"])
def get_objectives_list(request):
    try:
        with connection.cursor() as cursor:
            # Récupérer les paramètres de filtrage
            period_type = request.GET.get('period_type', None)
            status = request.GET.get('status', None)
            usercode = request.GET.get('usercode', None)
            branch_code = request.GET.get('agence', None)  # Nouveau paramètre agence
            
            # Construire la requête SQL corrigée
            sql = """
                SELECT 
                    o.OBJECTIVE_ID,
                    u.ID,
                    ot.TASK_NAME,
                    ot.UNIT_MEASURE,
                    p.PERIOD_TYPE,
                    p.PERIOD_LABEL,
                    o.TARGET_VALUE,
                    o.ACTUAL_VALUE,
                    CASE 
                        WHEN o.TARGET_VALUE = 0 THEN 0
                        ELSE ROUND((o.ACTUAL_VALUE / o.TARGET_VALUE) * 100, 2)
                    END AS COMPLETION_PERCENTAGE,
                    o.STATUS,
                    o.START_DATE,
                    o.END_DATE,
                    o.CREATED_DATE,
                    COUNT(m.MONTH_OBJ_ID) as MONTHLY_OBJECTIVES_COUNT,
                    -- Champs pour l'assigné (utilisateur principal)
                    u.USERNAME,
                    u.FULLNAME,
                    u.EMAIL,
                    u.POST,
                    u.BRANCH_CODE,
                    -- Champs pour le créateur
                    creator.ID as CREATOR_ID,
                    creator.USERNAME as CREATOR_USERNAME,
                    creator.FULLNAME as CREATOR_FULLNAME,
                    creator.EMAIL as CREATOR_EMAIL,
                    creator.POST as CREATOR_POST,
                    creator.BRANCH_CODE as CREATOR_BRANCH_CODE
                FROM AM_USER_OBJECTIVES o
                JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
                JOIN AM_OBJECTIVE_TYPES ot ON o.TASK_TYPE_ID = ot.TASK_TYPE_ID
                JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
                LEFT JOIN AM_MONTHLY_OBJECTIVES m ON o.OBJECTIVE_ID = m.OBJECTIVE_ID
                LEFT JOIN AM_USERS_LOCAL creator ON o.CREATED_BY = creator.ID
            """
            
            where_conditions = []
            params = {}
            
            # Appliquer les filtres
            if period_type:
                where_conditions.append("p.PERIOD_TYPE = %s")
                params['period_type'] = period_type
                
            if status:
                where_conditions.append("o.STATUS = %s")
                params['status'] = status
                
            if usercode:
                where_conditions.append("u.USERCODE = %s")
                params['usercode'] = usercode
            
            # Nouveau filtre par agence (BRANCH_CODE)
            if branch_code:
                where_conditions.append("u.BRANCH_CODE = %s")
                params['branch_code'] = branch_code
            
            if where_conditions:
                sql += " WHERE " + " AND ".join(where_conditions)
            
            sql += """ 
                GROUP BY o.OBJECTIVE_ID, u.ID, ot.TASK_NAME, ot.UNIT_MEASURE, 
                         p.PERIOD_TYPE, p.PERIOD_LABEL, o.TARGET_VALUE, o.ACTUAL_VALUE, 
                         o.STATUS, o.START_DATE, o.END_DATE, o.CREATED_DATE,
                         u.USERNAME, u.FULLNAME, u.EMAIL, u.POST, u.BRANCH_CODE,
                         creator.ID, creator.USERNAME, creator.FULLNAME, creator.EMAIL, creator.POST, creator.BRANCH_CODE
                ORDER BY o.CREATED_DATE DESC
            """
            
            # Préparer les paramètres pour cursor.execute
            query_params = []
            if period_type:
                query_params.append(period_type)
            if status:
                query_params.append(status)
            if usercode:
                query_params.append(usercode)
            if branch_code:
                query_params.append(branch_code)
            
            cursor.execute(sql, query_params)
            columns = [col[0] for col in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                
                # Structurer les données en objets assignee et created_by
                formatted_row = {
                    'OBJECTIVE_ID': row_dict.get('OBJECTIVE_ID'),
                    'ID': row_dict.get('ID'),
                    'TASK_NAME': row_dict.get('TASK_NAME'),
                    'UNIT_MEASURE': row_dict.get('UNIT_MEASURE'),
                    'PERIOD_TYPE': row_dict.get('PERIOD_TYPE'),
                    'PERIOD_LABEL': row_dict.get('PERIOD_LABEL'),
                    'TARGET_VALUE': row_dict.get('TARGET_VALUE'),
                    'ACTUAL_VALUE': row_dict.get('ACTUAL_VALUE'),
                    'COMPLETION_PERCENTAGE': row_dict.get('COMPLETION_PERCENTAGE'),
                    'STATUS': row_dict.get('STATUS'),
                    'START_DATE': row_dict.get('START_DATE'),
                    'END_DATE': row_dict.get('END_DATE'),
                    'CREATED_DATE': row_dict.get('CREATED_DATE'),
                    'MONTHLY_OBJECTIVES_COUNT': row_dict.get('MONTHLY_OBJECTIVES_COUNT'),
                    'assignee': {
                        'USERNAME': row_dict.get('USERNAME'),
                        'FULLNAME': row_dict.get('FULLNAME'),
                        'EMAIL': row_dict.get('EMAIL'),
                        'POST': row_dict.get('POST'),
                        'BRANCH_CODE': row_dict.get('BRANCH_CODE')
                    },
                    'created_by': {
                        'ID': row_dict.get('CREATOR_ID'),
                        'USERNAME': row_dict.get('CREATOR_USERNAME'),
                        'FULLNAME': row_dict.get('CREATOR_FULLNAME'),
                        'EMAIL': row_dict.get('CREATOR_EMAIL'),
                        'POST': row_dict.get('CREATOR_POST'),
                        'BRANCH_CODE': row_dict.get('CREATOR_BRANCH_CODE')
                    }
                }
                
                # Convertir les dates en string pour JSON
                for key, value in formatted_row.items():
                    if value and hasattr(value, 'isoformat'):
                        formatted_row[key] = value.isoformat()
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if sub_value and hasattr(sub_value, 'isoformat'):
                                formatted_row[key][sub_key] = sub_value.isoformat()
                
                results.append(formatted_row)
            
            return JsonResponse({
                'success': True,
                'objectives': results,
                'total_count': len(results),
                'filters_applied': {
                    'period_type': period_type,
                    'status': status,
                    'usercode': usercode,
                    'agence': branch_code
                }
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'type': type(e).__name__
        }, status=500)

# @csrf_exempt
# @require_http_methods(["GET", "POST"])
# def get_objectives_list(request):
#     try:
#         with connection.cursor() as cursor:
#             # Récupérer les paramètres de filtrage
#             period_type = request.GET.get('period_type', None)
#             status = request.GET.get('status', None)
#             usercode = request.GET.get('usercode', None)
            
#             # Construire la requête SQL corrigée
#             sql = """
#                 SELECT 
#                     o.OBJECTIVE_ID,
#                     u.ID,
#                     ot.TASK_NAME,
#                     ot.UNIT_MEASURE,
#                     p.PERIOD_TYPE,
#                     p.PERIOD_LABEL,
#                     o.TARGET_VALUE,
#                     o.ACTUAL_VALUE,
#                     CASE 
#                         WHEN o.TARGET_VALUE = 0 THEN 0
#                         ELSE ROUND((o.ACTUAL_VALUE / o.TARGET_VALUE) * 100, 2)
#                     END AS COMPLETION_PERCENTAGE,
#                     o.STATUS,
#                     o.START_DATE,
#                     o.END_DATE,
#                     o.CREATED_DATE,
#                     COUNT(m.MONTH_OBJ_ID) as MONTHLY_OBJECTIVES_COUNT,
#                     -- Champs pour l'assigné (utilisateur principal)
#                     u.USERNAME,
#                     u.FULLNAME,
#                     u.EMAIL,
#                     u.POST,
#                     u.BRANCH_CODE,
#                     -- Champs pour le créateur
#                     creator.ID as CREATOR_ID,
#                     creator.USERNAME as CREATOR_USERNAME,
#                     creator.FULLNAME as CREATOR_FULLNAME,
#                     creator.EMAIL as CREATOR_EMAIL,
#                     creator.POST as CREATOR_POST,
#                     creator.BRANCH_CODE as CREATOR_BRANCH_CODE
#                 FROM AM_USER_OBJECTIVES o
#                 JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
#                 JOIN AM_OBJECTIVE_TYPES ot ON o.TASK_TYPE_ID = ot.TASK_TYPE_ID
#                 JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
#                 LEFT JOIN AM_MONTHLY_OBJECTIVES m ON o.OBJECTIVE_ID = m.OBJECTIVE_ID
#                 LEFT JOIN AM_USERS_LOCAL creator ON o.CREATED_BY = creator.ID
#             """
            
#             where_conditions = []
#             params = {}
            
#             # Appliquer les filtres
#             if period_type:
#                 where_conditions.append("p.PERIOD_TYPE = %s")
#                 params['period_type'] = period_type
                
#             if status:
#                 where_conditions.append("o.STATUS = %s")
#                 params['status'] = status
                
#             if usercode:
#                 where_conditions.append("u.USERCODE = %s")
#                 params['usercode'] = usercode
            
#             if where_conditions:
#                 sql += " WHERE " + " AND ".join(where_conditions)
            
#             sql += """ 
#                 GROUP BY o.OBJECTIVE_ID, u.ID, ot.TASK_NAME, ot.UNIT_MEASURE, 
#                          p.PERIOD_TYPE, p.PERIOD_LABEL, o.TARGET_VALUE, o.ACTUAL_VALUE, 
#                          o.STATUS, o.START_DATE, o.END_DATE, o.CREATED_DATE,
#                          u.USERNAME, u.FULLNAME, u.EMAIL, u.POST, u.BRANCH_CODE,
#                          creator.ID, creator.USERNAME, creator.FULLNAME, creator.EMAIL, creator.POST, creator.BRANCH_CODE
#                 ORDER BY o.CREATED_DATE DESC
#             """
            
#             # Préparer les paramètres pour cursor.execute
#             query_params = []
#             if period_type:
#                 query_params.append(period_type)
#             if status:
#                 query_params.append(status)
#             if usercode:
#                 query_params.append(usercode)
            
#             cursor.execute(sql, query_params)
#             columns = [col[0] for col in cursor.description]
#             results = []
            
#             for row in cursor.fetchall():
#                 row_dict = dict(zip(columns, row))
                
#                 # Structurer les données en objets assignee et created_by
#                 formatted_row = {
#                     'OBJECTIVE_ID': row_dict.get('OBJECTIVE_ID'),
#                     'ID': row_dict.get('ID'),
#                     'TASK_NAME': row_dict.get('TASK_NAME'),
#                     'UNIT_MEASURE': row_dict.get('UNIT_MEASURE'),
#                     'PERIOD_TYPE': row_dict.get('PERIOD_TYPE'),
#                     'PERIOD_LABEL': row_dict.get('PERIOD_LABEL'),
#                     'TARGET_VALUE': row_dict.get('TARGET_VALUE'),
#                     'ACTUAL_VALUE': row_dict.get('ACTUAL_VALUE'),
#                     'COMPLETION_PERCENTAGE': row_dict.get('COMPLETION_PERCENTAGE'),
#                     'STATUS': row_dict.get('STATUS'),
#                     'START_DATE': row_dict.get('START_DATE'),
#                     'END_DATE': row_dict.get('END_DATE'),
#                     'CREATED_DATE': row_dict.get('CREATED_DATE'),
#                     'MONTHLY_OBJECTIVES_COUNT': row_dict.get('MONTHLY_OBJECTIVES_COUNT'),
#                     'assignee': {
#                         'USERNAME': row_dict.get('USERNAME'),
#                         'FULLNAME': row_dict.get('FULLNAME'),
#                         'EMAIL': row_dict.get('EMAIL'),
#                         'POST': row_dict.get('POST'),
#                         'BRANCH_CODE': row_dict.get('BRANCH_CODE')
#                     },
#                     'created_by': {
#                         'ID': row_dict.get('CREATOR_ID'),
#                         'USERNAME': row_dict.get('CREATOR_USERNAME'),
#                         'FULLNAME': row_dict.get('CREATOR_FULLNAME'),
#                         'EMAIL': row_dict.get('CREATOR_EMAIL'),
#                         'POST': row_dict.get('CREATOR_POST'),
#                         'BRANCH_CODE': row_dict.get('CREATOR_BRANCH_CODE')
#                     }
#                 }
                
#                 # Convertir les dates en string pour JSON
#                 for key, value in formatted_row.items():
#                     if value and hasattr(value, 'isoformat'):
#                         formatted_row[key] = value.isoformat()
#                     elif isinstance(value, dict):
#                         for sub_key, sub_value in value.items():
#                             if sub_value and hasattr(sub_value, 'isoformat'):
#                                 formatted_row[key][sub_key] = sub_value.isoformat()
                
#                 results.append(formatted_row)
            
#             return JsonResponse({
#                 'success': True,
#                 'objectives': results,
#                 'total_count': len(results)
#             })
            
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e),
#             'type': type(e).__name__
#         }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def assign_objectives(request):
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Validation des champs obligatoires
        required_fields = [
            'user_id', 'task_type_id', 'period_id', 
            'target_value', 'created_by'
        ]
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Champs manquants: {", ".join(missing_fields)}',
                'required_fields': required_fields
            }, status=400)
        
        # Gérer user_id comme liste ou valeur unique
        user_ids = data['user_id']
        if not isinstance(user_ids, list):
            user_ids = [user_ids]
        
        task_type_id = data['task_type_id']
        period_id = data['period_id']
        target_value = float(data['target_value'])
        created_by = data['created_by']
        
        results = []
        errors = []
        
        with connection.cursor() as cursor:
            # Vérifier que le type de tâche existe (une seule fois)
            cursor.execute(
                "SELECT TASK_TYPE_ID FROM AM_OBJECTIVE_TYPES WHERE TASK_TYPE_ID = :task_type_id",
                {'task_type_id': task_type_id}
            )
            if not cursor.fetchone():
                return JsonResponse({
                    'success': False,
                    'error': f'Type de tâche "{task_type_id}" non trouvé'
                }, status=404)
            
            # Vérifier que la période existe (une seule fois)
            cursor.execute(
                "SELECT START_DATE, END_DATE FROM AM_OBJECTIVE_PERIODS WHERE PERIOD_ID = :period_id",
                {'period_id': period_id}
            )
            period_row = cursor.fetchone()
            if not period_row:
                return JsonResponse({
                    'success': False,
                    'error': f'Période "{period_id}" non trouvée. Créez d\'abord la période.'
                }, status=404)
            
            start_date, end_date = period_row
            
            # Calcul des objectifs mensuels (une seule fois pour tous les users)
            months_diff = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
            monthly_target_value = round(target_value / months_diff, 2)
            
            # Ajustement pour le dernier mois
            total_monthly = monthly_target_value * (months_diff - 1)
            last_month_target = round(target_value - total_monthly, 2)
            
            # Pour chaque utilisateur
            for user_id in user_ids:
                try:
                    # Vérifier que l'utilisateur existe
                    cursor.execute(
                        "SELECT ID, USERCODE, FULLNAME FROM AM_USERS_LOCAL WHERE ID = :user_id",
                        {'user_id': user_id}
                    )
                    user_row = cursor.fetchone()
                    if not user_row:
                        errors.append(f'Utilisateur avec ID {user_id} non trouvé')
                        continue
                    
                    user_id_db, usercode, fullname = user_row
                    
                    # Générer un ID d'objectif unique
                    from datetime import datetime
                    date_prefix = datetime.now().strftime('%Y%m%d%H%M%S')
                    cursor.execute(
                        "SELECT COUNT(*) FROM AM_USER_OBJECTIVES WHERE OBJECTIVE_ID LIKE :prefix",
                        {'prefix': f'OBJ_{date_prefix}%'}
                    )
                    count = cursor.fetchone()[0]
                    objective_id = f"OBJ_{date_prefix}_{count+1:04d}"
                    
                    # Insérer l'objectif principal
                    insert_sql = """
                        INSERT INTO AM_USER_OBJECTIVES (
                            OBJECTIVE_ID, USER_ID, TASK_TYPE_ID, PERIOD_ID,
                            TARGET_VALUE, START_DATE, END_DATE, CREATED_BY
                        ) VALUES (
                            :objective_id, :user_id, :task_type_id, :period_id,
                            :target_value, :start_date, :end_date, :created_by
                        )
                    """
                    
                    cursor.execute(insert_sql, {
                        'objective_id': objective_id,
                        'user_id': user_id,
                        'task_type_id': task_type_id,
                        'period_id': period_id,
                        'target_value': target_value,
                        'start_date': start_date,
                        'end_date': end_date,
                        'created_by': created_by
                    })
                    
                    # Créer les objectifs mensuels automatiquement
                    monthly_count = 0
                    for month in range(months_diff):
                        current_month = (start_date.month + month - 1) % 12 + 1
                        current_year = start_date.year + (start_date.month + month - 1) // 12
                        
                        month_obj_id = f"MOBJ_{objective_id[4:]}_{month+1:02d}"
                        target = last_month_target if month == months_diff - 1 else monthly_target_value
                        
                        cursor.execute("""
                            INSERT INTO AM_MONTHLY_OBJECTIVES (
                                MONTH_OBJ_ID, OBJECTIVE_ID, MONTH_NUMBER, MONTH_YEAR, MONTHLY_TARGET
                            ) VALUES (
                                :month_obj_id, :objective_id, :month_number, :month_year, :monthly_target
                            )
                        """, {
                            'month_obj_id': month_obj_id,
                            'objective_id': objective_id,
                            'month_number': current_month,
                            'month_year': current_year,
                            'monthly_target': target
                        })
                        monthly_count += 1
                    
                    results.append({
                        'user_id': user_id,
                        'usercode': usercode,
                        'fullname': fullname,
                        'objective_id': objective_id,
                        'success': True,
                        'monthly_objectives_created': monthly_count
                    })
                    
                except Exception as e:
                    errors.append(f"Erreur pour l'utilisateur {user_id}: {str(e)}")
                    continue
            
            # Préparer la réponse
            if errors and not results:
                return JsonResponse({
                    'success': False,
                    'error': 'Aucun objectif n\'a pu être assigné',
                    'details': errors
                }, status=400)
            
            return JsonResponse({
                'success': True,
                'message': f'{len(results)} objectif(s) assigné(s) avec succès',
                'results': results,
                'errors': errors if errors else None,
                'summary': {
                    'total_users': len(user_ids),
                    'successful_assignments': len(results),
                    'failed_assignments': len(errors),
                    'task_type_id': task_type_id,
                    'period_id': period_id,
                    'target_value': target_value
                }
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'type': type(e).__name__
        }, status=500)




from datetime import datetime
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import uuid

@csrf_exempt
@require_http_methods(["POST"])
def create_period(request):
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Validation des champs obligatoires (seulement period_label maintenant)
        required_fields = ['period_label']
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Champs manquants: {", ".join(missing_fields)}'
            }, status=400)
        
        # Génération automatique du period_id
        period_id = str(uuid.uuid4().hex)[:20]
        
        # Champs fixes avec dates de l'année en cours
        current_year = datetime.now().year
        period_type = "ANNEE"
        start_date = f"{current_year}-01-01"
        end_date = f"{current_year}-12-31"
        
        # Champs du body
        period_label = data['period_label']
        created_by = data.get('created_by', 'SYSTEM')
        
        with connection.cursor() as cursor:
            # Vérifier si la période existe déjà
            cursor.execute(
                "SELECT COUNT(*) FROM AM_OBJECTIVE_PERIODS WHERE PERIOD_ID = :period_id",
                {'period_id': period_id}
            )
            if cursor.fetchone()[0] > 0:
                # Regénérer un nouvel ID si collision
                period_id = str(uuid.uuid4().hex)[:20]
                cursor.execute(
                    "SELECT COUNT(*) FROM AM_OBJECTIVE_PERIODS WHERE PERIOD_ID = :period_id",
                    {'period_id': period_id}
                )
                if cursor.fetchone()[0] > 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'Erreur de génération d\'identifiant unique'
                    }, status=500)
            
            # Vérifier la structure de la table
            cursor.execute("""
                SELECT column_name 
                FROM user_tab_columns 
                WHERE table_name = 'AM_OBJECTIVE_PERIODS' 
                ORDER BY column_id
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            # Construire la requête dynamiquement selon les colonnes disponibles
            if 'CREATED_DATE' in columns and 'CREATED_BY' in columns:
                insert_sql = """
                    INSERT INTO AM_OBJECTIVE_PERIODS (
                        PERIOD_ID, PERIOD_TYPE, START_DATE, END_DATE, 
                        PERIOD_LABEL, CREATED_DATE, CREATED_BY
                    ) VALUES (
                        :period_id, :period_type, TO_DATE(:start_date, 'YYYY-MM-DD'), 
                        TO_DATE(:end_date, 'YYYY-MM-DD'), :period_label, SYSDATE, :created_by
                    )
                """
                params = {
                    'period_id': period_id,
                    'period_type': period_type,
                    'start_date': start_date,
                    'end_date': end_date,
                    'period_label': period_label,
                    'created_by': created_by
                }
            elif 'CREATED_DATE' in columns:
                insert_sql = """
                    INSERT INTO AM_OBJECTIVE_PERIODS (
                        PERIOD_ID, PERIOD_TYPE, START_DATE, END_DATE, 
                        PERIOD_LABEL, CREATED_DATE
                    ) VALUES (
                        :period_id, :period_type, TO_DATE(:start_date, 'YYYY-MM-DD'), 
                        TO_DATE(:end_date, 'YYYY-MM-DD'), :period_label, SYSDATE
                    )
                """
                params = {
                    'period_id': period_id,
                    'period_type': period_type,
                    'start_date': start_date,
                    'end_date': end_date,
                    'period_label': period_label
                }
            else:
                insert_sql = """
                    INSERT INTO AM_OBJECTIVE_PERIODS (
                        PERIOD_ID, PERIOD_TYPE, START_DATE, END_DATE, PERIOD_LABEL
                    ) VALUES (
                        :period_id, :period_type, TO_DATE(:start_date, 'YYYY-MM-DD'), 
                        TO_DATE(:end_date, 'YYYY-MM-DD'), :period_label
                    )
                """
                params = {
                    'period_id': period_id,
                    'period_type': period_type,
                    'start_date': start_date,
                    'end_date': end_date,
                    'period_label': period_label
                }
            
            cursor.execute(insert_sql, params)
            
            return JsonResponse({
                'success': True,
                'message': 'Période créée avec succès',
                'period_id': period_id,
                'period_label': period_label,
                'period_type': period_type,
                'start_date': start_date,
                'end_date': end_date,
                'year': current_year
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'type': type(e).__name__
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_periods(request):
    try:
        with connection.cursor() as cursor:
            # Récupérer les paramètres de filtrage
            period_type = request.GET.get('period_type', None)
            
            # Requête principale pour récupérer les périodes
            sql = """
                SELECT 
                    PERIOD_ID,
                    PERIOD_TYPE,
                    START_DATE,
                    END_DATE,
                    PERIOD_LABEL,
                    CREATED_DATE,
                    CREATED_BY
                FROM AM_OBJECTIVE_PERIODS
            """
            
            params = {}
            if period_type:
                sql += " WHERE PERIOD_TYPE = :period_type"
                params['period_type'] = period_type
            
            sql += " ORDER BY START_DATE DESC"
            
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            periods = []
            
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                
                # Récupérer les informations de l'utilisateur créateur
                user_info = {}
                if row_dict.get('CREATED_BY'):
                    try:
                        cursor.execute("""
                            SELECT ID, USERNAME, FULLNAME, EMAIL, USERCODE, POST, BRANCH_CODE
                            FROM AM_USERS_LOCAL 
                            WHERE USERCODE = :usercode OR TO_CHAR(ID) = :id
                        """, {
                            'usercode': row_dict['CREATED_BY'],
                            'id': row_dict['CREATED_BY']
                        })
                        
                        user_columns = [col[0] for col in cursor.description]
                        user_row = cursor.fetchone()
                        
                        if user_row:
                            user_dict = dict(zip(user_columns, user_row))
                            user_info = {
                                'userId': user_dict.get('ID'),
                                'username': user_dict.get('USERNAME'),
                                'fullName': user_dict.get('FULLNAME'),
                                'email': user_dict.get('EMAIL'),
                                'post': user_dict.get('POST'),
                                'agence': user_dict.get('BRANCH_CODE')
                            }
                            # Nettoyer les valeurs None
                            user_info = {k: v for k, v in user_info.items() if v is not None}
                        else:
                            # Si aucun utilisateur trouvé, créer un objet minimal
                            user_info = {'userId': row_dict['CREATED_BY']}
                    except Exception as user_error:
                        # En cas d'erreur, créer un objet minimal avec l'ID original
                        user_info = {'userId': row_dict['CREATED_BY']}
                else:
                    # Si CREATED_BY est vide
                    user_info = {}
                
                # Formater la période
                period_data = {
                    'PERIOD_ID': row_dict.get('PERIOD_ID'),
                    'PERIOD_TYPE': row_dict.get('PERIOD_TYPE'),
                    'START_DATE': row_dict.get('START_DATE').isoformat() if row_dict.get('START_DATE') and hasattr(row_dict.get('START_DATE'), 'isoformat') else row_dict.get('START_DATE'),
                    'END_DATE': row_dict.get('END_DATE').isoformat() if row_dict.get('END_DATE') and hasattr(row_dict.get('END_DATE'), 'isoformat') else row_dict.get('END_DATE'),
                    'PERIOD_LABEL': row_dict.get('PERIOD_LABEL'),
                    'CREATED_DATE': row_dict.get('CREATED_DATE').isoformat() if row_dict.get('CREATED_DATE') and hasattr(row_dict.get('CREATED_DATE'), 'isoformat') else row_dict.get('CREATED_DATE'),
                    'CREATED_BY': user_info
                }
                
                periods.append(period_data)
            
            return JsonResponse({
                'success': True,
                'periods': periods,
                'total_count': len(periods)
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def check_period_exists(request, period_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT PERIOD_ID, PERIOD_LABEL, START_DATE, END_DATE FROM AM_OBJECTIVE_PERIODS WHERE PERIOD_ID = :period_id",
                {'period_id': period_id}
            )
            period_row = cursor.fetchone()
            
            if period_row:
                period_data = {
                    'period_id': period_row[0],
                    'period_label': period_row[1],
                    'start_date': period_row[2].isoformat() if period_row[2] else None,
                    'end_date': period_row[3].isoformat() if period_row[3] else None
                }
                return JsonResponse({
                    'success': True,
                    'exists': True,
                    'period': period_data
                })
            else:
                return JsonResponse({
                    'success': True,
                    'exists': False,
                    'message': 'Période non trouvée'
                })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_periods_bulk(request):
    try:
        data = json.loads(request.body) if request.body else {}
        
        required_fields = ['year', 'created_by']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Champs manquants: {", ".join(missing_fields)}'
            }, status=400)
        
        year = int(data['year'])
        created_by = data['created_by']
        
        created_periods = []
        
        with connection.cursor() as cursor:
            # Créer la période annuelle
            annual_period_id = f"ANNEE_{year}"
            cursor.execute("""
                INSERT INTO AM_OBJECTIVE_PERIODS (
                    PERIOD_ID, PERIOD_TYPE, START_DATE, END_DATE, PERIOD_LABEL, CREATED_BY
                ) VALUES (
                    :period_id, 'ANNEE', TO_DATE(:start_date, 'YYYY-MM-DD'), 
                    TO_DATE(:end_date, 'YYYY-MM-DD'), :period_label, :created_by
                )
            """, {
                'period_id': annual_period_id,
                'start_date': f'{year}-01-01',
                'end_date': f'{year}-12-31',
                'period_label': f'Année {year}',
                'created_by': created_by
            })
            created_periods.append(annual_period_id)
            
            # Créer les trimestres
            quarters = [
                (1, f'{year}-01-01', f'{year}-03-31', f'T1 {year}'),
                (2, f'{year}-04-01', f'{year}-06-30', f'T2 {year}'),
                (3, f'{year}-07-01', f'{year}-09-30', f'T3 {year}'),
                (4, f'{year}-10-01', f'{year}-12-31', f'T4 {year}')
            ]
            
            for quarter_num, start_date, end_date, label in quarters:
                quarter_period_id = f"T{quarter_num}_{year}"
                cursor.execute("""
                    INSERT INTO AM_OBJECTIVE_PERIODS (
                        PERIOD_ID, PERIOD_TYPE, START_DATE, END_DATE, PERIOD_LABEL, CREATED_BY
                    ) VALUES (
                        :period_id, 'TRIMESTRE', TO_DATE(:start_date, 'YYYY-MM-DD'), 
                        TO_DATE(:end_date, 'YYYY-MM-DD'), :period_label, :created_by
                    )
                """, {
                    'period_id': quarter_period_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'period_label': label,
                    'created_by': created_by
                })
                created_periods.append(quarter_period_id)
            
            # Créer les mois
            for month in range(1, 13):
                month_names = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                             'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
                
                if month in [1, 3, 5, 7, 8, 10, 12]:
                    end_day = 31
                elif month in [4, 6, 9, 11]:
                    end_day = 30
                else:  # Février
                    # Approximatif pour février (29 jours pour les années bissextiles)
                    end_day = 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28
                
                month_period_id = f"MOIS_{month:02d}_{year}"
                cursor.execute("""
                    INSERT INTO AM_OBJECTIVE_PERIODS (
                        PERIOD_ID, PERIOD_TYPE, START_DATE, END_DATE, PERIOD_LABEL, CREATED_BY
                    ) VALUES (
                        :period_id, 'MOIS', TO_DATE(:start_date, 'YYYY-MM-DD'), 
                        TO_DATE(:end_date, 'YYYY-MM-DD'), :period_label, :created_by
                    )
                """, {
                    'period_id': month_period_id,
                    'start_date': f'{year}-{month:02d}-01',
                    'end_date': f'{year}-{month:02d}-{end_day:02d}',
                    'period_label': f'{month_names[month-1]} {year}',
                    'created_by': created_by
                })
                created_periods.append(month_period_id)
            
            return JsonResponse({
                'success': True,
                'message': f'{len(created_periods)} périodes créées avec succès pour l\'année {year}',
                'created_periods': created_periods,
                'total_count': len(created_periods)
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)                                


@csrf_exempt
@require_http_methods(["POST"])
def create_task_type(request):
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Validation des champs obligatoires (task_type_id retiré)
        required_fields = ['task_name', 'unit_measure']
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Champs manquants: {", ".join(missing_fields)}'
            }, status=400)
        
        # Génération automatique du task_type_id
        import uuid
        task_type_id = str(uuid.uuid4().hex)[:20]  # UUID tronqué à 20 caractères
        task_name = data['task_name']
        task_description = data.get('task_description', '')
        unit_measure = data['unit_measure']
        created_by = data.get('created_by', 'SYSTEM')
        
        with connection.cursor() as cursor:
            # Vérifier si le type de tâche existe déjà (très improbable avec UUID mais bonnes pratiques)
            cursor.execute(
                "SELECT COUNT(*) FROM AM_OBJECTIVE_TYPES WHERE TASK_TYPE_ID = :task_type_id",
                {'task_type_id': task_type_id}
            )
            if cursor.fetchone()[0] > 0:
                # Regénérer un nouvel ID si collision
                task_type_id = str(uuid.uuid4().hex)[:20]
                cursor.execute(
                    "SELECT COUNT(*) FROM AM_OBJECTIVE_TYPES WHERE TASK_TYPE_ID = :task_type_id",
                    {'task_type_id': task_type_id}
                )
                if cursor.fetchone()[0] > 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'Erreur de génération d\'identifiant unique'
                    }, status=500)
            
            # Vérifier la structure de la table
            cursor.execute("""
                SELECT column_name 
                FROM user_tab_columns 
                WHERE table_name = 'AM_OBJECTIVE_TYPES' 
                ORDER BY column_id
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            # Construire la requête dynamiquement
            if 'CREATED_DATE' in columns and 'CREATED_BY' in columns:
                insert_sql = """
                    INSERT INTO AM_OBJECTIVE_TYPES (
                        TASK_TYPE_ID, TASK_NAME, TASK_DESCRIPTION, UNIT_MEASURE,
                        CREATED_DATE, CREATED_BY
                    ) VALUES (
                        :task_type_id, :task_name, :task_description, :unit_measure,
                        SYSDATE, :created_by
                    )
                """
                params = {
                    'task_type_id': task_type_id,
                    'task_name': task_name,
                    'task_description': task_description,
                    'unit_measure': unit_measure,
                    'created_by': created_by
                }
            elif 'CREATED_DATE' in columns:
                insert_sql = """
                    INSERT INTO AM_OBJECTIVE_TYPES (
                        TASK_TYPE_ID, TASK_NAME, TASK_DESCRIPTION, UNIT_MEASURE,
                        CREATED_DATE
                    ) VALUES (
                        :task_type_id, :task_name, :task_description, :unit_measure,
                        SYSDATE
                    )
                """
                params = {
                    'task_type_id': task_type_id,
                    'task_name': task_name,
                    'task_description': task_description,
                    'unit_measure': unit_measure
                }
            else:
                insert_sql = """
                    INSERT INTO AM_OBJECTIVE_TYPES (
                        TASK_TYPE_ID, TASK_NAME, TASK_DESCRIPTION, UNIT_MEASURE
                    ) VALUES (
                        :task_type_id, :task_name, :task_description, :unit_measure
                    )
                """
                params = {
                    'task_type_id': task_type_id,
                    'task_name': task_name,
                    'task_description': task_description,
                    'unit_measure': unit_measure
                }
            
            cursor.execute(insert_sql, params)
            
            return JsonResponse({
                'success': True,
                'message': 'Type de tâche créé avec succès',
                'task_type_id': task_type_id,
                'task_name': task_name
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'type': type(e).__name__
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_task_types(request):
    try:
        with connection.cursor() as cursor:
            # D'abord, vérifier quelles colonnes existent dans la table
            cursor.execute("""
                SELECT column_name 
                FROM user_tab_columns 
                WHERE table_name = 'AM_OBJECTIVE_TYPES' 
                ORDER BY column_id
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            # Construire la requête SELECT dynamiquement
            select_columns = ["TASK_TYPE_ID", "TASK_NAME", "TASK_DESCRIPTION", "UNIT_MEASURE"]
            
            # Ajouter les colonnes optionnelles si elles existent
            if 'CREATED_DATE' in existing_columns:
                select_columns.append("CREATED_DATE")
            if 'CREATED_BY' in existing_columns:
                select_columns.append("CREATED_BY")
            
            # Construire la requête SQL
            sql = f"SELECT {', '.join(select_columns)} FROM AM_OBJECTIVE_TYPES ORDER BY TASK_NAME"
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                # Convertir les dates en string pour JSON
                for key, value in row_dict.items():
                    if hasattr(value, 'isoformat'):
                        row_dict[key] = value.isoformat()
                results.append(row_dict)
            
            return JsonResponse({
                'success': True,
                'task_types': results,
                'total_count': len(results)
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_task_types_bulk(request):
    try:
        data = json.loads(request.body) if request.body else {}
        
        task_types = data.get('task_types', [])
        created_by = data.get('created_by', 'SYSTEM')
        
        if not task_types:
            return JsonResponse({
                'success': False,
                'error': 'Aucun type de tâche fourni'
            }, status=400)
        
        created_count = 0
        errors = []
        
        with connection.cursor() as cursor:
            for task_type in task_types:
                try:
                    required_fields = ['task_type_id', 'task_name', 'unit_measure']
                    missing_fields = [field for field in required_fields if field not in task_type]
                    
                    if missing_fields:
                        errors.append(f"Type {task_type.get('task_type_id', 'inconnu')}: Champs manquants {missing_fields}")
                        continue
                    
                    task_type_id = task_type['task_type_id']
                    task_name = task_type['task_name']
                    task_description = task_type.get('task_description', '')
                    unit_measure = task_type['unit_measure']
                    
                    # Vérifier si le type existe déjà
                    cursor.execute(
                        "SELECT COUNT(*) FROM AM_OBJECTIVE_TYPES WHERE TASK_TYPE_ID = :task_type_id",
                        {'task_type_id': task_type_id}
                    )
                    if cursor.fetchone()[0] > 0:
                        errors.append(f"Type {task_type_id}: existe déjà")
                        continue
                    
                    # Insérer le type de tâche
                    insert_sql = """
                        INSERT INTO AM_OBJECTIVE_TYPES (
                            TASK_TYPE_ID, TASK_NAME, TASK_DESCRIPTION, UNIT_MEASURE,
                            CREATED_DATE, CREATED_BY
                        ) VALUES (
                            :task_type_id, :task_name, :task_description, :unit_measure,
                            SYSDATE, :created_by
                        )
                    """
                    
                    cursor.execute(insert_sql, {
                        'task_type_id': task_type_id,
                        'task_name': task_name,
                        'task_description': task_description,
                        'unit_measure': unit_measure,
                        'created_by': created_by
                    })
                    
                    created_count += 1
                    
                except Exception as e:
                    errors.append(f"Type {task_type.get('task_type_id', 'inconnu')}: {str(e)}")
            
            response_data = {
                'success': True,
                'message': f'{created_count} types de tâches créés avec succès',
                'created_count': created_count
            }
            
            if errors:
                response_data['errors'] = errors
                response_data['partial_success'] = True
            
            return JsonResponse(response_data)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)                        




######## delete ###################

from django.http import JsonResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
@require_http_methods(["POST"])
def truncate_periods(request):
    """
    API pour truncater la table AM_OBJECTIVE_PERIODS
    """
    try:
        with connection.cursor() as cursor:
            # Vérifier d'abord si la table existe
            cursor.execute("""
                SELECT COUNT(*) FROM user_tables 
                WHERE table_name = 'AM_OBJECTIVE_PERIODS'
            """)
            if cursor.fetchone()[0] == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Table AM_OBJECTIVE_PERIODS non trouvée'
                }, status=404)
            
            # Exécuter le TRUNCATE
            cursor.execute("TRUNCATE TABLE AM_OBJECTIVE_PERIODS")
            
            return JsonResponse({
                'success': True,
                'message': 'Table AM_OBJECTIVE_PERIODS truncatée avec succès'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def truncate_task_types(request):
    """
    API pour truncater la table AM_OBJECTIVE_TYPES
    """
    try:
        with connection.cursor() as cursor:
            # Vérifier d'abord si la table existe
            cursor.execute("""
                SELECT COUNT(*) FROM user_tables 
                WHERE table_name = 'AM_OBJECTIVE_TYPES'
            """)
            if cursor.fetchone()[0] == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Table AM_OBJECTIVE_TYPES non trouvée'
                }, status=404)
            
            # Exécuter le TRUNCATE
            cursor.execute("TRUNCATE TABLE AM_OBJECTIVE_TYPES")
            
            return JsonResponse({
                'success': True,
                'message': 'Table AM_OBJECTIVE_TYPES truncatée avec succès'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def truncate_user_objectives(request):
    """
    API pour truncater la table AM_USER_OBJECTIVES
    """
    try:
        with connection.cursor() as cursor:
            # Vérifier d'abord si la table existe
            cursor.execute("""
                SELECT COUNT(*) FROM user_tables 
                WHERE table_name = 'AM_USER_OBJECTIVES'
            """)
            if cursor.fetchone()[0] == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Table AM_USER_OBJECTIVES non trouvée'
                }, status=404)
            
            # Exécuter le TRUNCATE
            cursor.execute("TRUNCATE TABLE AM_USER_OBJECTIVES")
            
            return JsonResponse({
                'success': True,
                'message': 'Table AM_USER_OBJECTIVES truncatée avec succès'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def truncate_monthly_objectives(request):
    """
    API pour truncater la table AM_MONTHLY_OBJECTIVES
    """
    try:
        with connection.cursor() as cursor:
            # Vérifier d'abord si la table existe
            cursor.execute("""
                SELECT COUNT(*) FROM user_tables 
                WHERE table_name = 'AM_MONTHLY_OBJECTIVES'
            """)
            if cursor.fetchone()[0] == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Table AM_MONTHLY_OBJECTIVES non trouvée'
                }, status=404)
            
            # Exécuter le TRUNCATE
            cursor.execute("TRUNCATE TABLE AM_MONTHLY_OBJECTIVES")
            
            return JsonResponse({
                'success': True,
                'message': 'Table AM_MONTHLY_OBJECTIVES truncatée avec succès'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)




@csrf_exempt
@require_http_methods(["GET"])
def get_monthly_objectives(request):
    try:
        with connection.cursor() as cursor:
            # Exécuter directement la requête SELECT *
            cursor.execute("SELECT * FROM AM_MONTHLY_OBJECTIVES")
            
            # Récupérer les noms des colonnes
            columns = [col[0] for col in cursor.description]
            results = []
            
            # Parcourir tous les résultats
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                
                # Convertir les dates en string pour JSON
                for key, value in row_dict.items():
                    if hasattr(value, 'isoformat'):
                        row_dict[key] = value.isoformat()
                
                results.append(row_dict)
            
            return JsonResponse({
                'success': True,
                'data': results,
                'total_count': len(results)
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)