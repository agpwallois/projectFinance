# Generated by Django 4.2 on 2025-03-27 18:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial_model', '0009_project_sensi_inflation_sponsor_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='financialmodel',
            name='model_type',
            field=models.CharField(default='default-identifier', max_length=255),
        ),
        migrations.AddField(
            model_name='financialmodel',
            name='sensitivity',
            field=models.CharField(default='default-identifier', max_length=255),
        ),
    ]
