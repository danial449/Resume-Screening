# Generated by Django 5.1.6 on 2025-03-14 10:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("resume", "0020_rename_flagged_resumedetails_compensation_flag_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="resumedetails",
            name="linkedin_url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
