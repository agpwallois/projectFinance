# Generated by Django 4.2 on 2023-12-31 21:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0054_remove_computationresult_changed_result_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='discount_factor_valuation',
            field=models.DecimalField(decimal_places=2, default=7, max_digits=4),
        ),
    ]