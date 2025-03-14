from rest_framework import serializers
from .models import JobDescription, JDResult, Resume, ResumeDetails, JDResultChangeLog

class JDResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = JDResult
        fields = ["id", "skill", "score", "hr_comment", "rationale", "category"]

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
        fields = ["id", "filename", "jd_filename", "candidate_name", "score", "score_reason", "candidate_application", "linkedin_url", "linkedin_flag","compensation_flag", "flag_type", "flag_reason"]

class JDResultChangeLogSerializer(serializers.ModelSerializer):
    jd_result = serializers.StringRelatedField()  # Displays related JDResult object meaningfully
    previous_score = serializers.IntegerField(required=False, min_value=0, max_value=100)
    updated_score = serializers.IntegerField(required=False, min_value=0, max_value=100)
    previous_hr_comment = serializers.CharField(required=False, allow_blank=True)
    updated_hr_comment = serializers.CharField(required=False, allow_blank=True)
    previous_rationale = serializers.CharField(required=False, allow_blank=True)
    updated_rationale = serializers.CharField(required=False, allow_blank=True)
    timestamp = serializers.DateTimeField(read_only=True)

    class Meta:
        model = JDResultChangeLog
        fields = [
            "id",
            "jd_result",
            "previous_score",
            "updated_score",
            "previous_hr_comment",
            "updated_hr_comment",
            "previous_rationale",
            "updated_rationale",
            "timestamp",
        ]
