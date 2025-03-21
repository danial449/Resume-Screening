import fitz  # PyMuPDF
from docx import Document
import openai
from django.conf import settings
import pandas as pd
import spacy
import re
from transformers import pipeline
import textwrap
import boto3

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

nlp = spacy.load("en_core_web_sm")
text_classifier = pipeline("text-classification", model="roberta-base-openai-detector")

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return "\n".join([page.get_text() for page in doc])

def extract_text_from_doc(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_xlsx(excel_file_path):
    df = pd.read_excel(excel_file_path)
    indices = [9, 12, 32, 15, 1]
    valid_indices = [index for index in indices if 0 <= index < len(df.columns)]
    result_list = []
    
    for row_number in range(1, 10):
        raw_compensation = df.iloc[row_number, valid_indices[3]] if pd.notna(df.iloc[row_number, valid_indices[3]]) else None  # Column 32
        compensation_match = re.search(r'\d+', str(raw_compensation))  # Extract only numbers
        summary = df.iloc[row_number, valid_indices[2]] if pd.notna(df.iloc[row_number, valid_indices[2]]) else None
        raw_candidate_name = df.iloc[row_number, valid_indices[4]] if pd.notna(df.iloc[row_number, valid_indices[4]]) else None 
 
        candidate_name = re.sub(r"\s*\(.*?\)", "", raw_candidate_name) if raw_candidate_name else None  

        row_dict = {
            "resume_name": df.iloc[row_number, valid_indices[0]] if pd.notna(df.iloc[row_number, valid_indices[0]]) else None,  # Column 9
            "workday_url": df.iloc[row_number, valid_indices[1]] if pd.notna(df.iloc[row_number, valid_indices[1]]) else None,  # Column 12
            "resume_text": summary if summary else "Summary is Empty",
            "candidate_name": candidate_name,
            "compensation": int(compensation_match.group()) if compensation_match else None   
        }
        result_list.append(row_dict)
    
    return result_list


def extract_name_from_text(text):
    lines = text.strip().split("\n")

    first_line = lines[0].strip()
    if len(first_line.split()) > 1 and "resume" not in first_line.lower():
        return first_line

    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text

    return "Not Found"

def assign_weightage_to_skills(content):
    prompt =  f"""
You are an expert Prompt Engineer and Skill Weightage Analyst. Your task is to:

1. Thoroughly review the Job Description (JD) below:
   {content}

2. Identify the *top 10 essential skills* required for the role, taking into account:
   - How frequently each skill is mentioned in the JD.
   - Its direct impact on the role’s key responsibilities.
   - Its significance to overall job performance and success.
   - Analyze the given skills and categorize them as either Mandatory or Preferred based on their relevance, necessity in the JD  

3. Assign a *unique weightage* (1–10) to each skill using the following **exact definitions**:

   - *10*  
     A “must-have” skill, cited frequently and integral to overall success. The role cannot function without it.

   - *9*  
     A highly crucial skill, strongly emphasized and vital to performance, yet slightly less all-encompassing than a 10.

   - *8*  
     An essential skill that is central to many responsibilities, though not the single most defining factor.

   - *7*  
     An important skill with clear impact on the role’s success but not always front and center.

   - *6*  
     A supportive skill that significantly contributes to efficiency and quality, though not a strict core requirement.

   - *5*  
     A moderately important skill, beneficial in multiple areas but not indispensable.

   - *4*  
     A useful skill that offers tangible value but remains secondary to higher-priority competencies.

   - *3*  
     A minor skill, rarely mentioned or situationally relevant, though still potentially helpful.

   - *2*  
     A peripheral skill that appears to have minimal direct impact on core tasks, referenced sparingly if at all.

   - *1*  
     A “nice-to-have” or bonus skill mentioned briefly or potentially implied, but not essential for day-to-day work.

4. *Justify each weight* in a concise paragraph:
   - State how often the skill appears in the JD (frequency).
   - Explain how it ties into the main duties (relevance).
   - Demonstrate whether it is indispensable, important, supportive, or supplementary (alignment).

5. Present your findings as a *numbered list* of the 10 skills with their *unique* weightages and justifications, for example:

   1. Skill Name - 10  
      Reasoning: [Highlight frequency, relevance, and why it's indispensable]
      Category: [Mandatory or Preferred]

   2. Skill Name - 9  
      Reasoning: [Highlight frequency, relevance, and why it's crucial but slightly less than 10]
      Category: [Mandatory or Preferred]

   ...

*Important Notes:*
- *No two skills* should receive the *same weight*.
- Ensure each justification is *clear, well-structured*, and directly tied to the JD.

"""

    # response = client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=[{"role": "system", "content": "Extract exactly 10 key skills and assign weightages from a job description."},
    #               {"role": "user", "content": prompt}],
    #     temperature=0
    # )

    # if not response.choices or not response.choices[0].message.content.strip():
    #     print("Warning: Empty response from API")
    #     return []

    # response_text = response.choices[0].message.content.strip()

    client = settings.SESSION.client("bedrock-runtime")

    messages = [
        {"role": "user", "content": [{"text": prompt}]},
    ]

    inference_config = {
    "temperature": 0
    }

    response = client.converse(
        modelId=settings.AWS_BEDROCK_MODEL, 
        messages=messages,
        inferenceConfig=inference_config
        )

    if not response["output"] or not response["output"]["message"]["content"][0]["text"].strip():
        print("Warning: Empty response from API")
        return []

    response_text =  response["output"]["message"]["content"][0]["text"].strip()

    weighted_skills = []
    lines = response_text.split("\n")

    skill_name, weightage, rationale, category = None, None, "", ""
    for line in lines:
        if "Skill Name - " in line:
            try:
                parts = line.split("Skill Name - ")
                skill_name = parts[1].rsplit(" - ", 1)[0].strip() 
                weightage = int(parts[1].rsplit(" - ", 1)[1].strip()) 
            except ValueError:
                continue  
        elif "Reasoning:" in line:
            rationale = line.replace("Reasoning:", "").strip()
        elif "Category:" in line:
            category = line.replace("Category:", "").strip()
            if skill_name and weightage:
                weighted_skills.append({
                    "skill": skill_name,
                    "score": weightage,
                    "rationale": rationale,
                    "category": category
                    })
            skill_name, weightage, rationale = None, None, ""  
        elif skill_name and weightage:
         rationale += " " + line.strip()
    return weighted_skills

def process_with_hr_ai(resume_text, jd_results):
    """
    Analyzes a resume against job description skills using ChatGPT and returns the overall weighted score as an integer.

    Args:
        jd_results (list): List of dictionaries containing job description skills data.
        resume_text (str): Text of the resume.
        api_key (str): OpenAI API key.

    Returns:
        int: Overall weighted score for the resume (rounded to the nearest integer).
    """
    prompt = f"""
    You are an expert in analyzing job descriptions and resumes. I will provide you with a list of skills extracted from a job description, including their weightage, rationale, and importance. Additionally, I will provide you with the text of a resume. Your task is to compare each skill from the job description against the resume text, considering the skill's weightage and rationale.

    For each skill, evaluate how well the resume demonstrates proficiency or experience in that skill. Assign a score from 1-10 for each skill based on the following sophisticated scoring criteria:

    1 (Negligible): The resume shows no mention or demonstration of the skill. There is a complete absence of any relevant evidence.
    2 (Marginal): The resume alludes to the skill in a superficial manner, without any substantive examples or context. Relevance to the job description is minimal.
    3 (Rudimentary): The resume briefly references the skill but lacks depth, detail, or evidence of practical application. Alignment with the job description is tenuous.
    4 (Elementary): The resume demonstrates a foundational understanding of the skill but lacks specific examples or measurable outcomes. Alignment with the job description is partial.
    5 (Moderate): The resume exhibits some experience with the skill, but the examples provided are generic or not strongly tied to the job description's rationale.
    6 (Progressive): The resume demonstrates clear but limited experience with the skill, showing potential for development. Alignment with the job description is evident but not fully realized.
    7 (Proficient): The resume clearly demonstrates the skill with specific examples and aligns well with the job description's rationale and weightage.
    8 (Advanced): The resume provides robust evidence of the skill, with detailed examples and clear alignment with the job description's expectations.
    9 (Exceptional): The resume demonstrates superior proficiency in the skill, with multiple examples and clear evidence of exceeding the job description's requirements.
    10 (Outstanding): The resume not only demonstrates mastery of the skill but also showcases exceptional expertise, innovation, or achievements that far surpass the job description's expectations.

    Here is the job description skills data:
    {jd_results}

    Here is the resume text:
    {resume_text}

    After evaluating each skill, calculate an overall weighted score for the resume based on the skill weightages provided in the job description.

    **Response strickly this format**
    1. **Overall Weighted Score:** Clearly state the overall weighted score in this format:
       **"Overall Weighted Score: X.X"**
    
    2. **Reasoning (Short Summary Format):** 
       - The reasoning should be **brief** and should **only mention key matching skills and relevant experience.**
       - It should not exceed **one sentence.**
       - Example format: 
         **"Candidate matches to the below key skills: Java, AWS, communication, and client handling, with 7+ years of experience in product-based companies."**
       - Do not provide a long explanation or bullet points.

    """
    
    # response = client.chat.completions.create(
    #     model="gpt-4",
    #     messages=[
    #         {"role": "system", "content": "You are an expert in analyzing job descriptions and resumes."},
    #         {"role": "user", "content": prompt}
    #     ],
    #     temperature=0
    # )

    # response_text = response.choices[0].message.content.strip()

    client = settings.SESSION.client("bedrock-runtime")

    messages = [
        {"role": "user", "content": [{"text": prompt}]},
    ]

    inference_config = {
    "temperature": 0
    }

    response = client.converse(
        modelId=settings.AWS_BEDROCK_MODEL, 
        messages=messages,
        inferenceConfig=inference_config
        )
    
    response_text = response["output"]["message"]["content"][0]["text"].strip()

    match = re.search(r"Overall Weighted Score: (\d+\.?\d*)", response_text)
    if match:
        overall_score = float(match.group(1))
    else:
        overall_score = 0
        # raise ValueError("Overall weighted score not found in the response.")

    reason_match = re.search(r"Reasoning \(Short Summary Format\):(.*?)(?=\n\n|\Z)", response_text, re.DOTALL)
    if reason_match:
        reason = reason_match.group(1).strip()
        reason = reason.replace("**", "").replace("\n", " ").strip()
    else:
        reason = "Reasoning not found in the response."

    score = {
        "score": int(round(overall_score)),
        "reason": reason
    }
    return score

def is_generated_by_ai(resume_text):
    
    prompt = f"""
You are an AI trained to determine whether a given text is human-written or AI-generated. Analyze the following resume text and classify it as either "Human-written" or "AI-generated". Provide only one of these two labels as your response.

    Resume Text:
    {resume_text}

    Instructions:
    1. Analyze the text for patterns, structure, and language usage.
    2. Classify the text as "Human-written" or "AI-generated".
    3. Do not provide any additional explanation or details.
    """
    
    # Call the Bedrock API with the prompt
    client = settings.SESSION.client("bedrock-runtime")

    messages = [
        {"role": "user", "content": [{"text": prompt}]},
    ]

    inference_config = {          
    "temperature": 0.5,      
    "topP": 1.0,              
    }

    response = client.converse(
        modelId=settings.AWS_BEDROCK_MODEL, 
        messages=messages,
        inferenceConfig=inference_config
        )

    if not response["output"] or not response["output"]["message"]["content"][0]["text"].strip():
        print("Warning: Empty response from API")
        return []

    response_text =  response["output"]["message"]["content"][0]["text"].strip()
    print(response_text)
    
    if "Human-written" in response_text:
        print("Classification: Human-written")
        classification = "Human-written"
        confidence = 1.0
        return classification, confidence
    elif "AI-generated" in response_text:
        classification = "Ai-Generated"
        confidence = 1.0
        return classification, confidence
    else:
        classification = None
        confidence = 0
        return classification, confidence
