# Generated by Django 3.2.23 on 2024-01-09 18:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pp4app', '0004_auto_20240102_1955'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='body',
            field=models.TextField(max_length=1000),
        ),
    ]
