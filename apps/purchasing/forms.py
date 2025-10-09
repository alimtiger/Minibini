from django import forms
from .models import PurchaseOrder
from apps.core.services import NumberGenerationService


class PurchaseOrderForm(forms.ModelForm):
    """Form for creating/editing PurchaseOrder"""

    class Meta:
        model = PurchaseOrder
        fields = ['job']
        help_texts = {
            'job': 'PO number will be assigned automatically on save.',
        }

    def __init__(self, *args, **kwargs):
        job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)

        # Job is optional, but if provided, pre-select it
        self.fields['job'].required = False
        if job:
            self.fields['job'].initial = job

    def save(self, commit=True):
        """Override save to generate PO number using NumberGenerationService"""
        instance = super().save(commit=False)

        # Generate the actual PO number (increments counter)
        instance.po_number = NumberGenerationService.generate_next_number('po')

        if commit:
            instance.save()
        return instance
