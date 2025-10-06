from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Contact, Business

def contact_list(request):
    contacts = Contact.objects.all().order_by('name')
    return render(request, 'contacts/contact_list.html', {'contacts': contacts})

def contact_detail(request, contact_id):
    contact = get_object_or_404(Contact, contact_id=contact_id)
    return render(request, 'contacts/contact_detail.html', {'contact': contact})

def business_list(request):
    businesses = Business.objects.all().order_by('business_name')
    return render(request, 'contacts/business_list.html', {'businesses': businesses})

def business_detail(request, business_id):
    business = get_object_or_404(Business, business_id=business_id)
    contacts = Contact.objects.filter(business=business).order_by('name')
    return render(request, 'contacts/business_detail.html', {'business': business, 'contacts': contacts})

def add_contact(request):
    # Get pre-filled data from session (from email workflow)
    initial_name = request.session.get('contact_name', '')
    initial_email = request.session.get('contact_email', '')
    initial_business_name = request.session.get('contact_company', '')
    suggested_business_id = request.session.get('suggested_business_id', None)
    email_record_id = request.session.get('email_record_id_for_job', None)
    email_body = request.session.get('email_body_for_job', '')

    # Get all businesses for dropdown
    all_businesses = Business.objects.all().order_by('business_name')

    if request.method == 'POST':
        # Contact fields
        name = request.POST.get('name')
        email = request.POST.get('email')
        work_number = request.POST.get('work_number')
        mobile_number = request.POST.get('mobile_number')
        home_number = request.POST.get('home_number')
        address = request.POST.get('address')
        city = request.POST.get('city')
        postal_code = request.POST.get('postal_code')

        # Business selection from dropdown
        business_id = request.POST.get('business_id')

        if name:
            business = None

            # Get selected business from dropdown (if not "NONE")
            if business_id and business_id != 'NONE':
                try:
                    business = Business.objects.get(business_id=int(business_id))
                except (Business.DoesNotExist, ValueError):
                    pass

            # Create contact
            contact = Contact.objects.create(
                name=name,
                email=email or '',
                work_number=work_number or '',
                mobile_number=mobile_number or '',
                home_number=home_number or '',
                addr1=address or '',
                city=city or '',
                postal_code=postal_code or '',
                business=business
            )

            success_msg = f'Contact "{name}" has been added successfully.'
            if business:
                success_msg += f' Associated with business "{business.business_name}".'
            messages.success(request, success_msg)

            # If NONE was selected and we came from email workflow with a company name
            # Redirect to intermediate page to ask about creating new business
            if business_id == 'NONE' and email_record_id and initial_business_name:
                # Store contact_id in session for the intermediate page
                request.session['contact_id_for_business'] = contact.contact_id
                return redirect('contacts:confirm_create_business')

            # Clear session data
            request.session.pop('contact_name', None)
            request.session.pop('contact_email', None)
            request.session.pop('contact_company', None)
            request.session.pop('suggested_business_id', None)

            # If this came from email workflow, redirect to job creation
            if email_record_id:
                from django.urls import reverse
                url = reverse('jobs:create') + f'?contact_id={contact.contact_id}&description={email_body[:200]}'
                return redirect(url)

            return redirect('contacts:contact_list')
        else:
            messages.error(request, 'Name is required.')

    return render(request, 'contacts/add_contact.html', {
        'initial_name': initial_name,
        'initial_email': initial_email,
        'initial_business_name': initial_business_name,
        'suggested_business_id': suggested_business_id,
        'all_businesses': all_businesses,
    })

