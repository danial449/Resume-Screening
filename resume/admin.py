from django.contrib import admin
from .models import JobDescription, JDResult, Resume, ResumeDetails

class JDResultInline(admin.TabularInline): 
    model = JDResult

@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ("id","filename")  
    search_fields = ("filename", "summary")  
    inlines = [JDResultInline]  

@admin.register(JDResult)
class JDResultAdmin(admin.ModelAdmin):
    list_display = ("get_jd_filename", "skill", "score")  
    search_fields = ("skill",)
    list_filter = ("score",)

    def get_jd_filename(self, obj):
        return obj.jd.filename  

    get_jd_filename.short_description = "Job Description"  


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("id", "filename", "summary")
    search_fields = ("filename", "summary")

@admin.register(ResumeDetails)
class ResumeDetailsAdmin(admin.ModelAdmin):
    list_display = ("id", "get_resume_filename", "get_jd_filename", "candidate_name", "score", "candidate_application", "flagged")
    list_filter = ("flagged", "score")
    search_fields = ("candidate_name", "flag_reason")

    def get_resume_filename(self, obj):
        return obj.resume.filename  

    def get_jd_filename(self, obj):
        return obj.jd.filename  

    get_resume_filename.short_description = "Resume"
    get_jd_filename.short_description = "Job Description"
