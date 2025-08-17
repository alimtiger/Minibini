from django.urls import path
from . import views

app_name = 'contacts'

urlpatterns = [
    path('', views.contact_list, name='contact_list'),
    path('<int:contact_id>/', views.contact_detail, name='contact_detail'),
    path('businesses/', views.business_list, name='business_list'),
    path('businesses/<int:business_id>/', views.business_detail, name='business_detail'),
]