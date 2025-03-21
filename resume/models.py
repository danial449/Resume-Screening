from django.db import models
import uuid

class JobDescription(models.Model):
    filename = models.CharField(max_length=255, unique=True)
    summary = models.TextField()
    file = models.FileField(upload_to="job_descriptions/", null=True, blank=True)
    compensation = models.IntegerField(null=True, blank=True)

class JDResult(models.Model):
    jd = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name="skills")
    skill = models.CharField(max_length=255)
    score = models.IntegerField() 
    hr_comment = models.TextField(blank=True, null=True)
    rationale = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)

class Resume(models.Model):
    filename=models.CharField(max_length=255, unique=True)
    summary = models.TextField()

class ResumeDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="resume")
    jd = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name="jd_resumes") 
    candidate_name = models.CharField(max_length=255)
    score = models.IntegerField()
    score_reason = models.TextField(null=True, blank=True)
    candidate_application = models.URLField(max_length=255, null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    linkedin_flag = models.BooleanField(null=True, blank=True)
    compensation_flag = models.BooleanField(null=True, blank=True)
    flag_type = models.CharField(max_length=255)
    flag_reason = models.TextField()

    class Meta:
        unique_together = ('resume', 'jd')

class JDResultChangeLog(models.Model):
    jd_result = models.ForeignKey(JDResult, on_delete=models.CASCADE, related_name="change_logs")
    previous_score = models.IntegerField(null=True, blank=True)
    updated_score = models.IntegerField(null=True, blank=True)
    previous_hr_comment = models.TextField(null=True, blank=True)
    updated_hr_comment = models.TextField(null=True, blank=True)
    previous_rationale = models.TextField(null=True, blank=True)
    updated_rationale = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Change log for {self.jd_result.skill} at {self.timestamp}"