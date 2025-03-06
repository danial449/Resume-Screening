from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import JobDescription, JDResult, Resume, ResumeDetails
from .serializers import JobDescriptionSerializer, JDResultSerializer, ResumeSerializer, ResumeDetailsSerializer
from .utils import extract_text_from_pdf, extract_text_from_doc, assign_weightage_to_skills, extract_name_from_text, extract_text_from_xlsx, process_with_hr_ai, is_generated_by_ai
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny



class JobDescriptionUploadView(APIView):
    def get(self, request):
        jds = JobDescription.objects.values("id", "filename")  
        return Response(list(jds), status=status.HTTP_200_OK)
    
    def post(self, request):
        file = request.FILES.get("file")
        compensation = request.data.get("compensation")
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        filename = file.name
        if filename.endswith(".pdf"):
            summary = extract_text_from_pdf(file)
        elif filename.endswith(".docx"):
            summary = extract_text_from_doc(file)
        else:
            return Response({"error": "Unsupported file format"}, status=status.HTTP_400_BAD_REQUEST)

        jd, created = JobDescription.objects.get_or_create(filename=filename, defaults={"summary": summary, "compensation": compensation, "file": file})
        serializer = JobDescriptionSerializer(jd)
        if not created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        skills_data = assign_weightage_to_skills(summary)
        for skill in skills_data:
            JDResult.objects.create(jd=jd, **skill)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class JDResultUpdateView(APIView):
    def put(self, request, jd_id):
        jd = get_object_or_404(JobDescription, id=jd_id)
        results = request.data.get("results", [])

        for result in results:
            jd_result, created = JDResult.objects.update_or_create(
                jd=jd, skill=result["skill"], 
                defaults={
                    "score": result.get("score"),
                    "hr_comment": result.get("hr_comment"),
                    "rationale": result.get("rationale"),
                }
            )
        serializer = JobDescriptionSerializer(jd)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ResumeScreeningAPIView(APIView):
    def post(self, request, jd_id):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        resumes = extract_text_from_xlsx(file)  

        jd = get_object_or_404(JobDescription, id=jd_id)
        jd_results = list(JDResult.objects.filter(jd=jd).values("skill", "score", "hr_comment", "rationale"))
        jd_compensation = jd.compensation

        results = []

        for resume_data in resumes:
            resume_name = resume_data["resume_name"]
            resume_text = resume_data["resume_text"]
            candidate_url = resume_data.get("workday_url", "No link available")
            resume_compensation = resume_data.get("compensation")
            candidate_name = resume_data.get("candidate_name")

            # candidate_name = extract_name_from_text(resume_text)

            resume_obj, _ = Resume.objects.get_or_create(filename=resume_name, defaults={"summary": resume_text})
            existing_result = ResumeDetails.objects.filter(resume=resume_obj, jd=jd).first()

            if existing_result:
               serializer = ResumeDetailsSerializer(existing_result)
            else:
            
                processed_data = process_with_hr_ai(resume_text, jd_results)
                score = processed_data.get("score", 0)
                score_reason = processed_data.get("reason", None)
                print(f"{candidate_name} - {score}")

                if resume_compensation is not None:
                    if resume_compensation > jd_compensation:
                        compensation = True
                        compensation_reason = f"Asking more pay then the budget"
                    else:
                        compensation = False
                        compensation_reason = f"Asking within the budget"
                else:
                    compensation = False
                    compensation_reason = "Candidate's compensation data is not available."

                resume_detail_obj = ResumeDetails.objects.create(
                    resume=resume_obj,
                    jd=jd,
                    candidate_name=candidate_name,
                    score=score,
                    score_reason=score_reason,
                    candidate_application=candidate_url,
                    flagged=compensation,
                    flag_type="Compensation",
                    flag_reason=compensation_reason
                )
                serializer = ResumeDetailsSerializer(resume_detail_obj)

            results.append(serializer.data)

        return Response(results, status=status.HTTP_200_OK)
    
    def put(self, request, jd_id):
        jd = get_object_or_404(JobDescription, id=jd_id)
        updates = request.data.get("updates", []) 

        if not updates:
            return Response({"error": "No updates provided"}, status=status.HTTP_400_BAD_REQUEST)

        updated_results = []

        for update in updates:
            resume_id = update.get("id")
            if not resume_id:
                continue  
            
            resume_detail = get_object_or_404(ResumeDetails, id=resume_id, jd=jd)

            resume_detail.score = update.get("score", resume_detail.score)
            resume_detail.score_reason = update.get("score_reason", resume_detail.score_reason)
            resume_detail.flagged = update.get("flagged", resume_detail.flagged)
            resume_detail.flag_type = update.get("flag_type", resume_detail.flag_type)
            resume_detail.flag_reason = update.get("flag_reason", resume_detail.flag_reason)
            resume_detail.candidate_application = update.get("candidate_application", resume_detail.candidate_application)

            resume_detail.save()
            serializer = ResumeDetailsSerializer(resume_detail)
            updated_results.append(serializer.data)

        return Response(updated_results, status=status.HTTP_200_OK)



@api_view(["GET"])
@permission_classes([AllowAny])
def check_ai_resume(request):
    resumes = Resume.objects.all()
    results = []
    for resume in resumes:
        filename = resume.filename
        resume_text = resume.summary
        if not resume_text:
            return Response({"error": "Resume text is required"}, status=400)
        ai_generated, confidence = is_generated_by_ai(resume_text)
        result = {
            "filename" : filename,
            "ai_generated": f"Ai-Generated" if ai_generated else "Human-Written",
            "confidence" : float(f"{confidence:.1f}")
        }
        results.append(result)
    return Response(results , status=status.HTTP_200_OK)

