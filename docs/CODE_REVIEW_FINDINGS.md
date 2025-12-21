# Code Review Findings Report

**Date:** December 19, 2025
**Reviewed By:** Automated Code Review
**Scope:** Full codebase review of existing functionality

---

## Executive Summary

This document presents findings from a comprehensive code review of the Minibini Django application. The application is a job management and invoicing system with modules for contacts, jobs, estimates, worksheets, invoicing, and purchasing.

**Note:** This review focuses on bugs and issues in **existing functionality**. Authentication, authorization, and credential management are intentionally simplified for development and will be addressed later.

| Severity | Count | Key Areas |
|----------|-------|-----------|
| CRITICAL | 1 | Data Integrity |
| IMPORTANT | 13 | Logic Bugs, Validation, Performance, Data Integrity |
| MINOR | 6 | Code Style, Incomplete Features |

---

## CRITICAL Issues (Must Fix)

### 1. Contact Deletion Bypasses Model Validation

**File:** `apps/contacts/views.py`, lines 656-660

**Description:**
```python
# Must delete business first to avoid PROTECT constraint on default_contact
business.delete()

# Delete contacts by ID since the queryset relationship is broken after business deletion
Contact.objects.filter(contact_id__in=contact_ids).delete()
```

**Impact:** Using `delete()` directly on a QuerySet bypasses the `Contact.delete()` override that validates business default contact logic. This could leave orphaned data or inconsistent state. The `Contact.delete()` method (lines 66-71) handles updating business default contacts, but this is skipped entirely.

**Recommended Fix:**

Since `Business.default_contact` is a required field (`null=False`), you cannot set it to null. The deletion logic must account for the constraint that every Business must have at least one Contact (its default_contact).

```python
from django.db import transaction

with transaction.atomic():
    # Delete contacts individually to trigger model logic
    # The Contact.delete() override will call validate_and_fix_default_contact()
    # which reassigns default_contact to another contact if available
    for contact_id in contact_ids:
        try:
            contact = Contact.objects.get(contact_id=contact_id)
            contact.delete()  # Triggers model validation
        except Contact.DoesNotExist:
            pass

    # Only delete business after all contacts are handled
    # If this is the last contact, deletion should be blocked
    business.delete()
```

Additionally, the `Contact.delete()` method should be enhanced to prevent deletion if:
1. The contact is the default_contact for a business, AND
2. It is the only contact belonging to that business

```python
def delete(self, *args, **kwargs):
    business = self.business
    if business and business.default_contact == self:
        other_contacts = business.contacts.exclude(pk=self.pk)
        if not other_contacts.exists():
            raise PermissionDenied(
                f'Cannot delete the only contact for business "{business}". '
                'Delete the business or add another contact as the default first.'
            )
    super().delete(*args, **kwargs)
    if business:
        business.validate_and_fix_default_contact()
```

---

## IMPORTANT Issues (Should Fix Before Production)

### 2. Invoice Default Status Mismatch

**File:** `apps/invoicing/models.py`, line 21

**Description:**
```python
status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='active')
```

**Impact:** The default value `'active'` is not in `INVOICE_STATUS_CHOICES` which starts with `'draft'`. This will cause validation errors when creating invoices or unexpected behavior in status-dependent logic.

**Recommended Fix:**
```python
status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='draft')
```

---

### 3. Race Condition in Business Reference Code Generation

**File:** `apps/contacts/models.py`, lines 110-124

**Description:**
```python
while Business.objects.filter(our_reference_code=self.our_reference_code).exists():
    next_id += 1
    self.our_reference_code = f"BUS-{next_id:04d}"
```

**Impact:** This loop-based uniqueness check is not atomic. Two concurrent requests could both pass the `exists()` check and attempt to insert the same reference code, causing an IntegrityError.

**Recommended Fix:** Use database-level unique constraint handling with retry logic:
```python
from django.db import transaction, IntegrityError

@transaction.atomic
def save(self, *args, **kwargs):
    if not self.our_reference_code:
        for attempt in range(10):
            try:
                self.our_reference_code = self._generate_next_code()
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                continue
        raise ValueError("Could not generate unique reference code")
```

