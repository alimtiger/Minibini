# Minibini Django Application - Codebase Documentation

## Overview

Minibini is a Django-based business management system designed for handling jobs, estimates, work orders, invoicing, and purchasing workflows. The application follows a minimal, functional design philosophy with no CSS framework or visual prettiness - just plain HTML forms and simple navigation.  It is in pre-production state and is changing rapidly as new features are added.  This document should be updated as changes are made.

## Core Architecture Principles

### Design Philosophy
- **Minimalist UI**: No CSS frameworks, no JavaScript, plain semantic HTML only
  - Inline styles should be avoided except for critical readability (e.g., borders on content)
  - Semantic HTML (`<p>`, `<strong>`, `<em>`, `<fieldset>`) over styled `<div>` elements
- **Function over form**: Focus on functionality rather than aesthetics
- **Django-native**: Leverage Django's built-in features (especially messages framework)
- **Development-first**: Includes auto-login middleware and development conveniences

### Technology Stack
- **Framework**: Django 5.2.5
- **Database**: MySQL (development configuration)
- **Authentication**: Custom User model extending Django's AbstractUser
- **Frontend**: Plain HTML templates with minimal styling
- **Email Integration**: imap-tools (IMAP client library, zero dependencies)

## Project Structure

```
Minibini/
├── apps/                    # Django applications
│   ├── core/               # Core functionality and base models
│   ├── jobs/               # Job management, estimates, work orders
│   ├── contacts/           # Contact and business management
│   ├── invoicing/          # Invoice generation and management
│   └── purchasing/         # Purchase orders and bills
├── templates/              # HTML templates
├── fixtures/               # Test data fixtures
├── tests/                  # Test suite
├── minibini/              # Project configuration
└── manage.py              # Django management script
```

## Database Schema

### Core Models (`apps.core`)

#### User
- Custom user model extending AbstractUser
- Links to Contact for business relationship
- Used for task assignment and authentication

#### Configuration
- Key-value store for system settings
- Stores sequence numbers for various document types (invoice, estimate, job, PO)
- Stores email_retention_days for TempEmail cleanup

#### EmailRecord
- Permanent record linking emails to jobs
- Contains only message_id (RFC 2822 Message-ID header) for IMAP retrieval
- Links to Job (nullable) - never automatically deleted
- Email server is source of truth

#### TempEmail
- Temporary cache of email metadata from IMAP server
- OneToOne relationship with EmailRecord
- Contains subject, from_email, to_email, cc_email, date_sent, flags
- Can be deleted after retention period (configurable via Configuration.email_retention_days)
- Auto-deleted by cleanup process while EmailRecord persists

#### BaseLineItem (Abstract)
- Abstract base class for all line item types
- Provides shared fields: task, price_list_item, line_number, qty, units, description, price_currency
- Validates that items can't have both task AND price_list_item
- Auto-generates line numbers if not provided
- Implements total_amount calculation

### Jobs Module (`apps.jobs`)

#### Job
- Central entity for work management
- Status workflow: draft → approved/rejected → needs_attention/blocked → complete
- Links to Contact for customer relationship
- Contains customer PO number and description

#### Estimate
- Quotes for jobs with versioning support
- Status workflow: draft → open → accepted/rejected/superseded
- Parent-child relationship for revision tracking
- Triggers worksheet status updates via signals

#### EstWorksheet
- Working document for creating estimates
- Can be created from WorkOrderTemplate
- Status: draft → final → superseded
- Version tracking with parent reference
- Contains Tasks that define the work

#### WorkOrder
- Actual work to be performed
- Status: draft → incomplete/blocked → complete
- Created from accepted estimates
- Contains executable Tasks

#### Task
- Individual work items
- Can belong to either EstWorksheet OR WorkOrder (not both)
- Hierarchical structure with parent_task
- Links to TaskTemplate for standardization
- Contains estimated quantity, rate, units

#### Blep
- Time tracking entity
- Records start/end times for task work
- Links user to task

