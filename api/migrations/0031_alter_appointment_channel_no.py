# Generated by Django 4.2.16 on 2025-01-06 16:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0030_appointment_channel_no'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='channel_no',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]