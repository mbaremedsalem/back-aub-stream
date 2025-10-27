from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import paramiko
import re
from datetime import datetime



# Configuration du serveur distant
SERVER_CONFIG = {
    'hostname': '172.16.3.1',
    'username': 'aub',
    'password': 'Megrap2024!',
    'paths': {
        'guichet': '/export/home2/aub/home/avis_aub/guichet',
        'virement_intern': '/export/home2/aub/home/avis_aub/virint',
        'virement_extern': '/export/home2/aub/home/avis_aub/virest',
        'transfer': '/export/home2/aub/home/avis_aub/transfer'
    }
}

def format_date(date_str):
    """Convertit les formats de date."""
    if '-' in date_str:  # Si la date est au format YYYY-MM-DD
        return date_str.replace('-', '')
    elif len(date_str) == 8:  # Si la date est au format YYYYMMDD
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str

def parse_filename(filename):
    """Parse le nom du fichier pour extraire client, nooper et date."""
    pattern = r'(\d+)_(\d+)_(\d{8})\.txt'
    match = re.match(pattern, filename)
    if match:
        return {
            'client': match.group(1),
            'nooper': match.group(2),
            'date_oper': format_date(match.group(3))
        }
    return None

def search_files_in_directory(remote_path, client=None, nooper=None, date_oper=None):
    """Fonction générique pour chercher des fichiers dans un répertoire distant."""
    try:
        # Créer une connexion SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                hostname=SERVER_CONFIG['hostname'],
                username=SERVER_CONFIG['username'],
                password=SERVER_CONFIG['password']
            )

            # Lister les fichiers dans le répertoire
            sftp = ssh.open_sftp()
            files = sftp.listdir(remote_path)

            matching_files = []

            # Vérifier si des critères de recherche sont spécifiés
            has_search_criteria = any([client, nooper, date_oper])

            # Si une date est fournie, la formater correctement
            if date_oper:
                date_oper = format_date(date_oper)

            for filename in files:
                file_info = parse_filename(filename)
                if file_info:
                    # Si aucun critère n'est spécifié, on ajoute tous les fichiers
                    if not has_search_criteria:
                        matches = True
                    else:
                        matches = True
                        if client and client != file_info['client']:
                            matches = False
                        if nooper and nooper != file_info['nooper']:
                            matches = False
                        if date_oper:
                            file_date = format_date(file_info['date_oper'])
                            if date_oper != file_date:
                                matches = False

                    if matches:
                        # Lire le contenu du fichier
                        remote_file_path = f"{remote_path}/{filename}"
                        try:
                            with sftp.open(remote_file_path, 'r') as remote_file:
                                content = remote_file.read().decode('utf-8')
                                matching_files.append({
                                    'filename': filename,
                                    'client': file_info['client'],
                                    'nooper': file_info['nooper'],
                                    'date_oper': file_info['date_oper'],  # Format YYYY-MM-DD pour l'API
                                    'content': content
                                })
                        except Exception as e:
                            print(f"Erreur lors de la lecture du fichier {filename}: {str(e)}")
                            continue

            return {
                'status': 'success',
                'total_files': len(matching_files),
                'has_filters': has_search_criteria,
                'filters_applied': {
                    'client': client,
                    'nooper': nooper,
                    'date_oper': date_oper
                },
                'data': matching_files
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Erreur de connexion au serveur: {str(e)}'
            }

        finally:
            ssh.close()

    except Exception as e:
        return {
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }
from django.core.paginator import Paginator