---

### 4. estimate_revise Sets Non-Existent Field

**File:** `apps/jobs/views.py`, lines 872-874

**Description:**
```python
parent_estimate.status = 'superseded'
parent_estimate.superseded_date = timezone.now()  # This field doesn't exist!
parent_estimate.save()
```

**Impact:** The `Estimate` model does not have a `superseded_date` field. This will cause an `AttributeError` at runtime when trying to revise an estimate.

**Recommended Fix:** Remove this line - the model's `save()` method already sets `closed_date` when transitioning to terminal states:
```python
parent_estimate.status = 'superseded'
# closed_date is automatically set by the model's save() method
parent_estimate.save()
```

---

### 5. PurchaseOrder Form Regenerates PO Number on Edit

**File:** `apps/purchasing/forms.py`, lines 62-71

**Description:**
```python
def save(self, commit=True):
    instance = super().save(commit=False)
    # Generate the actual PO number (increments counter)
    instance.po_number = NumberGenerationService.generate_next_number('po')
```

**Impact:** When editing an existing PO, this generates a new PO number, losing the original and wasting counter values. This breaks document continuity.

**Recommended Fix:**
```python
def save(self, commit=True):
    instance = super().save(commit=False)
    if not instance.pk:  # Only generate for new instances
        instance.po_number = NumberGenerationService.generate_next_number('po')
    if commit:
        instance.save()
    return instance
```

---

### 6. Missing Transaction Wrapping on Multi-Model Operations

**File:** `apps/contacts/views.py`, lines 54-78 (add_contact), lines 194-242 (add_business)

**Description:**
```python
business = Business.objects.create(...)
contact = Contact.objects.create(
    ...
    business=business
)
```

**Impact:** If contact creation fails after business creation, you'll have an orphaned business with no contacts, violating the business rule that a business must have at least one contact.

**Recommended Fix:**
```python
from django.db import transaction

with transaction.atomic():
    business = Business.objects.create(...)
    contact = Contact.objects.create(..., business=business)
```

---

### 7. Model clean() Method Not Called on ORM Create

**File:** `apps/contacts/views.py`, multiple locations

**Description:** `Contact.objects.create()` does not call `full_clean()` by default, so the model-level validation in `Contact.clean()` (requiring email and at least one phone number) is bypassed.

**Impact:** Contacts can be created without email or phone numbers through direct ORM usage, bypassing the validation that the view manually implements.

**Recommended Fix:** Override `Contact.save()` to call `full_clean()`:
```python
def save(self, *args, **kwargs):
    self.full_clean()  # Add this line
    # ... rest of save method
    super().save(*args, **kwargs)
```

---

### 8. N+1 Query Problem in delete_business View

**File:** `apps/contacts/views.py`, lines 585-604

**Description:**
```python
for contact in contacts:
    has_jobs = Job.objects.filter(contact=contact).exists()
    has_bills = Bill.objects.filter(contact=contact).exists()
    if has_jobs or has_bills:
        jobs = list(Job.objects.filter(contact=contact).values_list('job_number', flat=True))
        bills = list(Bill.objects.filter(contact=contact).values_list('bill_id', flat=True))
```

**Impact:** For each contact, this makes 2-4 database queries. With 10 contacts, that's 20-40 queries. This will cause performance issues as data grows.

**Recommended Fix:**
```python
contact_ids = list(contacts.values_list('contact_id', flat=True))

# Single query for jobs
jobs_by_contact = defaultdict(list)
for item in Job.objects.filter(contact_id__in=contact_ids).values('contact_id', 'job_number'):
    jobs_by_contact[item['contact_id']].append(item['job_number'])

# Single query for bills
bills_by_contact = defaultdict(list)
for item in Bill.objects.filter(contact_id__in=contact_ids).values('contact_id', 'bill_id'):
    bills_by_contact[item['contact_id']].append(item['bill_id'])

# Then check each contact using the dictionaries
```

---

### 9. State-Changing Operations on GET Requests