#### Template System
- **WorkOrderTemplate**: Defines complete products/services
- **TaskTemplate**: Reusable task definitions with rates
- **TaskMapping**: Defines how tasks map to line items
- **TemplateTaskAssociation**: Links templates with quantities and sort order
- **ProductBundlingRule**: Rules for bundling a set of Tasks, that create products, into line items

#### EstimateLineItem
- Line items for estimates
- Inherits from BaseLineItem
- Can reference either a Task or PriceListItem

### Contacts Module (`apps.contacts`)

#### Contact
- Individual person records
- Multiple phone numbers (work, mobile, home)
- Address fields with international support
- Links to Business entity

#### Business
- Company/organization records
- Tax information and exemptions
- Payment terms reference
- Our internal reference code

#### PaymentTerms
- Payment conditions for businesses

### Invoicing Module (`apps.invoicing`)

#### Invoice
- Final bills for completed work
- Links to Job
- Status: active/cancelled
- Unique invoice number

#### InvoiceLineItem
- Line items for invoices
- Inherits from BaseLineItem
- References Task or PriceListItem

#### PriceListItem
- Catalog of standard items/services
- Purchase and selling prices
- Inventory tracking (qty_on_hand, qty_sold, qty_wasted)

### Purchasing Module (`apps.purchasing`)

#### PurchaseOrder
- Orders to vendors
- Links to Job (optional)
- Unique PO number

#### Bill
- Vendor invoices received
- Links to PurchaseOrder and Contact
- Vendor invoice number tracking

#### PurchaseOrderLineItem & BillLineItem
- Line items inheriting from BaseLineItem

## URL Structure

### Main URLs (`minibini/urls.py`)
- `/` - Home page
- `/admin/` - Django admin
- `/settings/` - Settings page
- `/jobs/` - Jobs app URLs
- `/contacts/` - Contacts app URLs
- `/core/` - Core app URLs
- `/purchasing/` - Purchasing app URLs
- `/invoicing/` - Invoicing app URLs

### Core URLs (`apps/core/urls.py`)
Key endpoints:
- `/core/inbox/` - Email inbox with fetch from IMAP
- `/core/inbox/<email_record_id>/` - Email detail view
- `/core/inbox/<email_record_id>/create-job/` - Create job from email workflow

### Jobs URLs (`apps/jobs/urls.py`)
Key endpoints:
- `/jobs/` - Job list
- `/jobs/create/` - Create new job
- `/jobs/<id>/` - Job detail
- `/jobs/estimates/` - Estimate list
- `/jobs/worksheets/` - EstWorksheet list
- `/jobs/templates/` - WorkOrderTemplate management
- `/jobs/task-templates/` - TaskTemplate management
- `/jobs/work_orders/` - Work order management

### Contacts URLs (`apps/contacts/urls.py`)
Key endpoints:
- `/contacts/add/` - Add contact (supports email workflow session data)
- `/contacts/confirm-create-business/` - Intermediate page for business creation confirmation

## Views and Forms

### View Patterns
- Function-based views (no class-based views)
- Simple CRUD operations
- Redirect-after-POST pattern
- Django messages for user feedback
- get_object_or_404 for safe object retrieval

### Form Design
- ModelForms for database interaction
- Manual field configuration for control
- Auto-generation of document numbers (job numbers, etc.)
- Minimal JavaScript - datetime-local inputs for dates
- Select dropdowns for relationships

### Templates
- **Extends base.html template** - provides standard layout and navigation
- **Message display** - Django's messages framework is already in base.html
  - NEVER duplicate message display in individual templates
  - All user feedback goes through `messages.success()`, `messages.error()`, etc. in views
- **Use semantic HTML**:
  - `<p>` for paragraphs and form field wrappers
  - `<strong>` and `<em>` for emphasis instead of styled spans/divs
  - `<fieldset>` and `<legend>` for grouping related form fields
  - `<table>` with `border="1"` for data tables (no CSS styling)
- **Forms**:
  - Each field in a `<p>` tag
  - `<label>` with `<strong>` for labels, followed by `<br>` then input
  - Plain `<button>` elements without any styling attributes
  - Simple text links, not styled as buttons
