# Generated by Django 4.2 on 2025-04-02 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial_model', '0010_financialmodel_model_type_financialmodel_sensitivity'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='sponsor_irr',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=4),
        ),
    ]
