# content/views.py
from django.shortcuts import render

def faq_view(request):
    # Plus tard, vous pourrez passer des données dynamiques si besoin
    context = {}
    return render(request, 'content/faq.html', context)