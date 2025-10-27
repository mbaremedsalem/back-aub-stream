from rest_framework import serializers
from .models import *
from decimal import Decimal

class BeneficiaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Beneficiaire
        fields = '__all__'

class BanqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banque
        fields = '__all__'

class CPT_LOCALSerializer(serializers.ModelSerializer):
    class Meta:
        model = CPT_LOCAL
        fields = '__all__'
    
    def to_representation(self, instance):
        """Convertit les Decimal en string pour éviter les erreurs de conversion"""
        ret = super().to_representation(instance)
        for field in ret:
            if isinstance(ret[field], Decimal):
                ret[field] = str(ret[field])  # Convertit Decimal en string
        return ret


### configure real #########   
class ClientPhysiqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientPhysique
        fields = '__all__'  # Inclut tous les champs

class ClientMoralSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientMoral
        fields = '__all__'  # Inclut tous les champs        

class TransferSerializer(serializers.ModelSerializer):    
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = '__all__'

    def get_created_by(self, obj):
        from .models import AmUsers
        from .serializers import AmUsersSerializer
        try:
            user = obj.created_by
            if user is None:
                return None
            return AmUsersSerializer(user).data
        except AmUsers.DoesNotExist:
            return None
            
class TransferSerializer1(serializers.ModelSerializer):    
    created_by = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = '__all__'

    def get_created_by(self, obj):
        from .models import AmUsers
        from .serializers import AmUsersSerializer
        try:
            user = obj.created_by
            if user is None:
                return None
            return AmUsersSerializer(user).data
        except AmUsers.DoesNotExist:
            return None   


    def get_client(self, obj):
        try:
            # Client Physique
            if obj.type_client == 'PHYSIQUE' and obj.id_client:
                from .models import ClientPhysique
                client = ClientPhysique.objects.get(id_client_physique=obj.id_client)
                return {
                        'type': 'PHYSIQUE',
                        'id_client_physique': client.id_client_physique,
                        'nature_de_compte': client.nature_de_compte,
                        'compte': client.compte,
                        'devise': client.devise,
                        'client': client.client,
                        'identifiant': client.identifiant,
                        'nni': client.nni,
                        'passport': client.passport,
                        'carte_sejour': client.carte_sejour,
                        'nationalite': client.nationalite,
                        'agence': client.agence,
                        'paysnais': client.paysnais,
                        'datnais': client.datnais,
                        'nom': client.nom,
                        'prenom': client.prenom,
                        'tel': client.tel,
                        'sexe': client.sexe,
                        'type_document': client.type_document
                }
            
            # Client Moral
            elif obj.type_client == 'MORAL' and obj.id_client:
                from .models import ClientMoral
                client = ClientMoral.objects.get(id_client_moral=obj.id_client)
                return {
                        'type': 'MORAL',
                        'id_client_moral': client.id_client_moral,
                        'client': client.client,
                        'nature_de_compte': client.nature_de_compte,
                        'compte': client.compte,
                        'devise': client.devise,
                        'nom': client.nom,
                        'agence': client.agence,
                        'raison_sociale': client.raison_sociale,
                        'nif': client.nif,
                        'rc': client.rc,
                        'adresse': client.adresse,
                        'tel': client.tel
                }
                
        except (ClientPhysique.DoesNotExist, ClientMoral.DoesNotExist):
            return None
        except Exception as e:
            # Log l'erreur si nécessaire
            print(f"Error getting client details: {str(e)}")
            return None
        
        return None
        
# class TransferSerializer1(serializers.ModelSerializer):    
#     created_by = serializers.SerializerMethodField()

#     class Meta:
#         model = Transfer
#         fields = '__all__'

#     def get_created_by(self, obj):
#         from .models import AmUsers
#         from .serializers import AmUsersSerializer
#         try:
#             user = obj.created_by
#             if user is None:
#                 return None
#             return AmUsersSerializer(user).data
#         except AmUsers.DoesNotExist:
#             return None

#     def get_client_physique(self, obj):
#         from .models import ClientPhysique
#         try:
#             user = obj.created_by
#             if user is None:
#                 return None
#             return ClientPhysiqueSerializer(user).data
#         except ClientPhysique.DoesNotExist:
#             return None  

#     def get_client_morale(self, obj):
#         from .models import ClientMoral
#         try:
#             user = obj.created_by
#             if user is None:
#                 return None
#             return ClientMoralSerializer(user).data
#         except ClientMoral.DoesNotExist:
#             return None                        


class HistoriqueTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoriqueTransfer
        fields = '__all__'

