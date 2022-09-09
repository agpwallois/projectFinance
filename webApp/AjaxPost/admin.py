from django.contrib import admin
from AjaxPost.models import Project

# Register your models here.

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name','country','technology')
	fields = ('name', 'country','technology')

admin.site.register(Project, ProjectAdmin)
