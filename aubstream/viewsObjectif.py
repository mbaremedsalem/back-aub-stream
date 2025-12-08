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

#----- delete taske 

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_task_type(request, task_type_id):
    try:
        # Vérifier si l'ID est valide
        if not task_type_id:
            return JsonResponse({
                'success': False,
                'error': 'Task type ID is required'
            }, status=400)
        
        with connection.cursor() as cursor:
            # Vérifier d'abord si la tâche existe
            cursor.execute("""
                SELECT COUNT(*) 
                FROM AM_OBJECTIVE_TYPES 
                WHERE TASK_TYPE_ID = :id
            """, {'id': task_type_id})
            
            if cursor.fetchone()[0] == 0:
                return JsonResponse({
                    'success': False,
                    'error': f'Task type with ID {task_type_id} not found'
                }, status=404)
            
            # Supprimer la tâche
            cursor.execute("""
                DELETE FROM AM_OBJECTIVE_TYPES 
                WHERE TASK_TYPE_ID = :id
            """, {'id': task_type_id})
            
            return JsonResponse({
                'success': True,
                'message': f'Task type with ID {task_type_id} deleted successfully'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

#-------- update taske --------------
@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def update_task_type(request, task_type_id):
    try:
        # Vérifier si l'ID est valide
        if not task_type_id:
            return JsonResponse({
                'success': False,
                'error': 'Task type ID is required'
            }, status=400)
        
        # Lire les données de la requête
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        
        # Vérifier les champs obligatoires
        if 'TASK_NAME' not in data:
            return JsonResponse({
                'success': False,
                'error': 'TASK_NAME is required'
            }, status=400)
        
        with connection.cursor() as cursor:
            # Vérifier d'abord si la tâche existe
            cursor.execute("""
                SELECT COUNT(*) 
                FROM AM_OBJECTIVE_TYPES 
                WHERE TASK_TYPE_ID = :id
            """, {'id': task_type_id})
            
            if cursor.fetchone()[0] == 0:
                return JsonResponse({
                    'success': False,
                    'error': f'Task type with ID {task_type_id} not found'
                }, status=404)
            
            # Vérifier les colonnes existantes dans la table
            cursor.execute("""
                SELECT column_name 
                FROM user_tab_columns 
                WHERE table_name = 'AM_OBJECTIVE_TYPES' 
                ORDER BY column_id
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            print(f"Colonnes existantes: {existing_columns}")  # Pour debug
            
            # Préparer les données de mise à jour
            update_fields = []
            update_values = {'id': task_type_id}
            
            # Champs de base toujours présents
            base_fields = ['TASK_NAME', 'TASK_DESCRIPTION', 'UNIT_MEASURE']
            
            # Construire la liste des champs autorisés en fonction des colonnes existantes
            allowed_fields = []
            for field in base_fields:
                if field in existing_columns:
                    allowed_fields.append(field)
            
            # Ajouter les champs optionnels seulement s'ils existent dans la table
            optional_fields = ['UPDATED_DATE', 'UPDATED_BY']
            for field in optional_fields:
                if field in existing_columns:
                    allowed_fields.append(field)
            
            print(f"Champs autorisés pour mise à jour: {allowed_fields}")  # Pour debug
            
            # Construire la requête de mise à jour dynamiquement
            param_index = 1
            for field in allowed_fields:
                if field in data:
                    param_name = f"val{param_index}"
                    update_fields.append(f"{field} = :{param_name}")
                    update_values[param_name] = data[field]
                    param_index += 1
            
            # Si aucun champ à mettre à jour
            if not update_fields:
                return JsonResponse({
                    'success': False,
                    'error': 'No valid fields to update'
                }, status=400)
            
            # Ajouter la date de mise à jour automatiquement si la colonne existe
            # ET si elle n'a pas été fournie dans les données
            if 'UPDATED_DATE' in existing_columns and 'UPDATED_DATE' not in data:
                update_fields.append("UPDATED_DATE = SYSDATE")
            
            # Construire et exécuter la requête SQL
            sql = f"""
                UPDATE AM_OBJECTIVE_TYPES 
                SET {', '.join(update_fields)}
                WHERE TASK_TYPE_ID = :id
            """
            
            print(f"SQL: {sql}")  # Pour debug
            print(f"Valeurs: {update_values}")  # Pour debug
            
            cursor.execute(sql, update_values)
            
            # Construire dynamiquement la requête SELECT pour récupérer les données mises à jour
            select_columns = ['TASK_TYPE_ID', 'TASK_NAME', 'TASK_DESCRIPTION', 'UNIT_MEASURE']
            
            # Ajouter les colonnes optionnelles si elles existent
            optional_select_columns = ['CREATED_DATE', 'CREATED_BY', 'UPDATED_DATE', 'UPDATED_BY']
            for col in optional_select_columns:
                if col in existing_columns:
                    select_columns.append(col)
            
            select_sql = f"""
                SELECT {', '.join(select_columns)}
                FROM AM_OBJECTIVE_TYPES 
                WHERE TASK_TYPE_ID = :id
            """
            
            cursor.execute(select_sql, {'id': task_type_id})
            
            columns = [col[0] for col in cursor.description]
            result = cursor.fetchone()
            
            if result:
                updated_task = dict(zip(columns, result))
                
                # Convertir les dates en string pour JSON
                for key, value in updated_task.items():
                    if value is not None and hasattr(value, 'isoformat'):
                        updated_task[key] = value.isoformat()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Task type with ID {task_type_id} updated successfully',
                    'task_type': updated_task
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to retrieve updated task'
                }, status=500)
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Erreur détaillée: {error_details}")  # Pour debug
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'details': "Vérifiez les colonnes de la table AM_OBJECTIVE_TYPES"
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



#################### - statistique - ###################

from django.http import JsonResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta

@csrf_exempt
@require_http_methods(["GET"])
def get_objectives_statistics(request):
    """
    API pour récupérer les statistiques globales des objectifs
    """
    try:
        with connection.cursor() as cursor:
            # Récupérer les paramètres de filtrage
            period_type = request.GET.get('period_type', None)
            branch_code = request.GET.get('agence', None)
            start_date = request.GET.get('start_date', None)
            end_date = request.GET.get('end_date', None)
            
            # Statistiques globales
            sql_global = """
                SELECT 
                    COUNT(*) as total_objectives,
                    SUM(CASE WHEN STATUS = 'COMPLETED' THEN 1 ELSE 0 END) as completed_objectives,
                    SUM(CASE WHEN STATUS = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress_objectives,
                    SUM(CASE WHEN STATUS = 'NOT_STARTED' THEN 1 ELSE 0 END) as not_started_objectives,
                    AVG(CASE 
                        WHEN TARGET_VALUE = 0 THEN 0
                        ELSE (ACTUAL_VALUE / TARGET_VALUE) * 100 
                    END) as avg_completion_rate,
                    SUM(TARGET_VALUE) as total_target,
                    SUM(ACTUAL_VALUE) as total_actual
                FROM AM_USER_OBJECTIVES o
                JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
                JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
                WHERE 1=1
            """
            
            params = []
            
            if period_type:
                sql_global += " AND p.PERIOD_TYPE = %s"
                params.append(period_type)
                
            if branch_code:
                sql_global += " AND u.BRANCH_CODE = %s"
                params.append(branch_code)
                
            if start_date:
                sql_global += " AND o.START_DATE >= TO_DATE(%s, 'YYYY-MM-DD')"
                params.append(start_date)
                
            if end_date:
                sql_global += " AND o.END_DATE <= TO_DATE(%s, 'YYYY-MM-DD')"
                params.append(end_date)
            
            cursor.execute(sql_global, params)
            global_stats = cursor.fetchone()
            
            # Statistiques par statut détaillé
            sql_status = """
                SELECT 
                    STATUS,
                    COUNT(*) as count,
                    ROUND(AVG(CASE 
                        WHEN TARGET_VALUE = 0 THEN 0
                        ELSE (ACTUAL_VALUE / TARGET_VALUE) * 100 
                    END), 2) as avg_completion_rate
                FROM AM_USER_OBJECTIVES o
                JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
                JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
                WHERE 1=1
            """
            
            status_params = params.copy()
            
            if period_type:
                sql_status += " AND p.PERIOD_TYPE = %s"
            if branch_code:
                sql_status += " AND u.BRANCH_CODE = %s"
            if start_date:
                sql_status += " AND o.START_DATE >= TO_DATE(%s, 'YYYY-MM-DD')"
            if end_date:
                sql_status += " AND o.END_DATE <= TO_DATE(%s, 'YYYY-MM-DD')"
                
            sql_status += " GROUP BY STATUS ORDER BY COUNT(*) DESC"
            
            cursor.execute(sql_status, status_params)
            status_columns = [col[0] for col in cursor.description]
            status_stats = []
            for row in cursor.fetchall():
                status_stats.append(dict(zip(status_columns, row)))
            
            # Statistiques par type de période
            sql_period = """
                SELECT 
                    p.PERIOD_TYPE,
                    COUNT(*) as count,
                    ROUND(AVG(CASE 
                        WHEN o.TARGET_VALUE = 0 THEN 0
                        ELSE (o.ACTUAL_VALUE / o.TARGET_VALUE) * 100 
                    END), 2) as avg_completion_rate
                FROM AM_USER_OBJECTIVES o
                JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
                JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
                WHERE 1=1
            """
            
            period_params = params.copy()
            
            if branch_code:
                sql_period += " AND u.BRANCH_CODE = %s"
            if start_date:
                sql_period += " AND o.START_DATE >= TO_DATE(%s, 'YYYY-MM-DD')"
            if end_date:
                sql_period += " AND o.END_DATE <= TO_DATE(%s, 'YYYY-MM-DD')"
                
            sql_period += " GROUP BY p.PERIOD_TYPE ORDER BY COUNT(*) DESC"
            
            cursor.execute(sql_period, period_params)
            period_columns = [col[0] for col in cursor.description]
            period_stats = []
            for row in cursor.fetchall():
                period_stats.append(dict(zip(period_columns, row)))
            
            # Statistiques par agence
            sql_branch = """
                SELECT 
                    u.BRANCH_CODE,
                    COUNT(*) as total_objectives,
                    SUM(CASE WHEN o.STATUS = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN o.STATUS = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress,
                    ROUND(AVG(CASE 
                        WHEN o.TARGET_VALUE = 0 THEN 0
                        ELSE (o.ACTUAL_VALUE / o.TARGET_VALUE) * 100 
                    END), 2) as avg_completion_rate,
                    SUM(o.TARGET_VALUE) as total_target,
                    SUM(o.ACTUAL_VALUE) as total_actual
                FROM AM_USER_OBJECTIVES o
                JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
                JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
                WHERE u.BRANCH_CODE IS NOT NULL
            """
            
            branch_params = []
            if period_type:
                sql_branch += " AND p.PERIOD_TYPE = %s"
                branch_params.append(period_type)
            if start_date:
                sql_branch += " AND o.START_DATE >= TO_DATE(%s, 'YYYY-MM-DD')"
                branch_params.append(start_date)
            if end_date:
                sql_branch += " AND o.END_DATE <= TO_DATE(%s, 'YYYY-MM-DD')"
                branch_params.append(end_date)
                
            sql_branch += " GROUP BY u.BRANCH_CODE ORDER BY total_objectives DESC"
            
            cursor.execute(sql_branch, branch_params)
            branch_columns = [col[0] for col in cursor.description]
            branch_stats = []
            for row in cursor.fetchall():
                branch_stats.append(dict(zip(branch_columns, row)))
            
            # Top 10 des meilleurs performeurs
            sql_top_performers = """
                SELECT 
                    u.ID,
                    u.FULLNAME,
                    u.USERCODE,
                    u.BRANCH_CODE,
                    COUNT(*) as total_objectives,
                    SUM(CASE WHEN o.STATUS = 'COMPLETED' THEN 1 ELSE 0 END) as completed_objectives,
                    ROUND(AVG(CASE 
                        WHEN o.TARGET_VALUE = 0 THEN 0
                        ELSE (o.ACTUAL_VALUE / o.TARGET_VALUE) * 100 
                    END), 2) as avg_completion_rate,
                    SUM(o.ACTUAL_VALUE) as total_actual
                FROM AM_USER_OBJECTIVES o
                JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
                JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
                WHERE 1=1
            """
            
            top_params = params.copy()
            
            sql_top_performers += " GROUP BY u.ID, u.FULLNAME, u.USERCODE, u.BRANCH_CODE"
            sql_top_performers += " HAVING COUNT(*) >= 1"
            sql_top_performers += " ORDER BY avg_completion_rate DESC"
            sql_top_performers += " FETCH FIRST 10 ROWS ONLY"
            
            cursor.execute(sql_top_performers, top_params)
            top_columns = [col[0] for col in cursor.description]
            top_performers = []
            for row in cursor.fetchall():
                top_performers.append(dict(zip(top_columns, row)))
            
            # Évolution mensuelle (objectifs créés par mois)
            sql_monthly_trend = """
                SELECT 
                    TO_CHAR(o.CREATED_DATE, 'YYYY-MM') as month_year,
                    COUNT(*) as objectives_created,
                    SUM(CASE WHEN o.STATUS = 'COMPLETED' THEN 1 ELSE 0 END) as completed
                FROM AM_USER_OBJECTIVES o
                JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
                JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
                WHERE o.CREATED_DATE >= ADD_MONTHS(SYSDATE, -12)
            """
            
            trend_params = []
            if period_type:
                sql_monthly_trend += " AND p.PERIOD_TYPE = %s"
                trend_params.append(period_type)
            if branch_code:
                sql_monthly_trend += " AND u.BRANCH_CODE = %s"
                trend_params.append(branch_code)
                
            sql_monthly_trend += " GROUP BY TO_CHAR(o.CREATED_DATE, 'YYYY-MM')"
            sql_monthly_trend += " ORDER BY month_year"
            
            cursor.execute(sql_monthly_trend, trend_params)
            trend_columns = [col[0] for col in cursor.description]
            monthly_trend = []
            for row in cursor.fetchall():
                monthly_trend.append(dict(zip(trend_columns, row)))
            
            # Préparer la réponse
            total_objectives = global_stats[0] if global_stats else 0
            completed_objectives = global_stats[1] if global_stats else 0
            completion_rate = (completed_objectives / total_objectives * 100) if total_objectives > 0 else 0
            
            response_data = {
                'success': True,
                'summary': {
                    'total_objectives': total_objectives,
                    'completed_objectives': completed_objectives,
                    'in_progress_objectives': global_stats[2] if global_stats else 0,
                    'not_started_objectives': global_stats[3] if global_stats else 0,
                    'overall_completion_rate': round(completion_rate, 2),
                    'avg_completion_percentage': round(global_stats[4] or 0, 2) if global_stats else 0,
                    'total_target_value': float(global_stats[5] or 0),
                    'total_actual_value': float(global_stats[6] or 0),
                    'performance_gap': float((global_stats[5] or 0) - (global_stats[6] or 0))
                },
                'by_status': status_stats,
                'by_period_type': period_stats,
                'by_branch': branch_stats,
                'top_performers': top_performers,
                'monthly_trend': monthly_trend,
                'filters_applied': {
                    'period_type': period_type,
                    'agence': branch_code,
                    'start_date': start_date,
                    'end_date': end_date
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return JsonResponse(response_data)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'type': type(e).__name__
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_user_statistics(request, user_id=None):
    """
    API pour récupérer les statistiques individuelles d'un utilisateur
    """
    try:
        with connection.cursor() as cursor:
            # Si user_id n'est pas fourni dans l'URL, chercher dans les paramètres
            if user_id is None:
                user_id = request.GET.get('user_id')
            
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'error': 'user_id est requis'
                }, status=400)
            
            # Vérifier que l'utilisateur existe
            cursor.execute(
                "SELECT ID, FULLNAME, USERCODE, BRANCH_CODE FROM AM_USERS_LOCAL WHERE ID = %s",
                [user_id]
            )
            user_row = cursor.fetchone()
            if not user_row:
                return JsonResponse({
                    'success': False,
                    'error': 'Utilisateur non trouvé'
                }, status=404)
            
            user_info = {
                'id': user_row[0],
                'fullname': user_row[1],
                'usercode': user_row[2],
                'branch_code': user_row[3]
            }
            
            # Statistiques globales de l'utilisateur
            sql_user_stats = """
                SELECT 
                    COUNT(*) as total_objectives,
                    SUM(CASE WHEN STATUS = 'COMPLETED' THEN 1 ELSE 0 END) as completed_objectives,
                    SUM(CASE WHEN STATUS = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress_objectives,
                    SUM(CASE WHEN STATUS = 'NOT_STARTED' THEN 1 ELSE 0 END) as not_started_objectives,
                    AVG(CASE 
                        WHEN TARGET_VALUE = 0 THEN 0
                        ELSE (ACTUAL_VALUE / TARGET_VALUE) * 100 
                    END) as avg_completion_rate,
                    SUM(TARGET_VALUE) as total_target,
                    SUM(ACTUAL_VALUE) as total_actual,
                    MIN(START_DATE) as first_objective_date,
                    MAX(END_DATE) as last_objective_date
                FROM AM_USER_OBJECTIVES
                WHERE USER_ID = %s
            """
            
            cursor.execute(sql_user_stats, [user_id])
            user_stats = cursor.fetchone()
            
            # Objectifs par type de période
            sql_period_stats = """
                SELECT 
                    p.PERIOD_TYPE,
                    COUNT(*) as count,
                    ROUND(AVG(CASE 
                        WHEN o.TARGET_VALUE = 0 THEN 0
                        ELSE (o.ACTUAL_VALUE / o.TARGET_VALUE) * 100 
                    END), 2) as avg_completion_rate,
                    SUM(o.TARGET_VALUE) as total_target,
                    SUM(o.ACTUAL_VALUE) as total_actual
                FROM AM_USER_OBJECTIVES o
                JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
                WHERE o.USER_ID = %s
                GROUP BY p.PERIOD_TYPE
                ORDER BY count DESC
            """
            
            cursor.execute(sql_period_stats, [user_id])
            period_columns = [col[0] for col in cursor.description]
            user_period_stats = []
            for row in cursor.fetchall():
                user_period_stats.append(dict(zip(period_columns, row)))
            
            # Objectifs par type de tâche
            sql_task_stats = """
                SELECT 
                    ot.TASK_NAME,
                    ot.UNIT_MEASURE,
                    COUNT(*) as count,
                    ROUND(AVG(CASE 
                        WHEN o.TARGET_VALUE = 0 THEN 0
                        ELSE (o.ACTUAL_VALUE / o.TARGET_VALUE) * 100 
                    END), 2) as avg_completion_rate,
                    SUM(o.TARGET_VALUE) as total_target,
                    SUM(o.ACTUAL_VALUE) as total_actual
                FROM AM_USER_OBJECTIVES o
                JOIN AM_OBJECTIVE_TYPES ot ON o.TASK_TYPE_ID = ot.TASK_TYPE_ID
                WHERE o.USER_ID = %s
                GROUP BY ot.TASK_NAME, ot.UNIT_MEASURE
                ORDER BY count DESC
            """
            
            cursor.execute(sql_task_stats, [user_id])
            task_columns = [col[0] for col in cursor.description]
            user_task_stats = []
            for row in cursor.fetchall():
                user_task_stats.append(dict(zip(task_columns, row)))
            
            # Performance mensuelle
            sql_monthly_performance = """
                SELECT 
                    TO_CHAR(o.CREATED_DATE, 'YYYY-MM') as month_year,
                    COUNT(*) as objectives_created,
                    SUM(CASE WHEN o.STATUS = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                    ROUND(AVG(CASE 
                        WHEN o.TARGET_VALUE = 0 THEN 0
                        ELSE (o.ACTUAL_VALUE / o.TARGET_VALUE) * 100 
                    END), 2) as avg_completion_rate
                FROM AM_USER_OBJECTIVES o
                WHERE o.USER_ID = %s AND o.CREATED_DATE >= ADD_MONTHS(SYSDATE, -6)
                GROUP BY TO_CHAR(o.CREATED_DATE, 'YYYY-MM')
                ORDER BY month_year
            """
            
            cursor.execute(sql_monthly_performance, [user_id])
            monthly_columns = [col[0] for col in cursor.description]
            monthly_performance = []
            for row in cursor.fetchall():
                monthly_performance.append(dict(zip(monthly_columns, row)))
            
            # Préparer la réponse
            total_user_objectives = user_stats[0] if user_stats else 0
            completed_user_objectives = user_stats[1] if user_stats else 0
            user_completion_rate = (completed_user_objectives / total_user_objectives * 100) if total_user_objectives > 0 else 0
            
            response_data = {
                'success': True,
                'user_info': user_info,
                'summary': {
                    'total_objectives': total_user_objectives,
                    'completed_objectives': completed_user_objectives,
                    'in_progress_objectives': user_stats[2] if user_stats else 0,
                    'not_started_objectives': user_stats[3] if user_stats else 0,
                    'completion_rate': round(user_completion_rate, 2),
                    'avg_completion_percentage': round(user_stats[4] or 0, 2) if user_stats else 0,
                    'total_target_value': float(user_stats[5] or 0),
                    'total_actual_value': float(user_stats[6] or 0),
                    'performance_gap': float((user_stats[5] or 0) - (user_stats[6] or 0)),
                    'first_objective_date': user_stats[7].isoformat() if user_stats and user_stats[7] else None,
                    'last_objective_date': user_stats[8].isoformat() if user_stats and user_stats[8] else None
                },
                'by_period_type': user_period_stats,
                'by_task_type': user_task_stats,
                'monthly_performance': monthly_performance
            }
            
            return JsonResponse(response_data)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'type': type(e).__name__
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_comparison_statistics(request):
    """
    API pour comparer les performances entre agences ou périodes - VERSION DEBUG
    """
    try:
        with connection.cursor() as cursor:
            comparison_type = request.GET.get('type', 'branches')
            metric = request.GET.get('metric', 'completion_rate')
            
            print(f"Comparison type: {comparison_type}")
            print(f"Metric: {metric}")
            
            if comparison_type == 'branches':
                sql = """
                    SELECT 
                        u.BRANCH_CODE,
                        COUNT(*) as total_objectives,
                        ROUND(AVG(CASE 
                            WHEN o.TARGET_VALUE = 0 THEN 0
                            ELSE (o.ACTUAL_VALUE / o.TARGET_VALUE) * 100 
                        END), 2) as avg_completion_rate,
                        SUM(CASE WHEN o.STATUS = 'COMPLETED' THEN 1 ELSE 0 END) as completed_count,
                        SUM(o.TARGET_VALUE) as total_target,
                        SUM(o.ACTUAL_VALUE) as total_actual
                    FROM AM_USER_OBJECTIVES o
                    JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
                    WHERE u.BRANCH_CODE IS NOT NULL
                    GROUP BY u.BRANCH_CODE
                    ORDER BY total_objectives DESC
                """
            else:
                sql = """
                    SELECT 
                        p.PERIOD_TYPE,
                        COUNT(*) as total_objectives,
                        ROUND(AVG(CASE 
                            WHEN o.TARGET_VALUE = 0 THEN 0
                            ELSE (o.ACTUAL_VALUE / o.TARGET_VALUE) * 100 
                        END), 2) as avg_completion_rate,
                        SUM(CASE WHEN o.STATUS = 'COMPLETED' THEN 1 ELSE 0 END) as completed_count,
                        SUM(o.TARGET_VALUE) as total_target,
                        SUM(o.ACTUAL_VALUE) as total_actual
                    FROM AM_USER_OBJECTIVES o
                    JOIN AM_OBJECTIVE_PERIODS p ON o.PERIOD_ID = p.PERIOD_ID
                    GROUP BY p.PERIOD_TYPE
                    ORDER BY total_objectives DESC
                """
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            print(f"Columns returned: {columns}")
            
            results = []
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                print(f"Row data: {row_dict}")
                
                # Convertir les décimales en float pour JSON
                for key, value in row_dict.items():
                    if hasattr(value, 'as_tuple'):  # Décimal
                        row_dict[key] = float(value)
                
                # Valeurs par défaut pour éviter les KeyError
                row_dict.setdefault('avg_completion_rate', 0)
                row_dict.setdefault('total_objectives', 0)
                row_dict.setdefault('total_actual', 0)
                
                results.append(row_dict)
            
            print(f"Total results: {len(results)}")
            
            # Trier selon la métrique
            if results:
                try:
                    if metric == 'quantity':
                        results.sort(key=lambda x: x.get('total_objectives', 0), reverse=True)
                    elif metric == 'performance':
                        results.sort(key=lambda x: x.get('total_actual', 0), reverse=True)
                    else:  # completion_rate
                        results.sort(key=lambda x: x.get('avg_completion_rate', 0), reverse=True)
                except Exception as sort_error:
                    print(f"Sort error: {sort_error}")
            
            return JsonResponse({
                'success': True,
                'comparison_type': comparison_type,
                'metric': metric,
                'data': results,
                'debug_info': {
                    'columns_found': columns,
                    'results_count': len(results),
                    'first_result_keys': list(results[0].keys()) if results else []
                }
            })
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in comparison API: {error_details}")
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'details': error_details,
            'comparison_type': request.GET.get('type', 'branches'),
            'metric': request.GET.get('metric', 'completion_rate')
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_dashboard_stats(request):
    """
    API pour les statistiques du dashboard (résumé rapide)
    """
    try:
        with connection.cursor() as cursor:
            # Statistiques très rapides pour le dashboard
            sql_dashboard = """
                SELECT 
                    -- Total objectifs
                    (SELECT COUNT(*) FROM AM_USER_OBJECTIVES) as total_objectives,
                    
                    -- Objectifs complétés ce mois
                    (SELECT COUNT(*) FROM AM_USER_OBJECTIVES 
                     WHERE STATUS = 'COMPLETED' 
                     AND EXTRACT(MONTH FROM CREATED_DATE) = EXTRACT(MONTH FROM SYSDATE)
                     AND EXTRACT(YEAR FROM CREATED_DATE) = EXTRACT(YEAR FROM SYSDATE)) as completed_this_month,
                    
                    -- Objectifs en cours
                    (SELECT COUNT(*) FROM AM_USER_OBJECTIVES WHERE STATUS = 'IN_PROGRESS') as in_progress,
                    
                    -- Nouveaux objectifs ce mois
                    (SELECT COUNT(*) FROM AM_USER_OBJECTIVES 
                     WHERE EXTRACT(MONTH FROM CREATED_DATE) = EXTRACT(MONTH FROM SYSDATE)
                     AND EXTRACT(YEAR FROM CREATED_DATE) = EXTRACT(YEAR FROM SYSDATE)) as new_this_month,
                    
                    -- Taux de completion moyen
                    (SELECT ROUND(AVG(CASE 
                         WHEN TARGET_VALUE = 0 THEN 0
                         ELSE (ACTUAL_VALUE / TARGET_VALUE) * 100 
                     END), 2) FROM AM_USER_OBJECTIVES) as avg_completion_rate,
                    
                    -- Total utilisateurs avec objectifs
                    (SELECT COUNT(DISTINCT USER_ID) FROM AM_USER_OBJECTIVES) as active_users,
                    
                    -- Total agences avec objectifs
                    (SELECT COUNT(DISTINCT u.BRANCH_CODE) 
                     FROM AM_USER_OBJECTIVES o 
                     JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID 
                     WHERE u.BRANCH_CODE IS NOT NULL) as active_branches
                FROM DUAL
            """
            
            cursor.execute(sql_dashboard)
            dashboard_stats = cursor.fetchone()
            
            # Derniers objectifs complétés
            sql_recent_completed = """
                SELECT 
                    o.OBJECTIVE_ID,
                    u.FULLNAME,
                    ot.TASK_NAME,
                    o.ACTUAL_VALUE,
                    o.TARGET_VALUE,
                    ROUND((o.ACTUAL_VALUE / o.TARGET_VALUE) * 100, 2) as completion_rate,
                    o.END_DATE
                FROM AM_USER_OBJECTIVES o
                JOIN AM_USERS_LOCAL u ON o.USER_ID = u.ID
                JOIN AM_OBJECTIVE_TYPES ot ON o.TASK_TYPE_ID = ot.TASK_TYPE_ID
                WHERE o.STATUS = 'COMPLETED'
                ORDER BY o.END_DATE DESC
                FETCH FIRST 5 ROWS ONLY
            """
            
            cursor.execute(sql_recent_completed)
            recent_columns = [col[0] for col in cursor.description]
            recent_completed = []
            for row in cursor.fetchall():
                recent_completed.append(dict(zip(recent_columns, row)))
            
            return JsonResponse({
                'success': True,
                'dashboard_stats': {
                    'total_objectives': dashboard_stats[0],
                    'completed_this_month': dashboard_stats[1],
                    'in_progress_objectives': dashboard_stats[2],
                    'new_this_month': dashboard_stats[3],
                    'avg_completion_rate': dashboard_stats[4] or 0,
                    'active_users': dashboard_stats[5],
                    'active_branches': dashboard_stats[6]
                },
                'recent_completed': recent_completed,
                'last_updated': datetime.now().isoformat()
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


from django.http import JsonResponse
from django.db import connections
from datetime import datetime
import json
from django.views.decorators.csrf import csrf_exempt
import logging

# Configuration du logging pour le débogage
logger = logging.getLogger(__name__)
@csrf_exempt
def comptes_negatifs_api_safe(request):
    """
    Version avec conversion explicite des dates
    """
    try:
        logger.info("Début de l'exécution de la requête Oracle avec dates sécurisées")
        
        # Utiliser TO_DATE pour toutes les dates
        sql_query = """
        Select 
            c.client,
            c.compte,
            c.agence, 
            c.devise,
            m.nom,
            (select i.numid from titu t, idp i where t.client = m.client and t.idp = i.idp ) NNI,
            (select idm.tin1 from titu t , cli m1, idm where t.client = m1.client and  t.client = m.client and t.idm = idm.idm and nvl(t.valide,'N') = 'V' ) RC,
            (select idm.rcsno from titu t , cli m1, idm where t.client = m1.client and  t.client = m.client and t.idm = idm.idm and nvl(t.valide,'N') = 'V' ) NIF,
            (select ageclib from agec  where agec.agec = m.agec) Type,
            (select f.proflib from titu t ,idp i, prof f where t.client = m.client and t.idp = i.idp and i.profession = f.prof) Profession,
            (select p.apelib from codape p  where m.codape = p.codape ) Secteur_activité,
            (select libelle from ncglib b where b.ncg = c.ncg) Produit_compte,
            c.datouv date_ouverture,
            c.datfrm date_fermeture,
            c.expl ,
            s.posdev Solde,
            (select sum(t.mntdev) from mvtc t  
             where t.compte = c.compte 
             and t.mntdev >= 0  
             and t.datoper between TO_DATE('01/03/2025', 'DD/MM/YYYY') 
             and TO_DATE('30/06/2025', 'DD/MM/YYYY')) Tot_Mvt_credit,
            
            case 
                When (select max(t.datoper) from mvtc t where t.compte = c.compte and t.mntdev >= 0) is null 
                then (select max(t1.datoper) from mvtc1 t1 where t1.compte = c.compte and t1.mntdev >= 0)
                When (select max(t.datoper) from mvtc t where t.compte = c.compte and t.mntdev >= 0) is null 
                and (select max(t1.datoper) from mvtc1 t1 where t1.compte = c.compte and t1.mntdev >= 0) is null 
                then (select max(t23.datoper) from mvtc23 t23 where t23.compte = c.compte and t23.mntdev >= 0)
                Else (select max(t.datoper) from mvtc t where t.compte = c.compte and t.mntdev >= 0) 
            End Date_dernier_credit,

            case 
                When (select max(t.datoper) from mvtc t where t.compte = c.compte and t.mntdev < 0) is null 
                then (select max(t1.datoper) from mvtc1 t1 where t1.compte = c.compte and t1.mntdev < 0)
                When (select max(t.datoper) from mvtc t where t.compte = c.compte and t.mntdev < 0) is null 
                and (select max(t1.datoper) from mvtc1 t1 where t1.compte = c.compte and t1.mntdev < 0) is null 
                then (select max(t23.datoper) from mvtc23 t23 where t23.compte = c.compte and t23.mntdev < 0)
                Else (select max(t.datoper) from mvtc t where t.compte = c.compte and t.mntdev < 0) 
            End date_dernier_debit

        from cpt c, cli m ,sldoper s 
        where c.client = m.client 
        and c.compte = s.compte 
        and s.datpos = TO_DATE('31/08/2025', 'DD/MM/YYYY')
        and c.ncg like '210%'
        
        and c.ncg <> '210400'
        order by c.client
        """
        
        # Utiliser la connexion PROD directement
        connection = connections['PROD']
        
        with connection.cursor() as cursor:
            logger.info(f"Exécution de la requête sur la base PROD")
            cursor.execute(sql_query)
            
            # Récupérer les noms des colonnes
            columns = [col[0] for col in cursor.description]
            logger.info(f"Colonnes récupérées: {columns}")
            
            # Convertir les résultats en liste de dictionnaires
            results = []
            for row in cursor.fetchall():
                row_dict = {}
                for i, value in enumerate(row):
                    column_name = columns[i]
                    
                    # Convertir les types Oracle spécifiques
                    if hasattr(value, 'read'):  # Pour les CLOB/BLOB
                        try:
                            value = value.read()
                        except:
                            value = str(value)
                    elif isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif hasattr(value, 'strftime'):  # Autres types date
                        try:
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            value = str(value)
                    elif value is None:
                        value = None
                    
                    row_dict[column_name] = value
                
                results.append(row_dict)
            
            logger.info(f"{len(results)} enregistrements récupérés")
            
            # Retourner la réponse JSON
            response_data = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'data_count': len(results),
                'data': results
            }
            
            return JsonResponse(response_data, safe=False, json_dumps_params={'ensure_ascii': False})
            
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500, json_dumps_params={'ensure_ascii': False})