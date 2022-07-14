from django import forms
from .models import SProject
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, HTML

class SProjectForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = ['name','genre','country']

class ConstructionForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = [
	 'start_construction',
	 'end_construction',
	 'costs_at_NTP',
	 'costs_at_FC',
	 'costs_month_1',
	 'costs_month_2',
	 'costs_month_3',
	 'costs_month_4',
	 'costs_month_5',
	 'costs_month_6',
	 'costs_month_7',
	 'costs_month_8',
	 'costs_month_9',
	 'costs_month_10',
	 'costs_month_11',
	 'costs_month_12',
	 ]
	 widgets = {
            'start_construction': forms.DateInput(
        	format=('%Y-%m-%d'),
        	attrs={'class': 'form-control', 
               'placeholder': 'Select a date',
               'type': 'date'
              }),
            'end_construction': forms.DateInput(
        	format=('%Y-%m-%d'),
        	attrs={'class': 'form-control', 
               'placeholder': 'Select a date',
               'type': 'date'
              }),
        }

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.helper = FormHelper()
		self.helper.layout = Layout(
			HTML('<h3>Construction schedule</h3>'),
            Row(
                Column('start_construction', css_class='form-group col-md-6 mb-0'),
                Column('end_construction', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('costs_at_NTP', css_class='form-group col-md-6 mb-0'),
                Column('costs_at_FC', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            HTML('<h3>Monthly costs</h3>'),
            'costs_month_1',
            'costs_month_2',
            'costs_month_3',
    		'costs_month_4',
            'costs_month_5',
            'costs_month_6',
            'costs_month_7',
            'costs_month_8',
            'costs_month_9',
            'costs_month_10',
            'costs_month_11',
            'costs_month_12',
        )
	 
class TimelineForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = ['start_year','length','periodicity']

class RevenuesForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = ['revenues','inflation']

class OpexForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = ['opex']