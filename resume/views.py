from rest_framework import status
from rest_framework.response import Response
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import JobDescription, JDResult, Resume, ResumeDetails, JDResultChangeLog
from .serializers import JobDescriptionSerializer, JDResultSerializer, ResumeSerializer, ResumeDetailsSerializer, JDResultChangeLogSerializer
from .utils import extract_text_from_pdf, extract_text_from_doc, assign_weightage_to_skills, extract_name_from_text, extract_text_from_xlsx, process_with_hr_ai, is_generated_by_ai
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import re
import logging


logger = logging.getLogger(__name__)

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
        
        if JDResult.objects.filter(jd=jd).exists():
            serializer = JobDescriptionSerializer(jd)
            return Response(serializer.data, status=status.HTTP_200_OK)


        skills_data = assign_weightage_to_skills(summary)
        for skill in skills_data:
            JDResult.objects.create(jd=jd, **skill)
        serializer = JobDescriptionSerializer(jd)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# class JDResultUpdateView(APIView):
#     def put(self, request, jd_id):
#         jd = get_object_or_404(JobDescription, id=jd_id)
#         skills = request.data.get("skills", [])
#         print(skills)
#         changed_by = "API User"  

#         jd_results = JDResult.objects.filter(jd=jd)
#         if not jd_results.exists():
#             return Response({"error": "No JD results found for this Job Description"}, status=status.HTTP_400_BAD_REQUEST)

#         for result in skills:
#             jd_result, created = JDResult.objects.get_or_create(
#                 jd=jd, skill=result["id"]
#             )
#             print(jd_result)
#             if not created:
#                 changes = {}
#                 if "score" in result and jd_result.score != result["score"]:
#                     changes["score"] = {
#                         "previous": jd_result.score,
#                         "updated": result["score"],
#                     }
#                 if "hr_comment" in result and jd_result.hr_comment != result["hr_comment"]:
#                     changes["hr_comment"] = {
#                         "previous": jd_result.hr_comment,
#                         "updated": result["hr_comment"],
#                     }
#                 if "rationale" in result and jd_result.rationale != result["rationale"]:
#                     changes["rationale"] = {
#                         "previous": jd_result.rationale,
#                         "updated": result["rationale"],
#                     }

#                 if changes:
#                     JDResultChangeLog.objects.create(
#                         jd_result=jd_result,
#                         changed_by=changed_by,
#                         changes=changes, 
#                     )

#             # Update the JDResult instance
#             if "score" in result:
#                 jd_result.score = result["score"]
#             if "hr_comment" in result:
#                 jd_result.hr_comment = result["hr_comment"]
#             if "rationale" in result:
#                 jd_result.rationale = result["rationale"]
#             jd_result.save()

#         serializer = JobDescriptionSerializer(jd)
#         return Response(serializer.data, status=status.HTTP_200_OK)
    
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

        def process_resume(resume_data):
            try:
                resume_name = resume_data["resume_name"]
                resume_text = resume_data["resume_text"]
                candidate_url = resume_data.get("workday_url", "No link available")
                resume_compensation = resume_data.get("compensation")
                candidate_name = resume_data.get("candidate_name")
                linkedin_pattern = r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-_%]+"
                match = re.search(linkedin_pattern, resume_text)
                linkedin_url = match.group(0) if match else "No LinkedIn profile found"

                # candidate_name = extract_name_from_text(resume_text)

                resume_obj, _ = Resume.objects.get_or_create(filename=resume_name, defaults={"summary": resume_text})
                existing_result = ResumeDetails.objects.filter(resume=resume_obj, jd=jd).first()

                if existing_result:
                   serializer = ResumeDetailsSerializer(existing_result)
                   return serializer.data if serializer.data else {"error": "Existing data is empty"}
                else:

                    processed_data = process_with_hr_ai(resume_text, jd_results)
                    score = processed_data.get("score", 0)
                    score_reason = processed_data.get("reason", None)

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
                        linkedin_flag=True if linkedin_url != "No LinkedIn profile found" else False,
                        linkedin_url=linkedin_url if linkedin_url else "No LinkedIn Profile",
                        compensation_flag=compensation,
                        flag_type="Compensation",
                        flag_reason=compensation_reason
                    )
                    serializer = ResumeDetailsSerializer(resume_detail_obj)
                    if not isinstance(serializer.data, (dict, list)):
                        raise TypeError(f"Serializer data is not JSON-serializable: {serializer.data}")

                    return serializer.data
            except Exception as e:
                logger.error(f"Error processing resume: {e}")
                return {"error": str(e)}
            
        with ThreadPoolExecutor() as executor:
            future_to_resume = {executor.submit(process_resume, resume_data): resume_data for resume_data in resumes}
            for future in as_completed(future_to_resume):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"An error occurred: {e}")
                    results.append({"error": str(e)})

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


class JDResultUpdateView(APIView):
    def put(self, request, jd_id):
        jd = get_object_or_404(JobDescription, id=jd_id)
        results = request.data.get("skills", [])

        for result in results:
            jd_result, created = JDResult.objects.get_or_create(
                jd=jd, skill=result["skill"]
            )
            if not created:
                # Log changes before updating
                JDResultChangeLog.objects.create(
                    jd_result=jd_result,
                    previous_score=jd_result.score,
                    updated_score=result.get("score"),
                    previous_hr_comment=jd_result.hr_comment,
                    updated_hr_comment=result.get("hr_comment"),
                    previous_rationale=jd_result.rationale,
                    updated_rationale=result.get("rationale"),
                )
            # Update the JDResult instance
            jd_result.score = result.get("score", jd_result.score)
            jd_result.hr_comment = result.get("hr_comment", jd_result.hr_comment)
            jd_result.rationale = result.get("rationale", jd_result.rationale)
            jd_result.save()

        serializer = JobDescriptionSerializer(jd)
        return Response(serializer.data, status=status.HTTP_200_OK)
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
            "ai_generated": ai_generated,
            "confidence" : float(f"{confidence:.1f}")
        }
        results.append(result)
    return Response(results , status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([AllowAny])
def ChangeHistoryLog(request):
    historylog = JDResultChangeLog.objects.all()
    print(historylog)
    serializer = JDResultChangeLogSerializer(historylog, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)