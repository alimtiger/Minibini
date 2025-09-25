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
        business_name = request.POST.get('business_name')
        our_reference_code = request.POST.get('our_reference_code')
        business_number = request.POST.get('business_number')
        business_address = request.POST.get('business_address')
        tax_exemption_number = request.POST.get('tax_exemption_number')
        tax_cloud = request.POST.get('tax_cloud')

        if name:
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
                success_msg += f' Associated with business "{business_name}".'
            messages.success(request, success_msg)
            return redirect('contacts:contact_list')
        else:
            messages.error(request, 'Name is required.')

    return render(request, 'contacts/add_contact.html')

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