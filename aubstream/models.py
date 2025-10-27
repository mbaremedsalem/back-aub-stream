# models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

class AmUsersLocal(AbstractBaseUser):
    username = models.CharField(max_length=50, primary_key=True, db_column='USERNAME')
    password = models.CharField(max_length=128, db_column='PASSWORD')
    fullname = models.CharField(max_length=100, db_column='FULLNAME')
    
    # Champs requis pour Django (mais non stockés en base)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Désactiver les vérifications de champs inexistants
    last_login = None
    date_joined = None

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = '"SYSTEM"."AM_USERS_LOCAL"'
        managed = False  # Important pour les tables existantes

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

class AmUsers(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    username = models.CharField(max_length=100, unique=True)
    fullname = models.CharField(max_length=255)
    usercode = models.CharField(max_length=100)
    signature_weight = models.IntegerField(default=0)
    authorization_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    mgr_usercode = models.CharField(max_length=100, null=True, blank=True)
    service_code = models.CharField(max_length=50)
    branch_code = models.CharField(max_length=50)
    client_id = models.CharField(max_length=100, null=True, blank=True)
    account_ledger_group_access = models.CharField(max_length=100)
    oper_access_level = models.CharField(max_length=1)
    profile_interface = models.CharField(max_length=100, null=True, blank=True)
    status_code = models.CharField(max_length=1)
    dtype = models.CharField(max_length=50)
    access_time1 = models.CharField(max_length=100, null=True, blank=True)
    access_time2 = models.CharField(max_length=100, null=True, blank=True)
    activation_date = models.DateTimeField(null=True, blank=True)
    deactivation_date = models.DateTimeField(null=True, blank=True)
    advice_printer_code = models.CharField(max_length=50, null=True, blank=True)
    report_printer_code = models.CharField(max_length=50, null=True, blank=True)
    language_code = models.CharField(max_length=2)
    email = models.EmailField(null=True, blank=True)
    sys_created_date = models.DateTimeField(auto_now_add=True)
    sys_created_by = models.CharField(max_length=100)
    sys_updated_date = models.DateTimeField(auto_now=True)
    sys_updated_by = models.CharField(max_length=100)
    init_usercode_for_mod = models.CharField(max_length=100, null=True, blank=True)
    profile_id = models.CharField(max_length=100, null=True, blank=True)
    password = models.CharField(max_length=255)
    is_password_admin = models.BooleanField(default=False)
    unsuccessful_login_number = models.IntegerField(default=0)
    last_password_change_date = models.DateTimeField(null=True, blank=True)
    last_login_date = models.DateTimeField(null=True, blank=True)
    sys_version_number = models.IntegerField()
    showinexpllov_flag = models.BooleanField(default=True)
    showinexplintrlov_flag = models.BooleanField(default=True)
    showinoriginlov_flag = models.BooleanField(default=True)
    showinrelmanagerlov_flag = models.BooleanField(default=True)
    dotmatrix_printer_code = models.CharField(max_length=50, null=True, blank=True)
    permissionsonauth = models.CharField(max_length=255, null=True, blank=True)
    employment_date = models.DateTimeField(null=True, blank=True)
    market = models.CharField(max_length=100, null=True, blank=True)
    desk = models.CharField(max_length=100, null=True, blank=True)
    authmnt = models.CharField(max_length=100, null=True, blank=True)
    dealer_authorization = models.CharField(max_length=100, null=True, blank=True)
    allow_holiday1_flag = models.BooleanField(default=False)
    allow_holiday2_flag = models.BooleanField(default=False)
    number_access_days = models.IntegerField(null=True, blank=True)
    permissionsonanauth = models.CharField(max_length=255, null=True, blank=True)
    office_phone = models.CharField(max_length=50, null=True, blank=True)
    fdsfiche = models.CharField(max_length=100, null=True, blank=True)
    fdssld = models.CharField(max_length=100, null=True, blank=True)
    fdsmvt = models.CharField(max_length=100, null=True, blank=True)
    Role= models.CharField(max_length=100, null=True, blank=True)
    POST= models.CharField(max_length=100, null=True, blank=True)
    POID= models.IntegerField(default=0)
    CONSULTE= models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = 'AM_USERS_LOCAL'
        managed = False

    def __str__(self):
        return self.username

    @property
    def id(self):
        return self.username

    def get_username(self):
        return self.username

    # Required for JWT token authentication
    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

class UserAppPlafonds(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    user_id = models.ForeignKey(AmUsers, on_delete=models.CASCADE, db_column='USER_ID')
    app_id = models.ForeignKey('Application', on_delete=models.CASCADE, db_column='APP_ID')
    plafond_montant = models.IntegerField(default=0)
    plafond_unite = models.CharField(max_length=10, default='EUR')
    periode_type = models.CharField(max_length=20, default='MENSUEL')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)
    statut = models.CharField(max_length=20, default='ACTIF')
    sys_created_by = models.CharField(max_length=144, default='SYSTEM')
    sys_updated_by = models.CharField(max_length=144, default='SYSTEM')

    class Meta:
        db_table = 'USER_APP_PLAFONDS'
        managed = False
        unique_together = ('user_id', 'app_id')

    def __str__(self):
        return f"{self.user_id.username} - {self.app_id.title} - {self.plafond_montant}"

class Archive(models.Model):
    doc_type = models.CharField(max_length=255, null=True, blank=True)  # DOC_TYPE
    doc_id = models.CharField(max_length=255, null=True, blank=True)  # DOC_ID
    doc_date = models.DateField(null=True, blank=True)  # DOC_DATE
    debtor_account = models.CharField(max_length=255, null=True, blank=True)  # DEBTOR_ACCOUNT
    c_branch = models.CharField(max_length=255, null=True, blank=True)  # C_BRANCH
    creditor_account = models.CharField(max_length=255, null=True, blank=True)  # CREDITOR_ACCOUNT
    c_name = models.CharField(max_length=255, null=True, blank=True)  # C_NAME
    type_dc = models.CharField(max_length=255, null=True, blank=True)  # TYPE_DC
    summa = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # SUMMA
    kod = models.CharField(max_length=255, null=True, blank=True)  # KOD
    beneficiary_bic = models.CharField(max_length=255, null=True, blank=True)  # Beneficiary Bic
    description = models.TextField(null=True, blank=True)  # Description
    created_at = models.DateTimeField(auto_now_add=True)  # Date d'ajout automatique
    posted = models.BooleanField(default=False)
  
    class Meta:
        db_table = 'Archive'
        managed = False  

    def __str__(self):
        return f"DOC_ID: {self.doc_id}, SUMMA: {self.summa}"   
           

class Application(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)  # DOC_TYPE
    description = models.CharField(max_length=255, null=True, blank=True)  # DOC_ID
    date_creation = models.DateField(null=True, blank=True)  # DOC_DATE
    date_update = models.DateField(null=True, blank=True)  # DOC_DATE
    version = models.CharField(max_length=255, null=True, blank=True)  # Beneficiary Bic

    class Meta:
        db_table = 'Application'
        managed = False  

    def __str__(self):
        return f"TITLE: {self.title}, VERSION: {self.version}"   
    

class User_Applications(models.Model):
    user_id = models.CharField(max_length=255, null=True, blank=True)  # DOC_TYPE
    application_id = models.CharField(max_length=255, null=True, blank=True)  # DOC_ID
    date_creation = models.DateField(null=True, blank=True)  # DOC_DATE
    date_update = models.DateField(null=True, blank=True)  # DOC_DATE
    version = models.CharField(max_length=255, null=True, blank=True)  # Beneficiary Bic

    class Meta:
        db_table = 'User_Applications'
        managed = False  

    def __str__(self):
        return f"DOC_ID: {self.doc_id}, SUMMA: {self.summa}"   

class UserApplications(models.Model):
    user = models.ForeignKey(AmUsers, db_column='user_id', to_field='username', on_delete=models.CASCADE)
    application = models.ForeignKey('Application', db_column='application_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'User_Applications'
        unique_together = (('user', 'application'),)
        managed = False
        auto_created = True

    def __str__(self):
        return f"{self.user} - {self.application}"




class ArchiveStatus(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmé'),
        ('rejected', 'Rejeté'),
    ]
    
    archive = models.OneToOneField(
        Archive, 
        on_delete=models.CASCADE,
        related_name='status',
        primary_key=True
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='confirmed'
    )
    motif = models.TextField(
        blank=True,
        null=True,
        help_text="Raison du rejet si le statut est 'rejeté'"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Archive_Status'
        managed = False 

    def __str__(self):
        return f"{self.archive} - {self.get_status_display()}"


########################## ------------------ transfere ----------------------------------------######################################
class Beneficiaire(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID_BENEFICIAIRE') 
    nom = models.CharField(max_length=100)
    adresse = models.TextField()
    iban = models.CharField(max_length=34, blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Beneficiaire'

class Banque(models.Model):
    TYPE_CHOICES = [
        ('BENEFICIAIRE', 'Banque bénéficiaire'),
        ('INTERMEDIAIRE', 'Banque intermédiaire'),
    ]
    id = models.AutoField(primary_key=True, db_column='ID_BANQUE') 
    nom = models.CharField(max_length=100)
    code_swift = models.CharField(max_length=11)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Banque'

###### cpt local #######
class CPT_LOCAL(models.Model):
    CLIENT = models.CharField(max_length=100)
    DEVISE = models.CharField(max_length=3)
    COMPTE = models.CharField(max_length=50, unique=True)
    NOM = models.CharField(max_length=100)
    NCG = models.CharField(max_length=20)
    TYP = models.CharField(max_length=10)
    DATOUV = models.DateField()
    DATFRM = models.DateField(null=True, blank=True)
    CODFRM = models.CharField(max_length=10, null=True, blank=True)
    EXPL = models.CharField(max_length=200, null=True, blank=True)
    CLERIB = models.CharField(max_length=20, null=True, blank=True)
    DATFIC = models.DateField(null=True, blank=True)
    PERREL1 = models.CharField(max_length=100, null=True, blank=True)
    NBREL1 = models.CharField(max_length=50, null=True, blank=True)
    ADREL1 = models.TextField(null=True, blank=True)
    PERREL2 = models.CharField(max_length=100, null=True, blank=True)
    NBREL2 = models.CharField(max_length=50, null=True, blank=True)
    ADREL2 = models.TextField(null=True, blank=True)
    NBCHQ = models.IntegerField(null=True, blank=True)
    ADRCHQ = models.TextField(null=True, blank=True)
    RUBCOMP = models.CharField(max_length=50, null=True, blank=True)
    AGENCE = models.CharField(max_length=50)
    MOTIFRM = models.CharField(max_length=100, null=True, blank=True)
    CPTDEVE = models.CharField(max_length=50, null=True, blank=True)
    BLOCA = models.CharField(max_length=1, null=True, blank=True)
    DIRIGE = models.CharField(max_length=100, null=True, blank=True)
    INTCHQ = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    DATDINT = models.DateField(null=True, blank=True)
    DATFINT = models.DateField(null=True, blank=True)
    MONTAUT = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    DATECHAUT = models.DateField(null=True, blank=True)
    AUTPROV = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    DATECHPRO = models.DateField(null=True, blank=True)
    AUTOCONF = models.CharField(max_length=1, null=True, blank=True)
    CIONCONF = models.CharField(max_length=1, null=True, blank=True)
    MODCAL = models.CharField(max_length=10, null=True, blank=True)
    RELFORCE = models.CharField(max_length=1, null=True, blank=True)
    NBRTAUX = models.IntegerField(null=True, blank=True)
    NBRCHQ = models.IntegerField(null=True, blank=True)
    NBRMVT = models.IntegerField(null=True, blank=True)
    INSTCLI = models.CharField(max_length=50, null=True, blank=True)
    DATMAJ = models.DateField(null=True, blank=True)
    TYPCPT = models.CharField(max_length=10, null=True, blank=True)
    OUVMOD = models.CharField(max_length=10, null=True, blank=True)
    DATPOS = models.DateField(null=True, blank=True)
    POSDEV = models.CharField(max_length=10, null=True, blank=True)
    DATREL1 = models.DateField(null=True, blank=True)
    POSREL1 = models.CharField(max_length=10, null=True, blank=True)
    NOREL1 = models.CharField(max_length=50, null=True, blank=True)
    DATREL2 = models.DateField(null=True, blank=True)
    POSREL2 = models.CharField(max_length=10, null=True, blank=True)
    NOREL2 = models.CharField(max_length=50, null=True, blank=True)
    RESID = models.CharField(max_length=50, null=True, blank=True)
    INTPREV = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    DATVAL = models.DateField(null=True, blank=True)
    POSVAL = models.CharField(max_length=10, null=True, blank=True)
    NOM2 = models.CharField(max_length=100, null=True, blank=True)
    APPLIC = models.CharField(max_length=50, null=True, blank=True)
    OPLIST = models.TextField(null=True, blank=True)
    LORNOS = models.CharField(max_length=1, null=True, blank=True)
    EXPLMAJ = models.CharField(max_length=200, null=True, blank=True)
    DATIND = models.DateField(null=True, blank=True)
    TYPIND = models.CharField(max_length=10, null=True, blank=True)
    TXCR = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    TXDB = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    NCOMPST = models.CharField(max_length=50, null=True, blank=True)
    FICOBA = models.CharField(max_length=50, null=True, blank=True)
    POSDISP = models.CharField(max_length=10, null=True, blank=True)
    POSATT = models.CharField(max_length=10, null=True, blank=True)
    XSLDREL1 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    XSLDREL2 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    FICANNUL = models.CharField(max_length=1, null=True, blank=True)
    PERSWFT1 = models.CharField(max_length=100, null=True, blank=True)
    PERSWFT2 = models.CharField(max_length=100, null=True, blank=True)
    DOUT = models.CharField(max_length=1, null=True, blank=True)
    MOB = models.CharField(max_length=1, null=True, blank=True)
    PCTMOB = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    NAT = models.CharField(max_length=10, null=True, blank=True)
    TYPF = models.CharField(max_length=10, null=True, blank=True)
    AFF = models.CharField(max_length=10, null=True, blank=True)
    ORGAN = models.CharField(max_length=50, null=True, blank=True)
    PROD = models.CharField(max_length=50, null=True, blank=True)
    CAMP = models.CharField(max_length=50, null=True, blank=True)
    AN = models.IntegerField(null=True, blank=True)
    POSAUT = models.CharField(max_length=10, null=True, blank=True)
    POSCOM = models.CharField(max_length=10, null=True, blank=True)
    OPTFISC = models.CharField(max_length=10, null=True, blank=True)
    RELBAP = models.CharField(max_length=1, null=True, blank=True)
    RELFILJ = models.CharField(max_length=1, null=True, blank=True)
    RELFILM = models.CharField(max_length=1, null=True, blank=True)
    RELREJV = models.CharField(max_length=1, null=True, blank=True)
    RELREJE = models.CharField(max_length=1, null=True, blank=True)
    RELREJP = models.CharField(max_length=1, null=True, blank=True)
    NORELBAP = models.CharField(max_length=50, null=True, blank=True)
    RELCRED = models.CharField(max_length=1, null=True, blank=True)
    CODDCI = models.CharField(max_length=10, null=True, blank=True)
    MOTDCI = models.CharField(max_length=100, null=True, blank=True)
    NOOPDCI = models.CharField(max_length=50, null=True, blank=True)
    IDEBAP = models.CharField(max_length=50, null=True, blank=True)
    TYPRELS = models.CharField(max_length=10, null=True, blank=True)
    BICRELS = models.CharField(max_length=20, null=True, blank=True)
    CNTRGEST = models.CharField(max_length=50, null=True, blank=True)
    CODAPE = models.CharField(max_length=10, null=True, blank=True)
    COTABDF = models.CharField(max_length=1, null=True, blank=True)
    INDFIN = models.CharField(max_length=1, null=True, blank=True)
    DEVORIG = models.CharField(max_length=3, null=True, blank=True)
    RESORIG = models.CharField(max_length=50, null=True, blank=True)
    ISOORIG = models.CharField(max_length=10, null=True, blank=True)
    DATDOUT = models.DateField(null=True, blank=True)
    NOPORT = models.CharField(max_length=50, null=True, blank=True)
    DATPOSOPER = models.DateField(null=True, blank=True)
    CHPRTAXE = models.CharField(max_length=1, null=True, blank=True)
    NOREL942 = models.CharField(max_length=50, null=True, blank=True)
    PERWEB = models.CharField(max_length=100, null=True, blank=True)
    XREOUV = models.CharField(max_length=1, null=True, blank=True)
    INTPREVDISP = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    VIREMSAL = models.CharField(max_length=1, null=True, blank=True)
    CHQADRNO = models.CharField(max_length=1, null=True, blank=True)
    SECTEUR = models.CharField(max_length=50, null=True, blank=True)
    XCAMT054 = models.CharField(max_length=1, null=True, blank=True)
    CLASST = models.CharField(max_length=10, null=True, blank=True)
    DATCPTA = models.DateField(null=True, blank=True)
    TAUXCB = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    TAUXDB = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    TAUXC = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    TAUXD = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    ORIENTEPARGNE = models.CharField(max_length=1, null=True, blank=True)
    DATHMAJ = models.DateField(null=True, blank=True)
    CODBAP = models.CharField(max_length=10, null=True, blank=True)
    XMAJCOTABDF = models.CharField(max_length=1, null=True, blank=True)
    FONDS = models.CharField(max_length=50, null=True, blank=True)
    MOTIF = models.CharField(max_length=100, null=True, blank=True)
    DRACX = models.CharField(max_length=1, null=True, blank=True)
    RELEVCANAL = models.CharField(max_length=1, null=True, blank=True)
    GARTYP = models.CharField(max_length=10, null=True, blank=True)
    NATSUPPOR = models.CharField(max_length=50, null=True, blank=True)
    DATECH = models.DateField(null=True, blank=True)
    DATECHF = models.DateField(null=True, blank=True)
    CPTOFFICIEL = models.CharField(max_length=50, null=True, blank=True)
    DINIX = models.CharField(max_length=1, null=True, blank=True)
    id_compte_local = models.AutoField(primary_key=True, db_column='ID_COMPTE_LOCAL')

    class Meta:
        db_table = 'CPT_LOCAL'
        verbose_name = 'Compte Local'
        verbose_name_plural = 'Comptes Locaux'

    def __str__(self):
        return f"{self.COMPTE} - {self.NOM}"  
#### ---- physique 
from django.db import models

class ClientPhysique(models.Model):
    id_client_physique = models.AutoField(primary_key=True)
    nature_de_compte = models.CharField(max_length=128, blank=True, null=True)
    compte = models.CharField(max_length=44)
    devise = models.CharField(max_length=12, blank=True, null=True)
    client = models.CharField(max_length=24, blank=True, null=True)
    identifiant = models.CharField(max_length=28)
    nni = models.CharField(max_length=92, blank=True, null=True)
    passport = models.CharField(max_length=92, blank=True, null=True)
    carte_sejour = models.CharField(max_length=64, blank=True, null=True)
    nationalite = models.CharField(max_length=128, blank=True, null=True)
    agence = models.CharField(max_length=20, blank=True, null=True)
    paysnais = models.CharField(max_length=128, blank=True, null=True)
    datnais = models.DateField(blank=True, null=True)
    nom = models.CharField(max_length=128, blank=True, null=True)
    prenom = models.CharField(max_length=128, blank=True, null=True)
    tel = models.CharField(max_length=144, blank=True, null=True)
    sexe = models.CharField(max_length=5, blank=True, null=True)
    type_document = models.CharField(max_length=4, blank=True, null=True)

    class Meta:
        db_table = 'CLIENT_PHYSIQUE'
        verbose_name = 'Client Physique'
        verbose_name_plural = 'Clients Physiques'

    def __str__(self):
        return f"{self.nom} {self.prenom} - {self.identifiant}"


#### ----moral 

from django.db import models

class ClientMoral(models.Model):
    id_client_moral = models.AutoField(primary_key=True)
    client = models.CharField(max_length=24, blank=True, null=True)
    nature_de_compte = models.CharField(max_length=128, blank=True, null=True)
    compte = models.CharField(max_length=44)
    devise = models.CharField(max_length=12, blank=True, null=True)
    nom = models.CharField(max_length=100, blank=True, null=True)
    agence = models.CharField(max_length=20, blank=True, null=True)
    raison_sociale = models.CharField(max_length=960, blank=True, null=True)
    nif = models.CharField(max_length=128, blank=True, null=True)
    rc = models.CharField(max_length=84, blank=True, null=True)
    adresse = models.CharField(max_length=464, blank=True, null=True)
    tel = models.CharField(max_length=144, blank=True, null=True)

    class Meta:
        db_table = 'CLIENT_MORAL'
        verbose_name = 'Client Moral'
        verbose_name_plural = 'Clients Moraux'

    def __str__(self):
        return f"{self.raison_sociale} - {self.rc if self.rc else self.nif}"


class Transfer(models.Model):
    TYPE_CLIENT_CHOICES = [
        ('PHYSIQUE', 'Physique'),
        ('MORAL', 'Moral'),
    ]

    id = models.AutoField(primary_key=True, db_column='ID_TRANSFER')
    date_ordre = models.DateTimeField()
    nom_chargeur = models.CharField(max_length=255)
    montant_en_lettre = models.TextField()
    devise = models.CharField(max_length=10)
    montant_chiffre = models.DecimalField(max_digits=15, decimal_places=2)
    frais_mru = models.CharField(max_length=10, blank=True, null=True)
    frais_etranger = models.CharField(max_length=10, blank=True, null=True)
    date_creation = models.DateTimeField()
    date_modification = models.DateTimeField(blank=True, null=True)
    files = models.CharField(max_length=255, blank=True, null=True)
    FILESSWIFT = models.FileField(upload_to='Transfer/', blank=True, null=True)
    plafond = models.IntegerField(default=0)
    current_approval_level = models.IntegerField(default=1)
    observation = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20)
    created_by = models.ForeignKey('AmUsers', on_delete=models.SET_NULL, null=True, db_column='CREATED_BY')
    nom_beneficiaire = models.CharField(max_length=255)
    adresse_beneficiaire = models.TextField()
    iban_beneficiaire = models.CharField(max_length=34)
    nom_banque_beneficiaire = models.CharField(max_length=255)
    code_swift_banque_beneficiaire = models.CharField(max_length=11)
    nom_banque_intermediaire = models.CharField(max_length=255, blank=True, null=True)
    code_swift_banque_intermediaire = models.CharField(max_length=11, blank=True, null=True)
    
    # Relations avec les clients
    id_client = models.IntegerField(blank=True, null=True)
    type_client = models.CharField(max_length=10, choices=TYPE_CLIENT_CHOICES)
    
    # Nouveaux champs (si nécessaire)
    ref_fac = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'TRANSFER'

    def __str__(self):
        return f"Transfer {self.id_transfer} - {self.nom_beneficiaire}"


class HistoriqueTransfer(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    transfer = models.ForeignKey('Transfer', on_delete=models.CASCADE, db_column='TRANSFER_ID')
    user = models.ForeignKey('AmUsers', on_delete=models.CASCADE, db_column='USER_ID')
    action_date = models.DateTimeField(db_column='ACTION_DATE')
    action_type = models.CharField(max_length=50, db_column='ACTION_TYPE')
    observation = models.CharField(max_length=800, db_column='OBSERVATION', blank=True, null=True)
    plafond = models.IntegerField(db_column='PLAFOND', null=True)
    current_approval_level = models.IntegerField(db_column='CURRENT_APPROVAL_LEVEL', null=True)
    status = models.CharField(max_length=20, db_column='STATUS', null=True)

    class Meta:
        db_table = 'HISTORIQUE_TRANSFER'
        managed = False


        


###### ------ credit back ------ ###########
from django.db import models
import os
import uuid
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
# -------- models.py --------
class Client(models.Model):
    client_code = models.CharField(max_length=20, unique=True)
    identifiant = models.CharField(max_length=20, null=True)
    pays_naissance = models.CharField(max_length=100, null=True)
    # date_naissance = models.DateField()
    date_naissance = models.DateField(blank=True, null=True)     

    nom = models.CharField(max_length=255, null=True)
    prenom = models.CharField(max_length=255, null=True)
    tel = models.CharField(max_length=20, null=True)
    sexe = models.CharField(max_length=10, null=True)
    type_document = models.CharField(max_length=10, null=True)
    # date_expiration = models.DateField()
    date_expiration = models.DateField(blank=True, null=True)     
    date_creation = models.DateField(blank=True, null=True)     
    nni = models.CharField(max_length=20, null=True)
    # date_creation = models.DateField()
    agence = models.CharField(max_length=20, null=True)
    type_client = models.CharField(max_length=50, null=True)
    NIF = models.TextField(blank=True, null=True)
    Address = models.TextField(blank=True, null=True)
    def __str__(self): 
        return self.client_code 


class Credit(models.Model):
    STATUT_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('VALIDÉ', 'Validé'),
        ('REJETÉ', 'Rejeté'),
    ]
    TYPE_DOSSIER = [
        ('Particulier', 'Particulier'),
        ('Entreprise', 'Entreprise'),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='credits')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    duree = models.IntegerField()  # en mois
    avis = models.CharField(max_length=500)
    memo = models.CharField(max_length=500)
    date_demande = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_COURS')
    points_valides = models.IntegerField(default=0)
    motif_rejet = models.TextField(blank=True, null=True)
    date_rejet = models.DateTimeField(blank=True, null=True)  # ← champ ajouté
    agence = models.CharField(max_length=50)
    type_credit = models.CharField(max_length=50)
    nature_credit = models.CharField(max_length=50)
   

    type_dossier = models.CharField(max_length=20, choices=TYPE_DOSSIER, default='Particulier')

    def save(self, *args, **kwargs):
        if self.status == 'REJETÉ' and not self.date_rejet:
            self.date_rejet = timezone.now()
        elif self.status != 'REJETÉ':
            self.date_rejet = None

        if not self.reference:
            date_str = timezone.now().strftime('%Y%m%d%H%M%S')
            self.reference = f"CRD-{date_str}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.client)  


class Document(models.Model):
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='documents')
    fichier = models.FileField(upload_to='documents/')
    type_document = models.CharField(max_length=100)
    createur = models.ForeignKey(AmUsers, on_delete=models.CASCADE, related_name='createuro')
    date_creation = models.DateTimeField(auto_now_add=True) 

    def __str__(self): 
        return str(self.credit.client)+" | "+self.type_document+ " | creer par "+str(self.createur) + " a la date : "+str(self.date_creation)


def get_next_poste(current_poste):
    current_points = POSTE_POINTS.get(current_poste)
    if current_points is None:
        return None

    for poste, points in sorted(POSTE_POINTS.items(), key=lambda x: x[1]):
        if points > current_points:
            return poste
    return None  # Aucun suivant, donc validé final

User = get_user_model()

class ValidationCredit(models.Model):
    TYPE_CREDIT = [
        ('Validé', 'Validé'),
        ('Rejeté', 'Rejeté'),
        ('Créé', 'Créé')
    ]
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='validations')
    validateur = models.ForeignKey(AmUsers, on_delete=models.CASCADE)
    date_validation = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(null=True, blank=True)
    date_rejet = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=TYPE_CREDIT)
    

    points = models.IntegerField()
    motiv = models.CharField(max_length=100)
    memo = models.CharField(max_length=100)
    poste = models.CharField(max_length=100)

    
    class Meta:
        pass




    def __str__(self):
        return f"{self.validateur.username} → {self.credit.reference} ({self.points} pts)"



class TypeUploadFile(models.Model):
    TYPE_CHOICES = [
        ('entreprise', 'Entreprise'),
        ('particulier', 'Particulier'),
    ]
    
    nom = models.CharField(max_length=100)  
    value = models.CharField(max_length=100)  
    label = models.TextField() 
    type_client = models.CharField(max_length=20, choices=TYPE_CHOICES)

    def __str__(self):
        return f"{self.nom} ({self.type_client})"



class Notification(models.Model):
    user = models.ForeignKey(AmUsers, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    objet = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    def __str__(self):
        return f"notification {self.message} [{self.date_created}]"
