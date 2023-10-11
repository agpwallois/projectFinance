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
from django.urls import path
from AjaxPost import views as AjaxPost
import authentication.views

urlpatterns = [
	path('admin/', admin.site.urls, name='project-admin'),
	path('auth/', authentication.views.LoginPageView.as_view(), name='login'),
	path('', AjaxPost.ProjectListView.as_view(), name='project-list'),
	path('projects/<int:id>/', AjaxPost.project_view, name='project_view'),
	]