def confirm_create_business(request):
    """
    Intermediate page shown when user selects NONE for business but a company
    name was extracted from email. Asks if they want to create a new business.
    """
    # Get session data
    contact_id = request.session.get('contact_id_for_business')
    initial_business_name = request.session.get('contact_company', '')
    email_record_id = request.session.get('email_record_id_for_job', None)
    email_body = request.session.get('email_body_for_job', '')

    if not contact_id or not initial_business_name:
        messages.error(request, 'Session expired. Please try again.')
        return redirect('contacts:contact_list')

    try:
        contact = Contact.objects.get(contact_id=contact_id)
    except Contact.DoesNotExist:
        messages.error(request, 'Contact not found.')
        return redirect('contacts:contact_list')

    if request.method == 'POST':
        create_business = request.POST.get('create_business')

        if create_business == 'yes':
            # Create the business
            business = Business.objects.create(
                business_name=initial_business_name.strip(),
                # Other fields can be left blank for now
            )

            # Associate contact with the new business
            contact.business = business
            contact.save()

            messages.success(request, f'Business "{business.business_name}" created and associated with contact.')
        else:
            # User chose to skip business creation
            messages.info(request, 'Continuing without creating a business.')

        # Clear session data
        request.session.pop('contact_id_for_business', None)
        request.session.pop('contact_name', None)
        request.session.pop('contact_email', None)
        request.session.pop('contact_company', None)
        request.session.pop('suggested_business_id', None)

        # Redirect to job creation
        if email_record_id:
            from django.urls import reverse
            url = reverse('jobs:create') + f'?contact_id={contact.contact_id}&description={email_body[:200]}'
            return redirect(url)

        return redirect('contacts:contact_detail', contact_id=contact.contact_id)

    return render(request, 'contacts/confirm_create_business.html', {
        'contact': contact,
        'business_name': initial_business_name,
    })

