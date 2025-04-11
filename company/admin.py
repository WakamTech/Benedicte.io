# company/admin.py
from django.contrib import admin
from .models import CompanyProfile, FinancialData, Charge, ProductService

# Simple registration for now
admin.site.register(CompanyProfile)
admin.site.register(FinancialData)
admin.site.register(Charge)
admin.site.register(ProductService)