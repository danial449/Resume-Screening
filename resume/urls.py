from django.urls import path
from .views import JobDescriptionUploadView, JDResultUpdateView, ResumeScreeningAPIView, check_ai_resume, ChangeHistoryLog

urlpatterns = [
    path("upload-jd/", JobDescriptionUploadView.as_view(), name="upload-jd"),
    path("update-jd-results/<int:jd_id>/", JDResultUpdateView.as_view(), name="update-jd-results"),
    path("upload-resume/<int:jd_id>/", ResumeScreeningAPIView.as_view(), name="upload-Resume"),
    path("check-ai-resume/", check_ai_resume, name="check-ai-text"),
    path("change-history/", ChangeHistoryLog, name="change-history"),
]
