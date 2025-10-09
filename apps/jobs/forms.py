from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    WorkOrderTemplate, TaskTemplate, TaskMapping,
    EstWorksheet, Task, Estimate, EstimateLineItem, Job
)
from apps.contacts.models import Contact
from apps.core.services import NumberGenerationService


class JobCreateForm(forms.ModelForm):
    """Form for creating a new Job"""
    contact = forms.ModelChoiceField(
        queryset=Contact.objects.all().select_related('business'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Contact --"
    )
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    class Meta:
        model = Job
        fields = ['contact', 'customer_po_number', 'description', 'due_date']
        widgets = {
            'customer_po_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        help_texts = {
            'contact': 'Job number will be assigned automatically on save.',
        }

    def __init__(self, *args, **kwargs):
        initial_contact = kwargs.pop('initial_contact', None)
        super().__init__(*args, **kwargs)

        # Customize contact field display to include business name
        self.fields['contact'].label_from_instance = self.label_from_instance_with_business

        # Pre-select contact if provided
        if initial_contact:
            self.fields['contact'].initial = initial_contact

    def label_from_instance_with_business(self, contact):
        """Custom label for contact dropdown to include business name"""
        if contact.business:
            return f"{contact.name} ({contact.business.business_name})"
        return contact.name

    def save(self, commit=True):
        """Override save to generate job number using NumberGenerationService"""
        instance = super().save(commit=False)

        # Generate the actual job number (increments counter)
        instance.job_number = NumberGenerationService.generate_next_number('job')

        if commit:
            instance.save()
        return instance


class WorkOrderTemplateForm(forms.ModelForm):
    class Meta:
        model = WorkOrderTemplate
        fields = ['template_name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class TaskTemplateForm(forms.ModelForm):
    task_mapping = forms.ModelChoiceField(
        queryset=TaskMapping.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Task Mapping (Optional) --"
    )
    
    class Meta:
        model = TaskTemplate
        fields = ['template_name', 'description', 'units', 'rate', 'task_mapping', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'units': forms.TextInput(attrs={'placeholder': 'e.g., hours, pieces'}),
            'rate': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
        }


class EstWorksheetForm(forms.ModelForm):
    """Form for creating/editing EstWorksheet"""
    class Meta:
        model = EstWorksheet
        fields = ['job', 'template']  # Removed 'status' - always starts as draft
        widgets = {
            'template': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Template is optional
        self.fields['template'].required = False
        self.fields['template'].empty_label = "-- No Template (Manual) --"


# Removed EstWorksheetFromTemplateForm - functionality merged into EstWorksheetForm


class TaskForm(forms.ModelForm):
    """Form for creating/editing Task"""
    class Meta:
        model = Task
        fields = ['name', 'template', 'est_worksheet', 'est_qty', 'units', 'rate']
        widgets = {
            'est_qty': forms.NumberInput(attrs={'step': '0.01'}),
            'rate': forms.NumberInput(attrs={'step': '0.01'}),
        }


class TaskFromTemplateForm(forms.Form):
    """Form for adding Task from TaskTemplate"""
    template = forms.ModelChoiceField(
        queryset=TaskTemplate.objects.filter(is_active=True),
        required=True,
        label="Task Template"
    )
    est_qty = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=1.0,
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )


class EstimateLineItemForm(forms.ModelForm):
    """Form for creating/editing EstimateLineItem"""
    class Meta:
        model = EstimateLineItem
        fields = ['description', 'qty', 'units', 'price_currency', 'task', 'price_list_item']
        widgets = {
            'qty': forms.NumberInput(attrs={'step': '0.01'}),
            'price_currency': forms.NumberInput(attrs={'step': '0.01'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        estimate = kwargs.pop('estimate', None)
        super().__init__(*args, **kwargs)
        if estimate:
            # Only show tasks from the estimate's job
            self.fields['task'].queryset = Task.objects.filter(
                est_worksheet__job=estimate.job
            )


class EstimateForm(forms.ModelForm):
    """Form for creating/editing Estimate"""
    class Meta:
        model = Estimate
        fields = ['status']
        widgets = {
            'status': forms.Select(choices=Estimate.ESTIMATE_STATUS_CHOICES)
        }
        help_texts = {
            'status': 'Estimate number will be assigned automatically on save.',
        }

    def __init__(self, *args, **kwargs):
        job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)
        # Store job for use in save method
        self._job = job

    def save(self, commit=True):
        """Override save to generate estimate number using NumberGenerationService"""
        instance = super().save(commit=False)

        # Generate the actual estimate number (increments counter)
        instance.estimate_number = NumberGenerationService.generate_next_number('estimate')

        if commit:
            instance.save()
        return instance


class EstimateStatusForm(forms.Form):
    """Form for changing Estimate status"""
    VALID_TRANSITIONS = {
        'draft': ['open', 'rejected'],
        'open': ['accepted', 'rejected', 'superseded'],
        'accepted': ['superseded'],
        'rejected': [],
        'superseded': []
    }

    status = forms.ChoiceField(choices=[], required=True)

    def __init__(self, *args, **kwargs):
        current_status = kwargs.pop('current_status', 'draft')
        super().__init__(*args, **kwargs)

        # Set valid status choices based on current status
        valid_statuses = self.VALID_TRANSITIONS.get(current_status, [])
        choices = [(current_status, f'{current_status.title()} (current)')]
        choices.extend([(s, s.title()) for s in valid_statuses])

        self.fields['status'].choices = choices
        self.fields['status'].initial = current_status

    def clean_status(self):
        status = self.cleaned_data['status']
        # Additional validation if needed
        return status