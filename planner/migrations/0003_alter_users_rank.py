# Generated by Django 5.1.7 on 2025-03-31 08:21

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0002_alter_users_rank'),
    ]

    operations = [
        migrations.AlterField(
            model_name='users',
            name='rank',
            field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
