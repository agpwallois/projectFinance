from django.shortcuts import render
from django.views.generic import View


class HomePageView(View):
	template_home = 'home_page/home.html'

	def get(self, request):
		return render(request, self.template_home)
	
	def post(self, request):
		return render(request, self.template_home)
