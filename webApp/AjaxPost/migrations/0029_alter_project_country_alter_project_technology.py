# Generated by Django 4.0.4 on 2022-08-26 17:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0028_alter_project_country_alter_project_technology'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='country',
            field=models.IntegerField(choices=[('1', 'Italy'), ('2', 'France'), ('3', 'Spain')], default=2),
        ),
        migrations.AlterField(
            model_name='project',
            name='technology',
            field=models.IntegerField(choices=[('1', 'Solar'), ('2', 'Wind')], default=1),
        ),
    ]