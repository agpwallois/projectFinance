# Generated by Django 4.0.4 on 2022-07-30 19:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0014_rename_sproject_project'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='country',
        ),
        migrations.RemoveField(
            model_name='project',
            name='genre',
        ),
    ]