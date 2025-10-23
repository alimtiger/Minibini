from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Contact, Business

def contact_list(request):
    contacts = Contact.objects.all().order_by('last_name', 'first_name')
    return render(request, 'contacts/contact_list.html', {'contacts': contacts})

def contact_detail(request, contact_id):
    contact = get_object_or_404(Contact, contact_id=contact_id)
    return render(request, 'contacts/contact_detail.html', {'contact': contact})

def business_list(request):
    businesses = Business.objects.all().order_by('business_name')
    return render(request, 'contacts/business_list.html', {'businesses': businesses})

def business_detail(request, business_id):
    business = get_object_or_404(Business, business_id=business_id)
    contacts = Contact.objects.filter(business=business).order_by('last_name', 'first_name')
    return render(request, 'contacts/business_detail.html', {'business': business, 'contacts': contacts})

def add_contact(request):
    if request.method == 'POST':
        # Contact fields
        first_name = request.POST.get('first_name')
        middle_initial = request.POST.get('middle_initial')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        work_number = request.POST.get('work_number')
        mobile_number = request.POST.get('mobile_number')
        home_number = request.POST.get('home_number')
        address = request.POST.get('address')
        city = request.POST.get('city')
        postal_code = request.POST.get('postal_code')

        # Business fields
        business_name = request.POST.get('business_name')
        our_reference_code = request.POST.get('our_reference_code')
        business_number = request.POST.get('business_number')
        business_address = request.POST.get('business_address')
        tax_exemption_number = request.POST.get('tax_exemption_number')
        tax_cloud = request.POST.get('tax_cloud')

        if first_name and last_name:
            # Validate email is provided
            if not email or not email.strip():
                messages.error(request, 'Email address is required.')
                return render(request, 'contacts/add_contact.html')

            # Validate at least one phone number is provided
            if not any([work_number, mobile_number, home_number]):
                messages.error(request, 'At least one phone number (work, mobile, or home) is required.')
                return render(request, 'contacts/add_contact.html')

            business = None
            # Create business only if business name is provided and not just whitespace
            if business_name and business_name.strip():
                business = Business.objects.create(
                    business_name=business_name.strip(),
                    our_reference_code=our_reference_code.strip() if our_reference_code else '',
                    business_number=business_number.strip() if business_number else '',
                    business_address=business_address.strip() if business_address else '',
                    tax_exemption_number=tax_exemption_number.strip() if tax_exemption_number else '',
                    tax_cloud=tax_cloud.strip() if tax_cloud else ''
                )

            # Create contact
            contact = Contact.objects.create(
                first_name=first_name,
                middle_initial=middle_initial or '',
                last_name=last_name,
                email=email.strip(),
                work_number=work_number or '',
                mobile_number=mobile_number or '',
                home_number=home_number or '',
                addr1=address or '',
                city=city or '',
                postal_code=postal_code or '',
                business=business
            )

            success_msg = f'Contact "{contact.name}" has been added successfully.'
            if business:
                success_msg += f' Associated with business "{business_name}".'
            messages.success(request, success_msg)
            return redirect('contacts:contact_list')
        else:
            messages.error(request, 'First name and last name are required.')

    return render(request, 'contacts/add_contact.html')

