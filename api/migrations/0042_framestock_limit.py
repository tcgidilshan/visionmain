# Generated by Django 4.2.16 on 2025-02-01 11:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0041_remove_power_side_alter_lenspower_side'),
    ]

    operations = [
        migrations.AddField(
            model_name='framestock',
            name='limit',
            field=models.IntegerField(default=0),
        ),
    ]
