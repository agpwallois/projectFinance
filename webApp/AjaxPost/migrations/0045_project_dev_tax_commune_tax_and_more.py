# Generated by Django 4.2 on 2023-11-26 09:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0044_project_timeline_quarters_ceiling_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='dev_tax_commune_tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='project',
            name='dev_tax_department_tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='project',
            name='dev_tax_intercommunal_tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='project',
            name='dev_tax_regional_tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='project',
            name='dev_tax_taxable_base_solar',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='project',
            name='dev_tax_taxable_base_wind',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='project',
            name='panels_surface',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AlterField(
            model_name='project',
            name='timeline_quarters_ceiling',
            field=models.BooleanField(default=False, null=True),
        ),
    ]
