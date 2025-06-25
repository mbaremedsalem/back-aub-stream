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
    username = models.CharField(max_length=100, primary_key=True)
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