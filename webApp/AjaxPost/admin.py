from django.contrib import admin
from AjaxPost.models import Project

# Register your models here.

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name',)

admin.site.register(Project, ProjectAdmin)
