from .models import AmUsersLocal
from rest_framework import serializers
from .models import *



class AmUsersLocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmUsersLocal
        fields = '__all__'  # Inclut tous les champs
        # Ou spécifiez les champs manuellement :
        # fields = ['user_id', 'username', 'email']

class AmUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmUsers
        fields = '__all__'

class ArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Archive
        fields = '__all__'

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = '__all__'        



class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=255, write_only=True)

class PasswordResetSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    new_password = serializers.CharField(max_length=255, write_only=True)


class UserAppPlafondsSerializer(serializers.ModelSerializer):
    app_title = serializers.CharField(source='app_id.title', read_only=True)
    app_code = serializers.CharField(source='app_id.code_app', read_only=True)

    class Meta:
        model = UserAppPlafonds
        fields = ['app_id','user_id','app_title', 'app_code', 'plafond_montant', 
                 'plafond_unite', 'periode_type', 'statut']

####### bakup #########
# SERVER_NAME = '172.16.3.67'
# SERVER_USER = 'aub'
# SERVER_PASSWORD = 'manager1'


####### prod #########
# SERVER_NAME = '172.16.3.1'
# SERVER_USER = 'aub'
# SERVER_PASSWORD = 'Megrap2024!'

####### preprod #########
SERVER_NAME = '192.168.11.11'
SERVER_USER = 'aubpre'
SERVER_PASSWORD = 'manager1'

class UserApplicationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserApplications
        fields = '__all__'

class AssignApplicationsSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    application_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

from rest_framework import serializers
from .models import ArchiveStatus

class ArchiveStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchiveStatus
        fields = ['archive', 'status', 'motif', 'updated_at']
        read_only_fields = ['updated_at']    

class RejectArchiveSerializer(serializers.Serializer):
    archive_id = serializers.IntegerField()
    motif = serializers.CharField()    

class RemoveApplicationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    application_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )    


####### transfer serializers #########
class BeneficiaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Beneficiaire
        fields = '__all__'

class BanqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banque
        fields = '__all__'



# SUPPRIMER CPT_LOCALSerializer car le modèle n'existe plus
# class CPT_LOCALSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CPT_LOCAL
#         fields = '__all__'

# Ajouter ClientMoralSerializer
class ClientMoralSerializer(serializers.Serializer):
    CLIENT = serializers.CharField(max_length=24)
    DEVISE = serializers.CharField(max_length=12)
    COMPTE = serializers.CharField(max_length=44)
    NOM = serializers.CharField(max_length=100)
    RAISON_SOCIALE = serializers.CharField(max_length=960)
    ADRESSE = serializers.CharField(max_length=464)
    NIF = serializers.CharField(max_length=128)
    RC = serializers.CharField(max_length=84)
    AGENCE = serializers.CharField(max_length=20)
    ID_CLIENT_MORAL = serializers.IntegerField()

# Ajouter ClientPhysiqueSerializer
class ClientPhysiqueSerializer(serializers.Serializer):
    CLIENT = serializers.CharField(max_length=24)
    DEVISE = serializers.CharField(max_length=12)
    COMPTE = serializers.CharField(max_length=44)
    NOM = serializers.CharField(max_length=100)
    PRENOM = serializers.CharField(max_length=128)
    NATIONALITE = serializers.CharField(max_length=128)
    NNI = serializers.CharField(max_length=92)
    PASSEPORT = serializers.CharField(max_length=92)
    CARTE_DE_SEJOUR = serializers.CharField(max_length=64)
    AGENCE = serializers.CharField(max_length=20)
    ID_CLIENT_PHYSIQUE = serializers.IntegerField()