- **Avoid inline styles** - only use when absolutely necessary for content readability
- Navigation provided by base template in header/footer
- Status indicators use simple CSS classes in base.html (e.g., .superseded)

## Development Features

### AutoLoginMiddleware (`apps.core.middleware`)
- Automatically logs in 'dev_user' for development
- Bypasses authentication during development
- Should be removed for production

### Management Commands
Base class pattern for data population:
- `populate_data.py` - Base command class
- `populate_contact_data.py` - Load contact fixtures
- `populate_job_data.py` - Load job fixtures
- Commands handle database reset and fixture loading

### Fixtures
Located in `/fixtures/` directory:
- Test data for development
- Organized by data type (contacts, jobs, etc.)
- JSON format for Django loaddata compatibility

## Business Logic Patterns

### Document Numbering
- Automatic generation using sequences
- Stored in Configuration model

### Status Workflows
Strict status progressions enforced at model level:
- Jobs: draft → in progress → complete
- Estimates: draft → open → accepted/rejected
- Worksheets follow estimate status via signals

### Line Item Management
- Shared base class for consistency
- Automatic line numbering
- Either task-based OR catalog-based
- Total calculations at property level

### Template System
- WorkOrderTemplates define products/services
- TaskTemplates provide reusable task definitions
- Hierarchical task structure supported
- Mapping rules control estimate generation

### Versioning
- Estimates support revision tracking
- Parent-child relationships maintain history
- Superseded status for old versions
- EstWorksheets follow same pattern

### Email Integration
- **Two-model architecture**: EmailRecord (permanent, minimal) + TempEmail (temporary cache, can be deleted)
- **Email server as source of truth**: On-demand fetching from IMAP, not stored in database
- **Session-based workflow**: Data passed between steps via Django session
- **Heuristic parsing**: Best-effort extraction of sender name, email, and company from signatures
- **Four business association scenarios**: Select suggested, select other, none (no company), none (with company) → confirmation page
- **Automatic linking**: Created jobs automatically linked back to originating email

## Signals and Events

### Signal Pattern
Located in `apps/jobs/signals.py`:
- `estimate_status_changed_for_worksheet` - Updates worksheet status
- Efficient bulk updates using Django ORM
- Only fires when relevant changes occur

## Testing

### Test Organization
- Tests in `/tests/` directory
- Model tests with and without fixtures
- CRUD operation tests
- Workflow tests (estimates, worksheets, etc.)
- Template system tests
- Email workflow tests (`test_email_workflow.py`) - 18 tests covering all branches of job-from-email creation

### Test Patterns
- Django TestCase for database tests
- Fixture loading for complex scenarios
- Validation testing for business rules
- Signal testing for side effects

## Security Considerations

### Current State
- DEBUG = True (development mode)
- Secret key hardcoded (needs rotation)
- AutoLogin middleware (remove for production)
- ALLOWED_HOSTS includes testserver, localhost

### Production Requirements
- Set DEBUG = False
- Use environment variables for secrets
- Remove AutoLoginMiddleware
- Configure proper authentication
- Set appropriate ALLOWED_HOSTS

## Database Configuration

### Development Settings
- MySQL database: minibini_db
- User: minibini_user
- Password: dev_password (hardcoded - change for production)
- Host: localhost
- Port: 3306

### Migration Management
- Custom User model requires careful migration
- AUTH_USER_MODEL set before first migration
- BaseLineItem abstract inheritance pattern

**IMPORTANT - Claude AI Workflow:**
- **NEVER run `python manage.py migrate`** - Only the human user will apply migrations to the development database when ready to test on a running server
- **OK to run `python manage.py makemigrations`** - Creating migration files is necessary for tests to pass
- **OK to run `python manage.py test`** - Tests automatically create and migrate their own test database (separate from main db)
- **Workflow:** Write code → Create migrations (makemigrations) → Write tests → Run tests (creates test db) → Human runs migrate on main db when ready

## Conventions and Best Practices

### Code Style
- Clear, descriptive names
- Docstrings for complex logic
- Type hints where helpful
- Django conventions followed

