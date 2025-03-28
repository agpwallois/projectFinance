# Generated by Django 4.2 on 2025-01-07 07:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial_model', '0005_financialmodel_valuation'),
    ]

    operations = [
        migrations.CreateModel(
            name='DebtData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('debt_amount', models.FloatField(blank=True, null=True)),
                ('debt_schedule', models.JSONField(blank=True, null=True)),
            ],
        ),
    ]
