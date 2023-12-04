# api_integration/urls.py
from django.urls import path
from . import views

app_name = 'api'  # Define the app's namespace

urlpatterns = [
    path('taxedamenagement/', views.get_data, name='get_data'),
    # Add other URL patterns for the 'api' namespace as needed
]