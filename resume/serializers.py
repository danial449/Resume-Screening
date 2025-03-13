from rest_framework import serializers
from .models import JobDescription, JDResult, Resume, ResumeDetails

class JDResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = JDResult
        fields = ["skill", "score", "hr_comment", "rationale"]

class JobDescriptionSerializer(serializers.ModelSerializer):
    skills = JDResultSerializer(many=True, read_only=True)

    class Meta:
        model = JobDescription
        fields = ["id", "filename", "summary", "file", "compensation", "skills"]

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ["id", "filename"]
class ResumeDetailsSerializer(serializers.ModelSerializer):
    filename = serializers.CharField(source="resume.filename")
    jd_filename = serializers.CharField(source="jd.filename")  

    class Meta:
        model = ResumeDetails
        fields = ["id", "filename", "jd_filename", "candidate_name", "score", "score_reason", "candidate_application", "linkedin_url", "flagged", "flag_type", "flag_reason"]
