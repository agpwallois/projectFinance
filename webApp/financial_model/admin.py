from django.contrib import admin
from financial_model.model_project import Project

# Register your models here.

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'country', 'technology', 'created_date', 'updated_date')

admin.site.register(Project, ProjectAdmin)