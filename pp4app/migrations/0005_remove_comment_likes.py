# Generated by Django 3.2.23 on 2023-12-13 00:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pp4app', '0004_remove_comment_recipe'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comment',
            name='likes',
        ),
    ]