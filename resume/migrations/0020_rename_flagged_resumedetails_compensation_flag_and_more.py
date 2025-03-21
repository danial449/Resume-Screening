# Generated by Django 5.1.6 on 2025-03-14 10:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("resume", "0019_alter_resumedetails_linkedin_url"),
    ]

    operations = [
        migrations.RenameField(
            model_name="resumedetails",
            old_name="flagged",
            new_name="compensation_flag",
        ),
        migrations.AddField(
            model_name="resumedetails",
            name="linkedin_flag",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
