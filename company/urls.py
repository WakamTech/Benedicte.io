# company/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('onboarding/profile/', views.company_profile_step, name='company_profile_step'),
    path('onboarding/financials/', views.company_financials_step, name='company_financials_step'),
    path('onboarding/charges/', views.company_charges_step, name='company_charges_step'),
    path('onboarding/products/', views.company_products_step, name='company_products_step'),
]