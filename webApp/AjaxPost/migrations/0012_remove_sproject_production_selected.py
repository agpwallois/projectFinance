# Generated by Django 4.0.4 on 2022-07-30 12:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0011_remove_sproject_price_elec_high_y1_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sproject',
            name='production_selected',
        ),
    ]