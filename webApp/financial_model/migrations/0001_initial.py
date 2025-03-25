# Generated by Django 4.2 on 2024-08-13 10:19

import datetime
from django.db import migrations, models
import django.db.models.deletion
import financial_model.model_financial_model


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FinancialModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('financial_model', models.JSONField(default=dict, encoder=financial_model.model_financial_model.CustomJSONEncoder)),
                ('senior_debt_amount', models.FloatField(default=1000.0)),
                ('identifier', models.CharField(default='default-identifier', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('country', models.CharField(choices=[('France', 'France'), ('Spain', 'Spain')], default='France', max_length=100)),
                ('technology', models.CharField(choices=[('Solar - ground-mounted', 'Solar - ground-mounted'), ('Solar - rooftop', 'Solar - rooftop'), ('Wind', 'Wind')], default='Solar', max_length=100)),
                ('start_construction', models.DateField(blank=True, default=datetime.date(2022, 1, 1), null=True)),
                ('end_construction', models.DateField(blank=True, default=datetime.date(2022, 12, 31), null=True)),
                ('operating_life', models.IntegerField(default='25')),
                ('liquidation', models.IntegerField(default='6')),
                ('periodicity', models.IntegerField(default='6')),
                ('panels_capacity', models.IntegerField(blank=True, default='2500', null=True)),
                ('annual_degradation', models.DecimalField(blank=True, decimal_places=3, default=0.4, max_digits=5, null=True)),
                ('p50', models.IntegerField(default='1800')),
                ('p75', models.IntegerField(default='1750')),
                ('p90_10y', models.IntegerField(default='1700')),
                ('P99_10y', models.IntegerField(blank=True, default='1600', null=True)),
                ('production_choice', models.IntegerField(default='1')),
                ('seasonality_m1', models.DecimalField(decimal_places=3, default=0.03, max_digits=5)),
                ('seasonality_m2', models.DecimalField(decimal_places=3, default=0.05, max_digits=5)),
                ('seasonality_m3', models.DecimalField(decimal_places=3, default=0.09, max_digits=5)),
                ('seasonality_m4', models.DecimalField(decimal_places=3, default=0.11, max_digits=5)),
                ('seasonality_m5', models.DecimalField(decimal_places=3, default=0.13, max_digits=5)),
                ('seasonality_m6', models.DecimalField(decimal_places=3, default=0.13, max_digits=5)),
                ('seasonality_m7', models.DecimalField(decimal_places=3, default=0.13, max_digits=5)),
                ('seasonality_m8', models.DecimalField(decimal_places=3, default=0.12, max_digits=5)),
                ('seasonality_m9', models.DecimalField(decimal_places=3, default=0.1, max_digits=5)),
                ('seasonality_m10', models.DecimalField(decimal_places=3, default=0.06, max_digits=5)),
                ('seasonality_m11', models.DecimalField(decimal_places=3, default=0.03, max_digits=5)),
                ('seasonality_m12', models.DecimalField(decimal_places=3, default=0.02, max_digits=5)),
                ('costs_m1', models.IntegerField(default='200')),
                ('costs_m2', models.IntegerField(default='0')),
                ('costs_m3', models.IntegerField(default='500')),
                ('costs_m4', models.IntegerField(default='300')),
                ('costs_m5', models.IntegerField(default='0')),
                ('costs_m6', models.IntegerField(default='1000')),
                ('costs_m7', models.IntegerField(default='700')),
                ('costs_m8', models.IntegerField(default='600')),
                ('costs_m9', models.IntegerField(default='200')),
                ('costs_m10', models.IntegerField(default='300')),
                ('costs_m11', models.IntegerField(default='0')),
                ('costs_m12', models.IntegerField(default='500')),
                ('costs_m13', models.IntegerField(default='0')),
                ('costs_m14', models.IntegerField(default='0')),
                ('costs_m15', models.IntegerField(default='0')),
                ('costs_m16', models.IntegerField(default='0')),
                ('costs_m17', models.IntegerField(default='0')),
                ('costs_m18', models.IntegerField(default='0')),
                ('costs_m19', models.IntegerField(default='0')),
                ('costs_m20', models.IntegerField(default='0')),
                ('costs_m21', models.IntegerField(default='0')),
                ('costs_m22', models.IntegerField(default='0')),
                ('costs_m23', models.IntegerField(default='0')),
                ('costs_m24', models.IntegerField(default='0')),
                ('start_contract', models.DateField(blank=True, default=datetime.date(2023, 1, 1), null=True)),
                ('end_contract', models.DateField(blank=True, default=datetime.date(2042, 12, 31), null=True)),
                ('contract_price', models.DecimalField(decimal_places=2, default=130, max_digits=6)),
                ('contract_indexation_start_date', models.DateField(blank=True, default=datetime.date(2023, 1, 1), null=True)),
                ('index_rate_contract', models.DecimalField(decimal_places=2, default=2, max_digits=4)),
                ('price_elec_indexation_start_date', models.DateField(blank=True, default=datetime.date(2022, 1, 1), null=True)),
                ('index_rate_merchant', models.DecimalField(decimal_places=2, default=2, max_digits=4)),
                ('price_elec_choice', models.IntegerField(default='1')),
                ('price_elec_low_y1', models.IntegerField(default='50')),
                ('price_elec_low_y2', models.IntegerField(default='50')),
                ('price_elec_low_y3', models.IntegerField(default='50')),
                ('price_elec_low_y4', models.IntegerField(default='50')),
                ('price_elec_low_y5', models.IntegerField(default='50')),
                ('price_elec_low_y6', models.IntegerField(default='50')),
                ('price_elec_low_y7', models.IntegerField(default='50')),
                ('price_elec_low_y8', models.IntegerField(default='50')),
                ('price_elec_low_y9', models.IntegerField(default='50')),
                ('price_elec_low_y10', models.IntegerField(default='50')),
                ('price_elec_low_y11', models.IntegerField(default='50')),
                ('price_elec_low_y12', models.IntegerField(default='50')),
                ('price_elec_low_y13', models.IntegerField(default='50')),
                ('price_elec_low_y14', models.IntegerField(default='50')),
                ('price_elec_low_y15', models.IntegerField(default='50')),
                ('price_elec_low_y16', models.IntegerField(default='50')),
                ('price_elec_low_y17', models.IntegerField(default='50')),
                ('price_elec_low_y18', models.IntegerField(default='50')),
                ('price_elec_low_y19', models.IntegerField(default='50')),
                ('price_elec_low_y20', models.IntegerField(default='50')),
                ('price_elec_low_y21', models.IntegerField(default='50')),
                ('price_elec_low_y22', models.IntegerField(default='50')),
                ('price_elec_low_y23', models.IntegerField(default='50')),
                ('price_elec_low_y24', models.IntegerField(default='50')),
                ('price_elec_low_y25', models.IntegerField(default='50')),
                ('price_elec_low_y26', models.IntegerField(default='50')),
                ('price_elec_low_y27', models.IntegerField(default='50')),
                ('price_elec_low_y28', models.IntegerField(default='50')),
                ('price_elec_low_y29', models.IntegerField(default='50')),
                ('price_elec_low_y30', models.IntegerField(default='50')),
                ('price_elec_low_y31', models.IntegerField(default='50')),
                ('price_elec_low_y32', models.IntegerField(default='50')),
                ('price_elec_low_y33', models.IntegerField(default='50')),
                ('price_elec_low_y34', models.IntegerField(default='50')),
                ('price_elec_low_y35', models.IntegerField(default='50')),
                ('price_elec_low_y36', models.IntegerField(default='50')),
                ('price_elec_low_y37', models.IntegerField(default='50')),
                ('price_elec_low_y38', models.IntegerField(default='50')),
                ('price_elec_low_y39', models.IntegerField(default='50')),
                ('price_elec_low_y40', models.IntegerField(default='50')),
                ('price_elec_low_y41', models.IntegerField(default='50')),
                ('price_elec_low_y42', models.IntegerField(default='50')),
                ('price_elec_med_y1', models.IntegerField(default='100')),
                ('price_elec_med_y2', models.IntegerField(default='100')),
                ('price_elec_med_y3', models.IntegerField(default='100')),
                ('price_elec_med_y4', models.IntegerField(default='100')),
                ('price_elec_med_y5', models.IntegerField(default='100')),
                ('price_elec_med_y6', models.IntegerField(default='100')),
                ('price_elec_med_y7', models.IntegerField(default='100')),
                ('price_elec_med_y8', models.IntegerField(default='100')),
                ('price_elec_med_y9', models.IntegerField(default='100')),
                ('price_elec_med_y10', models.IntegerField(default='100')),
                ('price_elec_med_y11', models.IntegerField(default='100')),
                ('price_elec_med_y12', models.IntegerField(default='100')),
                ('price_elec_med_y13', models.IntegerField(default='100')),
                ('price_elec_med_y14', models.IntegerField(default='100')),
                ('price_elec_med_y15', models.IntegerField(default='100')),
                ('price_elec_med_y16', models.IntegerField(default='100')),
                ('price_elec_med_y17', models.IntegerField(default='100')),
                ('price_elec_med_y18', models.IntegerField(default='100')),
                ('price_elec_med_y19', models.IntegerField(default='100')),
                ('price_elec_med_y20', models.IntegerField(default='100')),
                ('price_elec_med_y21', models.IntegerField(default='100')),
                ('price_elec_med_y22', models.IntegerField(default='100')),
                ('price_elec_med_y23', models.IntegerField(default='100')),
                ('price_elec_med_y24', models.IntegerField(default='100')),
                ('price_elec_med_y25', models.IntegerField(default='100')),
                ('price_elec_med_y26', models.IntegerField(default='100')),
                ('price_elec_med_y27', models.IntegerField(default='100')),
                ('price_elec_med_y28', models.IntegerField(default='100')),
                ('price_elec_med_y29', models.IntegerField(default='100')),
                ('price_elec_med_y30', models.IntegerField(default='100')),
                ('price_elec_med_y31', models.IntegerField(default='100')),
                ('price_elec_med_y32', models.IntegerField(default='100')),
                ('price_elec_med_y33', models.IntegerField(default='100')),
                ('price_elec_med_y34', models.IntegerField(default='100')),
                ('price_elec_med_y35', models.IntegerField(default='100')),
                ('price_elec_med_y36', models.IntegerField(default='100')),
                ('price_elec_med_y37', models.IntegerField(default='100')),
                ('price_elec_med_y38', models.IntegerField(default='100')),
                ('price_elec_med_y39', models.IntegerField(default='100')),
                ('price_elec_med_y40', models.IntegerField(default='100')),
                ('price_elec_med_y41', models.IntegerField(default='100')),
                ('price_elec_med_y42', models.IntegerField(default='100')),
                ('price_elec_high_y1', models.IntegerField(default='150')),
                ('price_elec_high_y2', models.IntegerField(default='150')),
                ('price_elec_high_y3', models.IntegerField(default='150')),
                ('price_elec_high_y4', models.IntegerField(default='150')),
                ('price_elec_high_y5', models.IntegerField(default='150')),
                ('price_elec_high_y6', models.IntegerField(default='150')),
                ('price_elec_high_y7', models.IntegerField(default='150')),
                ('price_elec_high_y8', models.IntegerField(default='150')),
                ('price_elec_high_y9', models.IntegerField(default='150')),
                ('price_elec_high_y10', models.IntegerField(default='150')),
                ('price_elec_high_y11', models.IntegerField(default='150')),
                ('price_elec_high_y12', models.IntegerField(default='150')),
                ('price_elec_high_y13', models.IntegerField(default='150')),
                ('price_elec_high_y14', models.IntegerField(default='150')),
                ('price_elec_high_y15', models.IntegerField(default='150')),
                ('price_elec_high_y16', models.IntegerField(default='150')),
                ('price_elec_high_y17', models.IntegerField(default='150')),
                ('price_elec_high_y18', models.IntegerField(default='150')),
                ('price_elec_high_y19', models.IntegerField(default='150')),
                ('price_elec_high_y20', models.IntegerField(default='150')),
                ('price_elec_high_y21', models.IntegerField(default='150')),
                ('price_elec_high_y22', models.IntegerField(default='150')),
                ('price_elec_high_y23', models.IntegerField(default='150')),
                ('price_elec_high_y24', models.IntegerField(default='150')),
                ('price_elec_high_y25', models.IntegerField(default='150')),
                ('price_elec_high_y26', models.IntegerField(default='150')),
                ('price_elec_high_y27', models.IntegerField(default='150')),
                ('price_elec_high_y28', models.IntegerField(default='150')),
                ('price_elec_high_y29', models.IntegerField(default='150')),
                ('price_elec_high_y30', models.IntegerField(default='150')),
                ('price_elec_high_y31', models.IntegerField(default='150')),
                ('price_elec_high_y32', models.IntegerField(default='150')),
                ('price_elec_high_y33', models.IntegerField(default='150')),
                ('price_elec_high_y34', models.IntegerField(default='150')),
                ('price_elec_high_y35', models.IntegerField(default='150')),
                ('price_elec_high_y36', models.IntegerField(default='150')),
                ('price_elec_high_y37', models.IntegerField(default='150')),
                ('price_elec_high_y38', models.IntegerField(default='150')),
                ('price_elec_high_y39', models.IntegerField(default='150')),
                ('price_elec_high_y40', models.IntegerField(default='150')),
                ('price_elec_high_y41', models.IntegerField(default='150')),
                ('price_elec_high_y42', models.IntegerField(default='150')),
                ('opex', models.IntegerField(default='50')),
                ('opex_indexation_start_date', models.DateField(blank=True, default=datetime.date(2024, 1, 1), null=True)),
                ('index_rate_opex', models.DecimalField(decimal_places=2, default=2, max_digits=4)),
                ('debt_margin', models.DecimalField(decimal_places=2, default=5, max_digits=4)),
                ('debt_swap_rate', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('debt_swap_margin', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('debt_reference_rate_buffer', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('debt_upfront_fee', models.DecimalField(decimal_places=2, default=1.5, max_digits=4)),
                ('debt_commitment_fee', models.DecimalField(decimal_places=2, default=1, max_digits=4)),
                ('debt_target_DSCR', models.DecimalField(decimal_places=2, default=1.15, max_digits=4)),
                ('debt_gearing_max', models.DecimalField(decimal_places=2, default=90, max_digits=4)),
                ('debt_negative_tail', models.IntegerField(default='0')),
                ('debt_tenor', models.IntegerField(default='20')),
                ('corporate_income_tax', models.DecimalField(decimal_places=2, default=30, max_digits=4)),
                ('devfee_choice', models.IntegerField(default='2')),
                ('devfee_paid_FC', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('devfee_paid_COD', models.DecimalField(decimal_places=2, default=1, max_digits=4)),
                ('injection_choice', models.IntegerField(default='1')),
                ('subgearing', models.DecimalField(decimal_places=2, default=90, max_digits=4)),
                ('SHL_margin', models.DecimalField(decimal_places=2, default=3, max_digits=4)),
                ('calculation_detail', models.IntegerField(default='2')),
                ('payment_delay_revenues', models.IntegerField(default='30')),
                ('payment_delay_costs', models.IntegerField(default='30')),
                ('DSRA_choice', models.IntegerField(default='1')),
                ('initial_wc', models.IntegerField(default='0')),
                ('cash_min', models.IntegerField(default='0')),
                ('sensi_production', models.DecimalField(decimal_places=0, default=0, max_digits=3)),
                ('sensi_opex', models.DecimalField(decimal_places=0, default=10, max_digits=3)),
                ('sensi_inflation', models.DecimalField(decimal_places=0, default=1, max_digits=3)),
                ('sponsor_production_choice', models.IntegerField(default='3')),
                ('sponsor_price_elec_choice', models.IntegerField(default='2')),
                ('wind_turbine_installed', models.IntegerField(blank=True, default='3', null=True)),
                ('capacity_per_turbine', models.IntegerField(blank=True, default='2', null=True)),
                ('timeline_quarters_ceiling', models.BooleanField(default=False, null=True)),
                ('panels_surface', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('dev_tax_taxable_base_solar', models.DecimalField(decimal_places=2, default=10, max_digits=6)),
                ('dev_tax_taxable_base_wind', models.DecimalField(decimal_places=2, default=3000, max_digits=6)),
                ('dev_tax_commune_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('dev_tax_department_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('archeological_tax_base_solar', models.DecimalField(decimal_places=2, default=10, max_digits=8)),
                ('archeological_tax', models.DecimalField(decimal_places=2, default=0.4, max_digits=4)),
                ('lease', models.IntegerField(default='50')),
                ('lease_indexation_start_date', models.DateField(blank=True, default=datetime.date(2024, 1, 1), null=True)),
                ('index_rate_lease', models.DecimalField(decimal_places=2, default=2, max_digits=4)),
                ('tfpb_commune_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('tfpb_department_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('tfpb_additional_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('tfpb_region_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('cfe_discount_tax_base_y1', models.DecimalField(decimal_places=2, default=50, max_digits=4)),
                ('cfe_discount_tax_base', models.DecimalField(decimal_places=2, default=30, max_digits=4)),
                ('cfe_mgt_fee', models.DecimalField(decimal_places=2, default=3, max_digits=4)),
                ('cfe_instal_q1', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('cfe_instal_q2', models.DecimalField(decimal_places=2, default=50, max_digits=4)),
                ('cfe_instal_q3', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('cfe_instal_q4', models.DecimalField(decimal_places=2, default=50, max_digits=4)),
                ('cfe_commune_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('cfe_intercommunal_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('cfe_specific_eqp_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('cfe_localCCI_tax', models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ('project_status', models.CharField(choices=[('Development', 'Development'), ('Operational', 'Operational')], default='Development', max_length=100)),
                ('discount_factor_valuation', models.DecimalField(decimal_places=2, default=7, max_digits=4)),
                ('contract', models.CharField(choices=[('FiT', 'FiT'), ('CfD - E16', 'CfD - E16'), ('CfD - E17', 'CfD - E17'), ('CfD - AO', 'CfD - AO'), ('Corporate PPA', 'Corporate PPA')], default='CfD - AO', max_length=100)),
                ('rotor_diameter', models.DecimalField(decimal_places=2, default=92, max_digits=4)),
            ],
        ),
        migrations.CreateModel(
            name='SolarFinancialModel',
            fields=[
                ('financialmodel_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='financial_model.financialmodel')),
            ],
            bases=('financial_model.financialmodel',),
        ),
        migrations.CreateModel(
            name='WindFinancialModel',
            fields=[
                ('financialmodel_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='financial_model.financialmodel')),
            ],
            bases=('financial_model.financialmodel',),
        ),
        migrations.AddField(
            model_name='financialmodel',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='financial_model.project'),
        ),
    ]
