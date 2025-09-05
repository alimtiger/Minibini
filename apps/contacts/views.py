from django.shortcuts import render, get_object_or_404
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