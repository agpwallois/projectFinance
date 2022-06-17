from django.contrib import admin
from webApp.models import Project
from webApp.models import webApp

# Register your models here.

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'genre')

admin.site.register(Project, ProjectAdmin)