@require_http_methods(["GET"])
def search_guichet_files(request):
    """API optimisée avec pagination côté serveur"""
    # Récupération des paramètres
    params = request.GET.copy()
    page_number = int(params.get('page', 1))
    
    # Appel de la fonction existante
    result = search_files_in_directory(
        SERVER_CONFIG['paths']['guichet'],
        client=params.get('client'),
        nooper=params.get('nooper'),
        date_oper=params.get('date_oper')
    )
    
    # Gestion des erreurs
    if result['status'] == 'error':
        return JsonResponse(result, status=500)
    
    # Pagination des résultats
    paginator = Paginator(result['data'], 10)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Construction des URLs
    base_url = request.build_absolute_uri(request.path)
    
    def build_page_url(page):
        params['page'] = page
        return f"{base_url}?{params.urlencode()}"
    
    # Préparation de la réponse
    response_data = {
        'status': 'success',
        'count': paginator.count,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'page_size': 10,
            'links': {
                'first': build_page_url(1),
                'last': build_page_url(paginator.num_pages),
                'previous': build_page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                'next': build_page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
            }
        },
        'data': list(page_obj.object_list)
    }
    
    return JsonResponse(response_data)

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def search_virement_intern_files(request):
    """API optimisée pour chercher dans le répertoire virement_intern avec pagination."""
    # Récupération des paramètres
    params = request.GET.copy()
    page_number = int(params.get('page', 1))
    per_page = 10  # Nombre d'éléments par page

    # Appel de la fonction de recherche
    result = search_files_in_directory(
        SERVER_CONFIG['paths']['virement_intern'],
        client=params.get('client'),
        nooper=params.get('nooper'),
        date_oper=params.get('date_oper')
    )

    # Gestion des erreurs
    if result['status'] == 'error':
        return JsonResponse(result, status=500)

    # Pagination des résultats
    paginator = Paginator(result['data'], per_page)
    
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        # Si la page demandée est vide, on retourne la dernière page disponible
        page_obj = paginator.page(paginator.num_pages)

    # Construction des URLs de pagination
    base_url = request.build_absolute_uri(request.path)
    
    def build_page_url(page):
        params['page'] = page
        return f"{base_url}?{params.urlencode()}"

    # Préparation de la réponse
    response_data = {
        'status': 'success',
        'count': paginator.count,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'page_size': per_page,
            'links': {
                'first': build_page_url(1),
                'last': build_page_url(paginator.num_pages),
                'previous': build_page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                'next': build_page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
            }
        },
        'data': list(page_obj.object_list)
    }

    return JsonResponse(response_data)


@require_http_methods(["GET"])
def search_virement_extern_files(request):
    """API optimisée pour virement_extern avec pagination"""
    # Paramètres de pagination
    page_number = int(request.GET.get('page', 1))
    per_page = 10
    
    # Recherche des fichiers
    result = search_files_in_directory(
        SERVER_CONFIG['paths']['virement_extern'],
        client=request.GET.get('client'),
        nooper=request.GET.get('nooper'),
        date_oper=request.GET.get('date_oper')
    )
    
    # Gestion des erreurs
    if result['status'] == 'error':
        return JsonResponse(result, status=500)
    
    # Pagination
    paginator = Paginator(result['data'], per_page)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Construction des URLs
    params = request.GET.copy()
    base_url = request.build_absolute_uri(request.path)
    
    def build_page_url(p):
        params['page'] = p
        return f"{base_url}?{params.urlencode()}"
    
    # Réponse formatée
    return JsonResponse({
        'status': 'success',
        'count': paginator.count,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'page_size': per_page,
            'links': {
                'first': build_page_url(1),
                'last': build_page_url(paginator.num_pages),
                'previous': build_page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                'next': build_page_url(page_obj.next_page_number()) if page_obj.has_next() else None
            }
        },
        'data': list(page_obj.object_list)
    })

@require_http_methods(["GET"])
def search_transfer_files(request):
    """API optimisée pour transfer avec pagination"""
    # Paramètres de pagination
    page_number = int(request.GET.get('page', 1))
    per_page = 10
    
    # Recherche des fichiers
    result = search_files_in_directory(
        SERVER_CONFIG['paths']['transfer'],
        client=request.GET.get('client'),
        nooper=request.GET.get('nooper'),
        date_oper=request.GET.get('date_oper')
    )
    
    # Gestion des erreurs
    if result['status'] == 'error':
        return JsonResponse(result, status=500)
    
    # Pagination
    paginator = Paginator(result['data'], per_page)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Construction des URLs
    params = request.GET.copy()
    base_url = request.build_absolute_uri(request.path)
    
    def build_page_url(p):
        params['page'] = p
        return f"{base_url}?{params.urlencode()}"
    
    # Réponse formatée
    return JsonResponse({
        'status': 'success',
        'count': paginator.count,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'page_size': per_page,
            'links': {
                'first': build_page_url(1),
                'last': build_page_url(paginator.num_pages),
                'previous': build_page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                'next': build_page_url(page_obj.next_page_number()) if page_obj.has_next() else None
            }
        },
        'data': list(page_obj.object_list)
    })