**Files:** `apps/jobs/views.py` (lines 887, 927, 962), `apps/invoicing/views.py` (line 72), `apps/purchasing/views.py` (lines 309, 349)

**Description:** Reordering operations modify database state but are triggered via GET requests:
```python
def task_reorder_worksheet(request, worksheet_id, task_id, direction):
    # No POST check, but modifies data
    current_task.save()
    swap_task.save()
```

**Impact:** GET requests should be idempotent. While CSRF middleware provides some protection, these could still be triggered unintentionally by browser prefetching, crawlers, or link previews.

**Recommended Fix:** Require POST method:
```python
from django.views.decorators.http import require_POST

@require_POST
def task_reorder_worksheet(request, worksheet_id, task_id, direction):
    # ...
```

---

### 10. Inconsistent Validation Between Forms and Models

**File:** `apps/jobs/forms.py`, lines 296-322 vs `apps/jobs/models.py`, lines 134-142

**Description:** `EstimateStatusForm.VALID_TRANSITIONS` duplicates the transition logic from `Estimate.clean()`. Same issue exists for `WorkOrderStatusForm`, `PurchaseOrderStatusForm`, and `BillStatusForm`.

**Impact:** If transition rules change in the model, the form may not be updated (or vice versa), leading to inconsistent behavior.

**Recommended Fix:** Single source of truth - define transitions on the model and reference from forms:
```python
# In models.py
class Estimate(models.Model):
    VALID_TRANSITIONS = {
        'draft': ['open', 'rejected'],
        'open': ['accepted', 'superseded', 'rejected', 'expired'],
        # ...
    }

# In forms.py
class EstimateStatusForm(forms.Form):
    def __init__(self, *args, **kwargs):
        current_status = kwargs.pop('current_status', 'draft')
        super().__init__(*args, **kwargs)
        valid_statuses = Estimate.VALID_TRANSITIONS.get(current_status, [])
        # ...
```

---

### 11. Line Number Stored as String Instead of Integer

**File:** `apps/jobs/services.py`, lines 517, 523, 545, 551, 601, 608, 649, 658

**Description:**
```python
line_number=str(self.line_number),
```

**Impact:** `BaseLineItem.line_number` is defined as `PositiveIntegerField`, but the service assigns string values. While Django's type coercion handles this, it could cause sorting issues (string "10" sorts before "2") and is semantically incorrect.

**Recommended Fix:**
```python
line_number=self.line_number,  # Don't convert to string
```

---

### 12. Views Duplicate Validation Logic Already in Models

**File:** `apps/contacts/views.py`, lines 43-52, 106-115, 183-192, 276-292

**Description:** Views manually validate email and phone requirements:
```python
# View validation
if not email or not email.strip():
    messages.error(request, 'Email address is required.')
    return render(request, 'contacts/add_contact.html')

if not any([work_number, mobile_number, home_number]):
    messages.error(request, 'At least one phone number...')
```

This duplicates `Contact.clean()` logic.

**Impact:** Validation logic must be maintained in two places. If model validation changes, views may not be updated.

**Recommended Fix:** Use Django ModelForms which automatically call model validation:
```python
class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['first_name', 'last_name', 'email', ...]
```

---

### 13. Business Deletion Can Leave Default Contact Reference Invalid

**File:** `apps/contacts/views.py`, lines 643-646

**Description:**
```python
if contact_action == 'unlink':
    # Unlink contacts from business
    contacts.update(business=None)
    business.delete()
```

**Impact:** `contacts.update(business=None)` uses a bulk update that bypasses `Contact.save()`. This means `validate_and_fix_default_contact()` is never called, potentially leaving the business in an invalid state before deletion (though deletion may still succeed).

**Recommended Fix:** While this works because the business is deleted anyway, for consistency:
```python
with transaction.atomic():
    for contact in contacts:
        contact.business = None
        contact.save()
    business.delete()
```

---

### 14. delete_contact Uses Wrong Status Values

**File:** `apps/contacts/views.py`, lines 326-330

**Description:**
```python
open_jobs = Job.objects.filter(
    contact=contact
).exclude(
    status__in=['complete', 'rejected']
)
```

