# Generated by Django 4.2 on 2023-10-07 07:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0032_project_production_choice'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='production_choice',
        ),
    ]
