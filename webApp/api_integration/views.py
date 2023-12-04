from django.shortcuts import render

import requests
from django.http import JsonResponse

def get_data(request,city_name):
	url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/delta_deliberation_tam_17_01_23/records"
	params = {
		'select': 'taux',
		'where': f'"{city_name}"',
		'limit': 1
	}

	try:
		response = requests.get(url, params=params)
		response.raise_for_status()  # Raise an exception for any HTTP error
		data = response.json()
		
		# Process the data as needed
		# ...

		# Return a JsonResponse with the data you want to send as the API response
		return JsonResponse({'data': data})

	except requests.exceptions.RequestException as e:
		# Handle the error or return an error JsonResponse
		return JsonResponse({'error': str(e)}, status=500)