# Generated by Django 4.2.16 on 2025-07-13 09:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_orderpayment_is_edited'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='is_refund',
            field=models.BooleanField(default=False),
        ),
    ]