def add_business_contact(request, business_id):
    business = get_object_or_404(Business, business_id=business_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        middle_initial = request.POST.get('middle_initial')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        work_number = request.POST.get('work_number')
        mobile_number = request.POST.get('mobile_number')
        home_number = request.POST.get('home_number')
        address = request.POST.get('address')
        city = request.POST.get('city')
        postal_code = request.POST.get('postal_code')

        if first_name and last_name:
            # Validate email is provided
            if not email or not email.strip():
                messages.error(request, 'Email address is required.')
                return render(request, 'contacts/add_business_contact.html', {'business': business})

            # Validate at least one phone number is provided
            if not any([work_number, mobile_number, home_number]):
                messages.error(request, 'At least one phone number (work, mobile, or home) is required.')
                return render(request, 'contacts/add_business_contact.html', {'business': business})

            contact = Contact.objects.create(
                first_name=first_name,
                middle_initial=middle_initial or '',
                last_name=last_name,
                email=email.strip(),
                work_number=work_number or '',
                mobile_number=mobile_number or '',
                home_number=home_number or '',
                addr1=address or '',
                city=city or '',
                postal_code=postal_code or '',
                business=business
            )
            messages.success(request, f'Contact "{contact.name}" has been added to {business.business_name}.')
            return redirect('contacts:business_detail', business_id=business.business_id)
        else:
            messages.error(request, 'First name and last name are required.')

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
                'first_name': request.POST.get(f'contact_{i}_first_name'),
                'middle_initial': request.POST.get(f'contact_{i}_middle_initial'),
                'last_name': request.POST.get(f'contact_{i}_last_name'),
                'email': request.POST.get(f'contact_{i}_email'),
                'work_number': request.POST.get(f'contact_{i}_work_number'),
                'mobile_number': request.POST.get(f'contact_{i}_mobile_number'),
                'home_number': request.POST.get(f'contact_{i}_home_number'),
                'address': request.POST.get(f'contact_{i}_address'),
                'city': request.POST.get(f'contact_{i}_city'),
                'postal_code': request.POST.get(f'contact_{i}_postal_code')
            }
            # Only add contact if first and last name are provided
            if contact_data['first_name'] and contact_data['first_name'].strip() and contact_data['last_name'] and contact_data['last_name'].strip():
                contacts_data.append(contact_data)

        # Validate: business name and at least one contact required
        if not business_name or not business_name.strip():
            messages.error(request, 'Business name is required.')
        elif not contacts_data:
            messages.error(request, 'At least one contact with first and last name is required.')
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

            # Validate and create contacts
            created_contacts = []
            for i, contact_data in enumerate(contacts_data):
                # Validate email
                if not contact_data['email'] or not contact_data['email'].strip():
                    messages.error(request, f'Email address is required for contact {i + 1}.')
                    return render(request, 'contacts/add_business.html')

                # Validate at least one phone number
                if not any([contact_data['work_number'], contact_data['mobile_number'], contact_data['home_number']]):
                    messages.error(request, f'At least one phone number is required for contact {i + 1}.')
                    return render(request, 'contacts/add_business.html')

                contact = Contact.objects.create(
                    first_name=contact_data['first_name'].strip(),
                    middle_initial=contact_data['middle_initial'].strip() if contact_data['middle_initial'] else '',
                    last_name=contact_data['last_name'].strip(),
                    email=contact_data['email'].strip(),
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
        first_name = request.POST.get('first_name')
        middle_initial = request.POST.get('middle_initial')
        last_name = request.POST.get('last_name')
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

        if first_name and last_name:
            # Validate email is provided
            if not email or not email.strip():
                messages.error(request, 'Email address is required.')
                existing_businesses = Business.objects.all().order_by('business_name')
                return render(request, 'contacts/edit_contact.html', {
                    'contact': contact,
                    'existing_businesses': existing_businesses
                })

            # Validate at least one phone number is provided
            if not any([work_number, mobile_number, home_number]):
                messages.error(request, 'At least one phone number (work, mobile, or home) is required.')
                existing_businesses = Business.objects.all().order_by('business_name')
                return render(request, 'contacts/edit_contact.html', {
                    'contact': contact,
                    'existing_businesses': existing_businesses
                })

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
            contact.first_name = first_name
            contact.middle_initial = middle_initial or ''
            contact.last_name = last_name
            contact.email = email.strip()
            contact.work_number = work_number or ''
            contact.mobile_number = mobile_number or ''
            contact.home_number = home_number or ''
            contact.addr1 = address or ''
            contact.city = city or ''
            contact.postal_code = postal_code or ''
            contact.business = business
            contact.save()

            messages.success(request, f'Contact "{contact.name}" has been updated successfully.')
            return redirect('contacts:contact_detail', contact_id=contact.contact_id)
        else:
            messages.error(request, 'First name and last name are required.')

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