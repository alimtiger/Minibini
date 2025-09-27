# Minibini Django Application - Codebase Documentation

## Overview

Minibini is a Django-based business management system designed for handling jobs, estimates, work orders, invoicing, and purchasing workflows. The application follows a minimal, functional design philosophy with no CSS framework or visual prettiness - just plain HTML forms and simple navigation.  It is in pre-production state and is changing rapidly as new features are added.  This document should be updated as changes are made.

## Core Architecture Principles

### Design Philosophy
- **Minimalist UI**: No CSS frameworks, no JavaScript, just plain HTML with minimal inline styles
- **Function over form**: Focus on functionality rather than aesthetics
- **Django-native**: Leverage Django's built-in features without unnecessary abstractions
- **Development-first**: Includes auto-login middleware and development conveniences

### Technology Stack
- **Framework**: Django 5.2.5
- **Database**: MySQL (development configuration)
- **Authentication**: Custom User model extending Django's AbstractUser
- **Frontend**: Plain HTML templates with minimal styling

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
- Extends base.html template
- Navigation in header/footer
- Message display for user feedback
- Tables for list views
- Simple forms without fancy styling
- Status indicators using CSS classes (e.g., .superseded)

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
- Minimal inline CSS only
- No external CSS frameworks
- Simple HTML structure
- Django template tags for logic

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