**Impact:** The Job model uses `'completed'` not `'complete'`. This exclusion filter will never match completed jobs, incorrectly blocking contact edits.

**Recommended Fix:**
```python
).exclude(
    status__in=['completed', 'rejected', 'cancelled']
)
```

---

## MINOR Issues (Nice to Fix)

### 15. Inconsistent Error Message Formatting

**Files:** Various views

**Description:** Some error messages use f-strings with quotes around names, others don't. Some end with periods, others don't.

**Recommended Fix:** Establish a style guide for error messages and apply consistently.

---

### 16. Misplaced Import in jobs/models.py

**File:** `apps/jobs/models.py`, line 502

**Description:**
```python
from apps.core.models import BaseLineItem
```
This import appears mid-file instead of at the top with other imports.

**Recommended Fix:** Move import to top of file. This appears to be a circular import workaround - consider restructuring if possible.

---

### 17. PaymentTerms Model is Incomplete

**File:** `apps/contacts/models.py`, lines 181-186

**Description:**
```python
class PaymentTerms(models.Model):
    term_id = models.AutoField(primary_key=True)
    # Additional fields not visible in diagram
```

**Impact:** The model has no meaningful fields beyond the primary key. It's referenced by `Business.terms` but is currently unusable.

**Recommended Fix:** Either complete the model with necessary fields (days_until_due, discount_percentage, etc.) or remove the foreign key reference until needed.

---

### 18. Magic Strings for Status Values

**Files:** Various models and views

**Description:** Status values like `'draft'`, `'open'`, `'accepted'` are repeated as string literals throughout the codebase.

**Recommended Fix:** Use constants:
```python
class EstimateStatus:
    DRAFT = 'draft'
    OPEN = 'open'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    EXPIRED = 'expired'
    SUPERSEDED = 'superseded'
```

---

### 19. Decimal Field Precision for Financial Data

**File:** `apps/core/models.py`, line 60

**Description:**
```python
price_currency = models.DecimalField(max_digits=10, decimal_places=2)
```

**Impact:** 2 decimal places is standard for display but may cause rounding errors in intermediate calculations.

**Recommended Fix:** Consider 4 decimal places for storage, rounding on display:
```python
price_currency = models.DecimalField(max_digits=12, decimal_places=4)
```

---

### 20. Unused template Field in EstWorksheet

**File:** `apps/jobs/models.py`

**Description:** `EstWorksheet` inherits `template` from `AbstractWorkContainer` but the field is optional and the relationship to templates is managed through the workflow rather than direct assignment.

**Recommended Fix:** Review whether this field is needed or if the template relationship should be restructured.

---

## Priority Recommendations

### Immediate Priority (Blocks Testing)
1. **Fix Invoice default status** (`'active'` -> `'draft'`) - Will cause errors on invoice creation
2. **Fix estimate_revise `superseded_date` error** - Will crash when revising estimates
3. **Fix delete_contact status check** (`'complete'` -> `'completed'`) - Wrong filter logic

### Short-term Priority (Before Integration Testing)
1. Fix Contact deletion bypassing model validation (Critical #1)
2. Fix PurchaseOrder number regeneration on edit
3. Wrap multi-model operations in transactions
4. Fix line_number string/integer type mismatch

### Medium-term Priority (Before Production)
1. Consolidate validation between forms and models
2. Optimize N+1 queries
3. Require POST for state-changing operations
4. Add model-level validation enforcement in `save()`

---

## Appendix: Files Reviewed

| App | Files |
|-----|-------|
| contacts | `models.py`, `views.py` |
| core | `models.py`, `services.py`, `middleware.py` |
| jobs | `models.py`, `views.py`, `forms.py`, `services.py` |
| invoicing | `models.py`, `views.py` |
| purchasing | `models.py`, `views.py`, `forms.py` |
| search | `views.py` |
| minibini | `settings.py` |

---

## Notes

Items intentionally excluded from this review (to be addressed in future development phase):
- Authentication and authorization implementation
- Environment-based configuration management
- Secret key externalization
- AutoLoginMiddleware (intentional dev convenience)
