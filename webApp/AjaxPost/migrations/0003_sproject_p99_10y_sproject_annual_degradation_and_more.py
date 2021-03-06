# Generated by Django 4.0.4 on 2022-07-17 13:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AjaxPost', '0002_remove_sproject_p99_10y_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sproject',
            name='P99_10y',
            field=models.IntegerField(default='2000'),
        ),
        migrations.AddField(
            model_name='sproject',
            name='annual_degradation',
            field=models.DecimalField(decimal_places=0, default=2, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='availability',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='p50',
            field=models.IntegerField(default='2000'),
        ),
        migrations.AddField(
            model_name='sproject',
            name='p90_10y',
            field=models.IntegerField(default='2000'),
        ),
        migrations.AddField(
            model_name='sproject',
            name='panels_capacity',
            field=models.IntegerField(default='2000'),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m1',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m10',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m11',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m12',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m2',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m3',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m4',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m5',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m6',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m7',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m8',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='sproject',
            name='seasonality_m9',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=4),
        ),
    ]
