from django.contrib import admin
from AjaxPost.models import SProject

# Register your models here.

class ContactAdmin(admin.ModelAdmin):
	list_display = ('name',)

admin.site.register(SProject, ContactAdmin)