### Model Conventions
- AutoField primary keys with descriptive names
- ForeignKey on_delete explicitly defined
- Blank vs null carefully considered
- Clean methods for validation

### Business Logic Conventions
- Service classes link models and views

### View Conventions
- Explicit template paths
- Context dictionaries clearly defined
- Messages for user feedback
- Consistent redirect patterns

### Template Conventions
- **HTML must be as clean and minimal as possible**
- **NO inline styling except for absolutely necessary cases** (e.g., border/padding for readability of email content)
- **Use semantic HTML**: `<p>`, `<strong>`, `<em>`, `<fieldset>` instead of styled `<div>` elements
- **ALWAYS use Django's built-in messages system** - Never create custom message display divs
  - Messages are displayed in `base.html` template
  - Do NOT duplicate message handling in individual templates
  - Use `messages.success()`, `messages.error()`, `messages.info()`, `messages.warning()` in views
- **Form styling**:
  - Use `<p>` tags to wrap form fields
  - Use `<label>` with `<strong>` for field labels
  - Use `<br>` to separate label from input
  - Plain `<button>` elements without styling
  - Simple `<a>` links without button styling
- **No CSS frameworks** (Bootstrap, Tailwind, etc.)
- **No JavaScript** except for very specific cases (datetime-local inputs)
- Simple HTML structure - prioritize readability over appearance
- Django template tags for logic and control flow

#### Template Example - Correct Pattern

```html
{% extends 'base.html' %}

{% block content %}
<h2>Add Contact</h2>

<form method="post">
    {% csrf_token %}
    <p>
        <label for="name"><strong>Name *</strong></label><br>
        <input type="text" id="name" name="name" required>
    </p>

    <p>
        <label for="email"><strong>Email</strong></label><br>
        <input type="email" id="email" name="email">
    </p>

    <fieldset>
        <legend><strong>Business (Optional)</strong></legend>
        <p>
            <label for="business"><strong>Select Business</strong></label><br>
            <select id="business" name="business">
                <option value="">-- None --</option>
                {% for biz in businesses %}
                    <option value="{{ biz.id }}">{{ biz.name }}</option>
                {% endfor %}
            </select>
        </p>
    </fieldset>

    <p>
        <button type="submit">Save</button>
        <a href="{% url 'contact_list' %}">Cancel</a>
    </p>
</form>
{% endblock %}
```

#### Template Anti-Patterns - AVOID THESE

```html
<!-- DON'T: Duplicate message handling -->
{% if messages %}
    <div style="padding: 10px; background: green;">
        {% for message in messages %}
            {{ message }}
        {% endfor %}
    </div>
{% endif %}

<!-- DON'T: Inline styling on everything -->
<div style="margin-bottom: 15px;">
    <label style="font-weight: bold; color: #333;">Name</label>
    <input style="width: 100%; padding: 8px; border: 1px solid #ccc;">
</div>

<!-- DON'T: Styled buttons -->
<button style="background-color: #007bff; color: white; padding: 10px 20px;">
    Submit
</button>

<!-- DON'T: Links styled as buttons -->
<a href="/" style="background: #ccc; padding: 10px; text-decoration: none;">
    Cancel
</a>
```

## Key Business Workflows

### Job Creation Flow
1. Create Job with customer contact
2. Create EstWorksheet (optionally from template)
3. Add tasks to worksheet
4. Generate Estimate from worksheet
5. Send estimate to customer
6. Upon acceptance, create WorkOrder
7. Execute work and track time (Bleps)
8. Generate Invoice

### Template Usage
1. Define WorkOrderTemplate for standard products
2. Create TaskTemplates with labor/materials
3. Set up TaskMappings for line item generation
4. Use templates when creating EstWorksheets
5. System auto-generates tasks with quantities

### Revision Workflow
1. Estimate marked for revision
2. New version created with parent reference
3. Old version marked as superseded
4. EstWorksheet follows same pattern
5. History maintained through parent chain

### Email Integration and Job Creation Workflow
Email integration uses IMAP to fetch emails and create jobs from customer inquiries. The workflow handles contact/business discovery and creation:

1. **Email Fetching** (via email_inbox view)
   - Fetches emails from IMAP server (last 30 days on page load)
   - Creates/updates EmailRecord (permanent) and TempEmail (temporary cache)
   - Email server remains source of truth
   - TempEmail can be cleaned up after retention period while EmailRecord persists

2. **Create Job from Email** (via create_job_from_email view)
   - Parse sender email and name from headers
   - Extract company name from signature using heuristics
   - Extract email body for job description
   - Check if Contact exists with sender's email:

3. **Contact Exists Path**
   - Redirect directly to job creation with contact pre-selected
   - Pre-fill description from email body

4. **Contact Doesn't Exist Path**
   - Store sender info and company name in session
   - Check if Business exists (case-insensitive match on company name)
   - Redirect to contact creation with pre-filled data

5. **Contact Creation with Business Association** (add_contact view)
   - Four possible scenarios handled via dropdown:
     a. Select suggested business (pre-selected if match found)
     b. Select different existing business from dropdown
     c. Select "-- None --" with no company detected → create contact without business
     d. Select "-- None --" with company detected → intermediate confirmation page

6. **Business Confirmation** (confirm_create_business view)
   - Shows when "-- None --" selected but company was detected from email
   - User chooses: "Yes, Create Business" or "No, Continue Without Business"
   - If yes: creates Business and associates with Contact
   - Then redirects to job creation

7. **Job Creation and Email Linking** (job_create view)
   - Retrieves email_record_id from session
   - Creates job with contact and description
   - Links EmailRecord.job to created Job
   - Cleans up session data

#### Key Files
- `apps/core/services.py` - EmailService class for IMAP operations
- `apps/core/email_utils.py` - Email parsing utilities (parse_email_address, extract_company_from_signature, extract_email_body)
- `apps/core/views.py` - email_inbox, email_detail, create_job_from_email views
- `apps/contacts/views.py` - add_contact, confirm_create_business views with email workflow support
- `apps/jobs/views.py` - job_create view with email linking
- `templates/core/email_inbox.html` - Email list with "Create Job" button
- `templates/core/email_detail.html` - Full email view with "Create Job" button
- `templates/contacts/confirm_create_business.html` - Intermediate business confirmation page
- `fixtures/email_workflow_test_data.json` - Test data for email workflow
- `tests/test_email_workflow.py` - 18 tests covering all workflow branches

#### IMAP Configuration
Settings stored in `minibini/settings.py`:
- EMAIL_IMAP_SERVER - IMAP server hostname
- EMAIL_HOST_USER - Email account username
- EMAIL_HOST_PASSWORD - App password (for Gmail with 2FA)
- EMAIL_IMAP_FOLDER - Mailbox folder (default: 'INBOX')
- EMAIL_IMAP_SSL - Use SSL connection
- EMAIL_IMAP_PORT - Port number (optional)

## Future Considerations

### Planned Improvements
- Remove AutoLoginMiddleware for production
- Implement proper authentication system
- Add API endpoints for external integration
- Enhance reporting capabilities
- Implement proper permission system

### Technical Debt
- Move sensitive config to environment variables
- Add comprehensive logging
- Implement caching for performance
- Add database indexes for common queries
- Create deployment configuration

## Quick Reference

### Common Django Commands
```bash
python manage.py runserver          # Start development server
python manage.py makemigrations     # Create migrations
python manage.py migrate            # Apply migrations
python manage.py populate_job_data  # Load test data
python manage.py test               # Run test suite
```

### Key File Locations
- Models: `apps/*/models.py`
- Views: `apps/*/views.py`
- URLs: `apps/*/urls.py`
- Forms: `apps/*/forms.py`
- Templates: `templates/` and `apps/*/templates/`
- Settings: `minibini/settings.py`

### Database Access
- Admin: `/admin/` (requires superuser)
- Direct DB: MySQL client to localhost:3306

This documentation provides a comprehensive overview of the Minibini codebase structure, conventions, and key implementation details for quick onboarding in future sessions.