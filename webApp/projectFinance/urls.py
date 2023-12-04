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
from AjaxPost.views import project_list, project_view, test, testsimple
from authentication.views import LoginPageView
from api_integration import views


urlpatterns = [
	path('admin/', admin.site.urls),
	path('', LoginPageView.as_view(), name='login'),
	path('projects/', project_list, name='project_list'),
	path('project/<int:id>/', project_view, name='project_view'),
	path('test/<int:id>/', test, name='test'),
	path('testsimple', testsimple, name='testsimple'),
	path('api/', include('api_integration.urls', namespace='api')),

]

admin.site.site_url = '/projects/'
admin.site.site_header = "Shango Administration"
