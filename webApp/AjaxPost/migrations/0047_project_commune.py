# Generated by Django 4.2 on 2023-11-26 12:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0046_remove_project_dev_tax_intercommunal_tax_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='commune',
            field=models.CharField(choices=[('Ambronay', 'Ambronay'), ('Anglefort', 'Anglefort'), ('Apremont', 'Apremont')], default='Apremont', max_length=100),
        ),
    ]