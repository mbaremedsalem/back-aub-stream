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




####### bakup #########
SERVER_NAME = '172.16.3.67'
SERVER_USER = 'aub'
SERVER_PASSWORD = 'manager1'


####### prod #########
SERVER_NAME_P = '172.16.3.1'
SERVER_USER_P = 'aub'
SERVER_PASSWORD_P = 'Megrap2024!'

####### preprod #########
# SERVER_NAME = '192.168.11.11'
# SERVER_USER = 'aubpre'
# SERVER_PASSWORD = 'manager1'

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