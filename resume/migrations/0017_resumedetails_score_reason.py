# Generated by Django 5.1.6 on 2025-03-04 11:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("resume", "0016_alter_resumedetails_jd"),
    ]

    operations = [
        migrations.AddField(
            model_name="resumedetails",
            name="score_reason",
            field=models.TextField(blank=True, null=True),
        ),
    ]
