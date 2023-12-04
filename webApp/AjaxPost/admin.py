from django.contrib import admin
from AjaxPost.models import Project

# Register your models here.

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name','country','commune', 'technology','created_date','updated_date')
	fields = ('name', 'country','commune', 'technology')

admin.site.register(Project, ProjectAdmin)
