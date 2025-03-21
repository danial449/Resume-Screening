# Generated by Django 5.1.6 on 2025-02-28 11:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("resume", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Resume",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("filename", models.CharField(max_length=255, unique=True)),
                ("summary", models.TextField()),
            ],
        ),
        migrations.RenameField(
            model_name="jdresult",
            old_name="weightage",
            new_name="score",
        ),
        migrations.RenameField(
            model_name="jobdescription",
            old_name="content",
            new_name="summary",
        ),
        migrations.CreateModel(
            name="ResumeDetails",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("candidate_name", models.CharField(max_length=255)),
                ("score", models.IntegerField()),
                ("candidate_application", models.URLField(max_length=255)),
                ("flag_type", models.CharField(max_length=255)),
                ("flag_reason", models.TextField()),
                (
                    "resume",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resume",
                        to="resume.resume",
                    ),
                ),
            ],
        ),
    ]
