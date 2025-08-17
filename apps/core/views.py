from django.shortcuts import render, get_object_or_404
from .models import User

def user_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'core/user_list.html', {'users': users})

def user_detail(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    return render(request, 'core/user_detail.html', {'user': user})