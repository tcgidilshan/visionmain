# Generated by Django 4.2.16 on 2025-01-02 17:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0027_channelpayment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='doctor',
            name='specialization',
        ),
    ]
