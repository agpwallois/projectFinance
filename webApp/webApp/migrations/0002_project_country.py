# Generated by Django 4.0.4 on 2022-06-18 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='country',
            field=models.CharField(default='France', max_length=20),
            preserve_default=False,
        ),
    ]