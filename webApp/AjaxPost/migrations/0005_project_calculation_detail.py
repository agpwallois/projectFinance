# Generated by Django 4.2 on 2023-06-27 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0004_project_shl_margin_project_subgearing'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='calculation_detail',
            field=models.IntegerField(default='1'),
        ),
    ]
