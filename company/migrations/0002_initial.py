# Generated by Django 5.2 on 2025-04-14 07:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('company', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='companyprofile',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='company_profile', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='charge',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='charges', to='company.companyprofile'),
        ),
        migrations.AddField(
            model_name='financialdata',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='financial_data', to='company.companyprofile'),
        ),
        migrations.AddField(
            model_name='productservice',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products_services', to='company.companyprofile'),
        ),
        migrations.AlterUniqueTogether(
            name='financialdata',
            unique_together={('company', 'year')},
        ),
    ]
