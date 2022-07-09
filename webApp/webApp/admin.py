from django.contrib import admin
from webApp.models import Project
from webApp.models import webApp
from AjaxPost.models import SProject


# Register your models here.

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'genre')
	readonly_fields = ('id',)

admin.site.register(Project, ProjectAdmin)
