from rest_framework import serializers
from .models import *
from .models import Notification
        
class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmUsers
        fields = ['id', 'username', 'fullname', 'POST']

class NotificationSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer()
    class Meta:
        model = Notification
        fields = ['id', 'message', 'objet', 'date_created', 'lu', 'user']



# ------------ serializers.py ---------------
class DocumentSerializer(serializers.ModelSerializer):
    createur = SimpleUserSerializer()
    class Meta:
        model = Document
        fields = ['id', 'fichier', 'type_document', 'createur','date_creation']

class CreditSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, write_only=True)

    class Meta:
        model = Credit
        fields = ['montant', 'duree', 'documents']

class ClientSerializer(serializers.ModelSerializer):
    credits = CreditSerializer(many=True)

    class Meta:
        model = Client
        fields = [
            'client_code', 'identifiant', 'pays_naissance', 'date_naissance',
            'nom', 'prenom', 'tel', 'sexe', 'type_document', 'date_expiration',
            'nni', 'date_creation', 'agence', 'type_client', 'credits', 'NIF', 'Address'
        ]

    def create(self, validated_data):
        credits_data = validated_data.pop('credits')
        client = Client.objects.create(**validated_data)
        for credit_data in credits_data:
            documents_data = credit_data.pop('documents')
            credit = Credit.objects.create(client=client, **credit_data)
            for doc in documents_data:
                Document.objects.create(credit=credit, **doc)
        return client

# serializers.py
class CreditSerializer1(serializers.ModelSerializer):
    client = ClientSerializer()
    documents = DocumentSerializer(many=True)

    class Meta:
        model = Credit
        fields = '__all__'

class CreditSerializer2(serializers.ModelSerializer):
    client = ClientSerializer()
    documents = DocumentSerializer(many=True)

    class Meta:
        model = Credit
        fields = '__all__'        


class ValidationCreditSerializer(serializers.ModelSerializer):
    validateur = serializers.StringRelatedField()
    class Meta:
        model = ValidationCredit
        fields = ['validateur', 'poste', 'points', 'date_validation']



# serializers.py




class TypeUploadFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeUploadFile
        fields = ['nom', 'value', 'label', 'type_client']



class ValidationCreditDetailSerializer(serializers.ModelSerializer):
    validateur = SimpleUserSerializer()

    class Meta:
        model = ValidationCredit
        fields = ['validateur', 'poste', 'points', 'date_validation', 'motiv' ,'memo', 'status', 'date_rejet', 'date_creation']



from rest_framework import serializers
from .models import Credit

class CreditSummarySerializer(serializers.ModelSerializer):
    client = ClientSerializer()
    class Meta:
        model = Credit
        fields = [
            'id', 'client', 'montant', 'duree', 'avis', 'memo',
            'date_demande', 'reference', 'status', 'points_valides',
            'motif_rejet', 'date_rejet', 'agence'  # ← ajoutés ici
        ]




