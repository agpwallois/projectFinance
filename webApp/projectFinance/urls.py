"""projectFinance URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
	https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
	1. Add an import:  from my_app import views
	2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
	1. Add an import:  from other_app.views import Home
	2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
	1. Import the include() function: from django.urls import include, path
	2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from home_page.views import HomePageView
from financial_model.views import FinancialModelView
from dashboard.views import projects_dashboard, create_project, delete_project
from authentication.views import login_view, logout_view, register_view



urlpatterns = [
	path('admin/', admin.site.urls),
	path('', HomePageView.as_view(), name='home'),
	path('login/', login_view, name='login'),  
	path('logout/', logout_view, name='logout'),
	path('register/', register_view, name='register'),
	path('projects/', projects_dashboard, name='project_list'),
	path('project/<int:id>/', FinancialModelView.as_view(), name='project_view'),
	path('projects/create/', create_project, name='create_project'),
	path('projects/delete/', delete_project, name='delete_project'),
]

admin.site.site_url = '/projects/'
admin.site.site_header = "Shango Administration"
