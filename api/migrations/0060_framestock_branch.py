# Generated by Django 4.2.16 on 2025-03-19 15:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0059_alter_customuser_user_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='framestock',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='frame_stocks', to='api.branch'),
        ),
    ]
