# Generated by Django 4.2 on 2024-02-17 10:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0057_project_contract'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='rotor_diameter',
            field=models.DecimalField(decimal_places=2, default=92, max_digits=4),
        ),
    ]