def add_business_contact(request, business_id):
    business = get_object_or_404(Business, business_id=business_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        work_number = request.POST.get('work_number')
        mobile_number = request.POST.get('mobile_number')
        home_number = request.POST.get('home_number')
        address = request.POST.get('address')
        city = request.POST.get('city')
        postal_code = request.POST.get('postal_code')

        if name:
            contact = Contact.objects.create(
                name=name,
                email=email or '',
                work_number=work_number or '',
                mobile_number=mobile_number or '',
                home_number=home_number or '',
                addr1=address or '',
                city=city or '',
                postal_code=postal_code or '',
                business=business
            )
            messages.success(request, f'Contact "{name}" has been added to {business.business_name}.')
            return redirect('contacts:business_detail', business_id=business.business_id)
        else:
            messages.error(request, 'Name is required.')

    return render(request, 'contacts/add_business_contact.html', {'business': business})

def add_business(request):
    if request.method == 'POST':
        # Business fields
        business_name = request.POST.get('business_name')
        our_reference_code = request.POST.get('our_reference_code')
        business_number = request.POST.get('business_number')
        business_address = request.POST.get('business_address')
        tax_exemption_number = request.POST.get('tax_exemption_number')
        tax_cloud = request.POST.get('tax_cloud')

        # Get number of contacts
        contact_count = int(request.POST.get('contact_count', 1))

        # Collect contact data
        contacts_data = []
        for i in range(contact_count):
            contact_data = {
                'name': request.POST.get(f'contact_{i}_name'),
                'email': request.POST.get(f'contact_{i}_email'),
                'work_number': request.POST.get(f'contact_{i}_work_number'),
                'mobile_number': request.POST.get(f'contact_{i}_mobile_number'),
                'home_number': request.POST.get(f'contact_{i}_home_number'),
                'address': request.POST.get(f'contact_{i}_address'),
                'city': request.POST.get(f'contact_{i}_city'),
                'postal_code': request.POST.get(f'contact_{i}_postal_code')
            }
            # Only add contact if name is provided
            if contact_data['name'] and contact_data['name'].strip():
                contacts_data.append(contact_data)

        # Validate: business name and at least one contact required
        if not business_name or not business_name.strip():
            messages.error(request, 'Business name is required.')
        elif not contacts_data:
            messages.error(request, 'At least one contact with a name is required.')
        else:
            # Create business
            business = Business.objects.create(
                business_name=business_name.strip(),
                our_reference_code=our_reference_code.strip() if our_reference_code else '',
                business_number=business_number.strip() if business_number else '',
                business_address=business_address.strip() if business_address else '',
                tax_exemption_number=tax_exemption_number.strip() if tax_exemption_number else '',
                tax_cloud=tax_cloud.strip() if tax_cloud else ''
            )

            # Create contacts
            created_contacts = []
            for contact_data in contacts_data:
                contact = Contact.objects.create(
                    name=contact_data['name'].strip(),
                    email=contact_data['email'].strip() if contact_data['email'] else '',
                    work_number=contact_data['work_number'].strip() if contact_data['work_number'] else '',
                    mobile_number=contact_data['mobile_number'].strip() if contact_data['mobile_number'] else '',
                    home_number=contact_data['home_number'].strip() if contact_data['home_number'] else '',
                    addr1=contact_data['address'].strip() if contact_data['address'] else '',
                    city=contact_data['city'].strip() if contact_data['city'] else '',
                    postal_code=contact_data['postal_code'].strip() if contact_data['postal_code'] else '',
                    business=business
                )
                created_contacts.append(contact.name)

            success_msg = f'Business "{business_name}" has been created with {len(created_contacts)} contact(s): {", ".join(created_contacts)}.'
            messages.success(request, success_msg)
            return redirect('contacts:business_list')

    return render(request, 'contacts/add_business.html')

def edit_contact(request, contact_id):
    contact = get_object_or_404(Contact, contact_id=contact_id)

    if request.method == 'POST':
        # Contact fields
        name = request.POST.get('name')
        email = request.POST.get('email')
        work_number = request.POST.get('work_number')
        mobile_number = request.POST.get('mobile_number')
        home_number = request.POST.get('home_number')
        address = request.POST.get('address')
        city = request.POST.get('city')
        postal_code = request.POST.get('postal_code')

        # Business fields
        business_selection_mode = request.POST.get('business_selection_mode')
        existing_business_id = request.POST.get('existing_business_id')
        business_name = request.POST.get('business_name')
        our_reference_code = request.POST.get('our_reference_code')
        business_number = request.POST.get('business_number')
        business_address = request.POST.get('business_address')
        tax_exemption_number = request.POST.get('tax_exemption_number')
        tax_cloud = request.POST.get('tax_cloud')

        if name:
            # Check if contact has open jobs before allowing business change
            from apps.jobs.models import Job

            # Business association is changing if:
            # 1. Contact currently has no business but will be assigned one
            # 2. Contact currently has a business but will be changed to a different one or none
            current_business_id = contact.business.business_id if contact.business else None
            new_business_id = None

            if business_selection_mode == 'existing' and existing_business_id:
                new_business_id = int(existing_business_id)
            elif business_selection_mode == 'new' and business_name and business_name.strip():
                # For new business, we'll check if it's actually creating a new business later
                # For now, we know it's changing
                pass
            elif business_selection_mode == 'name_search' and business_name and business_name.strip():
                from django.db.models import Q
                existing_business = Business.objects.filter(business_name__iexact=business_name.strip()).first()
                if existing_business:
                    new_business_id = existing_business.business_id

            # Check if business is actually changing
            business_changing = (
                (current_business_id is None and (new_business_id is not None or
                 (business_selection_mode == 'new' and business_name and business_name.strip()))) or
                (current_business_id is not None and (new_business_id != current_business_id or
                 business_selection_mode is None or business_selection_mode == '' or
                 (business_selection_mode == 'new' and business_name and business_name.strip())))
            )

            if business_changing:
                # Check for open jobs (not complete or rejected)
                open_jobs = Job.objects.filter(
                    contact=contact
                ).exclude(
                    status__in=['complete', 'rejected']
                )

                if open_jobs.exists():
                    job_numbers = list(open_jobs.values_list('job_number', flat=True))
                    messages.error(
                        request,
                        f'Cannot change business association for "{contact.name}" because they have open jobs: {", ".join(job_numbers)}. '
                        'Complete or reject these jobs before changing the business association.'
                    )
                    existing_businesses = Business.objects.all().order_by('business_name')
                    return render(request, 'contacts/edit_contact.html', {
                        'contact': contact,
                        'existing_businesses': existing_businesses
                    })

            # Handle business association based on selection mode
            business = None

            if business_selection_mode == 'existing' and existing_business_id:
                # Associate with existing business - NO MODIFICATION ALLOWED
                try:
                    business = Business.objects.get(business_id=existing_business_id)
                    # Existing business is used as-is, no fields are updated
                except Business.DoesNotExist:
                    messages.error(request, 'Selected business no longer exists.')
                    existing_businesses = Business.objects.all().order_by('business_name')
                    return render(request, 'contacts/edit_contact.html', {
                        'contact': contact,
                        'existing_businesses': existing_businesses
                    })

            elif business_selection_mode == 'new' and business_name and business_name.strip():
                # Create new business - this will dissociate from current business
                # First, note the current business for messaging
                old_business_name = contact.business.business_name if contact.business else None

                # Check if business with this name already exists
                existing_business = Business.objects.filter(business_name__iexact=business_name.strip()).first()
                if existing_business:
                    # Use existing business instead of creating duplicate
                    business = existing_business
                    if old_business_name:
                        messages.info(request, f'Contact removed from "{old_business_name}" and associated with existing business "{existing_business.business_name}".')
                    else:
                        messages.info(request, f'Contact associated with existing business "{existing_business.business_name}".')
                else:
                    # Create new business (contact will be dissociated from old business)
                    business = Business.objects.create(
                        business_name=business_name.strip(),
                        our_reference_code=our_reference_code.strip() if our_reference_code else '',
                        business_number=business_number.strip() if business_number else '',
                        business_address=business_address.strip() if business_address else '',
                        tax_exemption_number=tax_exemption_number.strip() if tax_exemption_number else '',
                        tax_cloud=tax_cloud.strip() if tax_cloud else ''
                    )
                    if old_business_name:
                        messages.success(request, f'Contact removed from "{old_business_name}" and associated with new business "{business_name.strip()}".')
                    else:
                        messages.success(request, f'Contact associated with new business "{business_name.strip()}".')

            elif business_selection_mode == 'name_search' and business_name and business_name.strip():
                # Search for existing business by name - NO MODIFICATION ALLOWED
                existing_business = Business.objects.filter(business_name__iexact=business_name.strip()).first()
                if existing_business:
                    business = existing_business
                    # Existing business is used as-is, no fields are updated
                    messages.info(request, f'Contact associated with existing business "{existing_business.business_name}".')
                else:
                    messages.error(request, f'No business found with name "{business_name.strip()}". Please select from existing businesses or create a new one.')
                    existing_businesses = Business.objects.all().order_by('business_name')
                    return render(request, 'contacts/edit_contact.html', {
                        'contact': contact,
                        'existing_businesses': existing_businesses
                    })

            # business remains None if no selection mode or empty fields

            # Update contact
            contact.name = name
            contact.email = email or ''
            contact.work_number = work_number or ''
            contact.mobile_number = mobile_number or ''
            contact.home_number = home_number or ''
            contact.addr1 = address or ''
            contact.city = city or ''
            contact.postal_code = postal_code or ''
            contact.business = business
            contact.save()

            messages.success(request, f'Contact "{name}" has been updated successfully.')
            return redirect('contacts:contact_detail', contact_id=contact.contact_id)
        else:
            messages.error(request, 'Name is required.')

    existing_businesses = Business.objects.all().order_by('business_name')
    return render(request, 'contacts/edit_contact.html', {
        'contact': contact,
        'existing_businesses': existing_businesses
    })

def edit_business(request, business_id):
    business = get_object_or_404(Business, business_id=business_id)

    if request.method == 'POST':
        # Business fields
        business_name = request.POST.get('business_name')
        our_reference_code = request.POST.get('our_reference_code')
        business_number = request.POST.get('business_number')
        business_address = request.POST.get('business_address')
        tax_exemption_number = request.POST.get('tax_exemption_number')
        tax_cloud = request.POST.get('tax_cloud')

        if business_name and business_name.strip():
            # Check if another business with this name already exists
            existing_business = Business.objects.filter(
                business_name__iexact=business_name.strip()
            ).exclude(business_id=business.business_id).first()

            if existing_business:
                messages.error(
                    request,
                    f'A business with the name "{business_name.strip()}" already exists. '
                    'Business names must be unique.'
                )
            else:
                # Update business
                business.business_name = business_name.strip()
                business.our_reference_code = our_reference_code.strip() if our_reference_code else ''
                business.business_number = business_number.strip() if business_number else ''
                business.business_address = business_address.strip() if business_address else ''
                business.tax_exemption_number = tax_exemption_number.strip() if tax_exemption_number else ''
                business.tax_cloud = tax_cloud.strip() if tax_cloud else ''
                business.save()

                messages.success(request, f'Business "{business_name.strip()}" has been updated successfully.')
                return redirect('contacts:business_detail', business_id=business.business_id)
        else:
            messages.error(request, 'Business name is required.')

    return render(request, 'contacts/edit_business.html', {
        'business': business
    })