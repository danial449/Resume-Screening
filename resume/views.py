from rest_framework import status
from rest_framework.response import Response
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import JobDescription, JDResult, Resume, ResumeDetails
from .serializers import JobDescriptionSerializer, JDResultSerializer, ResumeSerializer, ResumeDetailsSerializer
from .utils import extract_text_from_pdf, extract_text_from_doc, assign_weightage_to_skills, extract_name_from_text, extract_text_from_xlsx, process_with_hr_ai, is_generated_by_ai
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import re
import subprocess
import time
import logging
from django.conf import settings

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
                print(linkedin_url)

                # candidate_name = extract_name_from_text(resume_text)

                resume_obj, _ = Resume.objects.get_or_create(filename=resume_name, defaults={"summary": resume_text})
                existing_result = ResumeDetails.objects.filter(resume=resume_obj, jd=jd).first()

                if existing_result:
                   serializer = ResumeDetailsSerializer(existing_result)
                   return serializer.data if serializer.data else {"error": "Existing data is empty"}
                else:
                    # if linkedin_url != "No LinkedIn profile found":
                    #     process = subprocess.Popen(
                    #         ['scrapy', 'crawl', 'linkedin', '-a', f'url={linkedin_url}', '-o', 'output.json'],
                    #         cwd=r'C:\Users\Mega Computer\Desktop\Resume-Screening\backend\linkedin_scraper',
                    #         stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    #     )
                    #     stdout, stderr = process.communicate()
                    #     print(f"Scrapy stdout: {stdout.decode()}")
                    #     print(f"Scrapy stderr: {stderr.decode()}")
                    #     if process.returncode == 0:
                    #         with open(r'C:\Users\Mega Computer\Desktop\Resume-Screening\backend\linkedin_scraper\output.json') as f:
                    #             linkedin_data = json.load(f)
                    #             experience = linkedin_data[0]['experience'] if linkedin_data else []
                    #             f"Srap : {experience}"

                    #     else:
                    #          print("Scrapy failed to scrape data.")
                    # else:
                    #     experience = []
                    #     print(f"Empty : {experience}")

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
                        flagged=compensation,
                        flag_type="Compensation",
                        flag_reason=compensation_reason
                    )
                    serializer = ResumeDetailsSerializer(resume_detail_obj)
                    # result = {
                    #     "candidate_name":candidate_name,
                    #     "score":score,
                    #     "score_reason":score_reason,
                    #     "candidate_application":candidate_url,
                    #     "flagged":compensation,
                    #     "flag_type":"Compensation",
                    #     "flag_reason":compensation_reason
                    # }


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

class LinkedInProfileScraper(APIView):
    def get(self, request):
        # Retrieve the LinkedIn profile URL from query parameters
        profile_url = request.query_params.get('url')
        if not profile_url:
            return Response({"error": "Profile URL is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Set up the Chrome driver
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = webdriver.Chrome(options=options)

        try:
            # Login to LinkedIn
            login_url = "https://www.linkedin.com/login"
            driver.get(login_url)
            time.sleep(3)

            email_input = driver.find_element(By.ID, "username")
            email_input.send_keys(settings.LINKEDIN_USERNAME)
            password_input = driver.find_element(By.ID, "password")
            password_input.send_keys(settings.LINKEDIN_PASSWORD)
            password_input.send_keys(Keys.RETURN)
            time.sleep(5)

            # Visit the profile URL
            driver.get(profile_url)
            time.sleep(5)

            # Extract data from the profile
            name = driver.find_element(By.XPATH, '/html/body/div[6]/div[3]/div/div/div[2]/div/div/main/section[1]/div[2]/div[2]/div[1]/div[1]/span/a/h1').text.strip()
            heading = driver.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[1]/div[2]/div[2]/div[1]/div[2]').text.strip()
            location = driver.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[1]/div[2]/div[2]/div[2]/span[1]').text.strip()
            experiences = driver.find_elements(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[3]/div[3]/ul')

            extracted_experience = []
            for exp in experiences:
                try:
                    title = exp.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[3]/div[3]/ul/li[1]/div/div[2]/div[1]/div/div/div/div/div/span[1]').text.strip()
                    company = exp.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[3]/div[3]/ul/li[1]/div/div[2]/div[1]/div/span[1]/span[1]').text.strip()
                    total_experience = exp.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[3]/div[3]/ul/li[1]/div/div[2]/div[1]/div/span[2]/span[1]').text.strip()
                    extracted_experience.append({"title": title, "total_experience": total_experience, "company": company})
                except Exception as e:
                    print(f"Error extracting experience: {e}")

            # Prepare response data
            response_data = {
                "name": name,
                "heading": heading,
                "location": location,
                "experience": extracted_experience
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        finally:
            driver.quit()