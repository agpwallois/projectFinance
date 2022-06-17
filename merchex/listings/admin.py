from django.contrib import admin
from listings.models import Project
from listings.models import listing

# Register your models here.

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'genre')

admin.site.register(Project, ProjectAdmin)
