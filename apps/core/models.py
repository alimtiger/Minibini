from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model extending Django's AbstractUser with business-specific fields."""
    
    # Business-specific fields
    contact = models.OneToOneField(
        'contacts.Contact', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text='Associated contact record for this user'
    )
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'



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