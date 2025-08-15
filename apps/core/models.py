from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    contact_id = models.ForeignKey('contacts.Contact', on_delete=models.SET_NULL, null=True, blank=True)
    username_flagged_but_not_required_email = models.CharField(max_length=255, blank=True)
    encrypted_password = models.CharField(max_length=255)
    role_id = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True)
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='core_user_set',
        related_query_name='core_user',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='core_user_set',
        related_query_name='core_user',
    )


class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=100)
    role_description = models.TextField(blank=True)

    def __str__(self):
        return self.role_name


class Configuration(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    field = models.CharField(max_length=255)
    invoice_number_sequence = models.CharField(max_length=50, blank=True)
    estimate_number_sequence = models.CharField(max_length=50, blank=True)
    job_number_sequence = models.CharField(max_length=50, blank=True)
    po_number_sequence = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"