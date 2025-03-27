# Generated by Django 4.2.16 on 2025-03-26 02:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0064_patient_patient_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='externallens',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='external_lenses', to='api.branch'),
        ),
    ]
