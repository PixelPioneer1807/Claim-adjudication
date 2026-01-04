import httpx
import base64
import json
import fitz 
from typing import List, Dict, Optional
from pathlib import Path
import asyncio
from .config import settings


class AIService:
    """Service for interacting with OpenRouter API for document extraction and AI tasks"""

    def __init__(self):
        self.base_url = settings.AI_BASE_URL.rstrip("/")
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "OPD Claim Adjudication System",
        }
        print(f"✅ AI Service initialized")

    async def extract_data_from_documents(self, document_paths: List[str]) -> Dict:
        """
        Extract structured data from medical documents (Images OR PDFs).
        """
        base64_images = []

        for doc_path in document_paths:
            path_obj = Path(doc_path)
            if not path_obj.exists():
                continue

            # ✅ LOGIC TO PROCESS PDF FILES (Using PyMuPDF)
            if path_obj.suffix.lower() == ".pdf":
                try:
                    print(f"   📄 Processing PDF: {path_obj.name}")
                    doc = fitz.open(doc_path)

                    for i, page in enumerate(doc):
                        # Render page to image (pixmap)
                        pix = page.get_pixmap(
                            matrix=fitz.Matrix(2, 2)
                        )  # 2x zoom for better OCR quality
                        img_bytes = pix.tobytes("jpeg")

                        img_str = base64.standard_b64encode(img_bytes).decode("utf-8")
                        base64_images.append(img_str)
                        print(f"      - Converted Page {i + 1}")

                    doc.close()

                except Exception as e:
                    error_msg = f"PDF Conversion Failed: {str(e)}"
                    print(f"❌ {error_msg}")
                    return {
                        "extracted_data": {},
                        "confidence_score": 0.0,
                        "error": error_msg,
                    }

            # ✅ LOGIC FOR STANDARD IMAGES
            else:
                base64_img = self._encode_image_to_base64(doc_path)
                if base64_img:
                    base64_images.append(base64_img)

        if not base64_images:
            return {
                "extracted_data": {},
                "confidence_score": 0.0,
                "error": "No valid documents processed",
            }

        try:
            # Build messages
            messages = self._build_vision_messages(base64_images)
            endpoint = f"{self.base_url}/chat/completions"

            print(f"\n📤 Sending request to AI API ({len(base64_images)} pages/images)")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    endpoint,
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.1,
                        "max_tokens": 2000,
                    },
                )

            if response.status_code != 200:
                print(f"❌ AI API Error: {response.status_code}")
                return {
                    "extracted_data": {},
                    "confidence_score": 0.0,
                    "error": f"API Error: {response.status_code}",
                }

            # Parse response
            content = response.json()["choices"][0]["message"]["content"]
            if "```" in content:
                content = content.replace("```json", "").replace("```", "").strip()

            extracted_data = json.loads(content)

            print("\n" + "=" * 30)
            print("🧐 AI EXTRACTED DATA:")
            print(json.dumps(extracted_data, indent=2))
            print("=" * 30 + "\n")

            return {
                "extracted_data": extracted_data,
                "confidence_score": self._calculate_confidence(extracted_data),
                "error": None,
            }

        except Exception as e:
            print(f"❌ Error in extract_data_from_documents: {str(e)}")
            return {"extracted_data": {}, "confidence_score": 0.0, "error": str(e)}

    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        try:
            with open(image_path, "rb") as image_file:
                return base64.standard_b64encode(image_file.read()).decode("utf-8")
        except Exception:
            return None

    def _build_vision_messages(self, base64_images: List[str]) -> List[Dict]:
        content = [{"type": "text", "text": self._build_extraction_prompt()}]
        for base64_img in base64_images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"},
                }
            )
        return [{"role": "user", "content": content}]

    def _build_extraction_prompt(self) -> str:
        return """You are an expert medical document analyzer.
Extract structured information from the provided medical documents.

Return ONLY a valid JSON object with this exact structure:

{
  "patient_name": "Full name or null",
  "patient_age": "Age string or null",
  "doctor_name": "Name or null",
  "doctor_registration": "Registration No or null",
  "clinic_hospital_name": "Hospital Name or null",
  "treatment_date": "YYYY-MM-DD or null",
  "diagnosis": "Primary diagnosis or null",
  "medicines_prescribed": [{"name": "...", "dosage": "..."}] or null,
  "diagnostic_tests": ["..."] or null,
  "procedures_performed": ["..."] or null,
  "total_amount": 1000.0 or null,
  "pre_authorization_number": "Pre-auth/Approval number if visible or null",
  "extraction_confidence": 0.95
}

CRITICAL: 
1. Return ONLY JSON. No markdown.
2. If the document mentions 'Pre-Auth' or 'Approval', capture that number.
3. Convert all dates to YYYY-MM-DD.
"""

    def _calculate_confidence(self, extracted_data: Dict) -> float:
        if "extraction_confidence" in extracted_data:
            try:
                return round(float(extracted_data["extraction_confidence"]), 2)
            except:
                pass
        return 0.85

    async def process_claim_with_ai(self, claim_data: Dict, policy_terms: Dict) -> Dict:
        """
        Uses AI to check medical necessity with enhanced Context Clues.
        """
        exclusions = policy_terms.get("exclusions", [])
        alt_med = policy_terms.get("coverage_details", {}).get(
            "alternative_medicine", {}
        )
        covered_alt = (
            alt_med.get("covered_treatments", []) if alt_med.get("covered") else []
        )

        prompt = f"""
        You are an expert Insurance Adjudicator. Review this claim against the policy rules.

        POLICY CONTEXT:
        1. EXCLUSIONS (Reject these): {exclusions}
        2. ALLOWED ALTERNATIVE MEDICINE: {covered_alt}

        CLAIM DETAILS:
        - Doctor Name: {claim_data.get("doctor_name")}
        - Pre-Auth No: {claim_data.get("pre_authorization_number")}
        - Diagnosis: {claim_data.get("diagnosis")}
        - Medicines: {claim_data.get("medicines_prescribed")}
        - Procedures: {claim_data.get("procedures_performed")}

        TASK:
        1. Check EXCLUSIONS first.
        2. CONTEXT CLUES:
           - If Doctor title is 'Vaidya' or Pre-Auth contains 'AYUR', this is AYURVEDIC treatment.
           - If Ayurvedic, check if the diagnosis generally aligns with 'Panchakarma' or similar therapies.
        3. DECISION:
           - If Standard Medicine: Verify matching diagnosis.
           - If Ayurvedic (Identified via context): Mark as medically necessary if it aligns with ALLOWED ALTERNATIVE MEDICINE.

        Return valid JSON only:
        {{
            "is_medically_necessary": boolean,
            "reasoning": "Short explanation using context clues.",
            "confidence": 0.9
        }}
        """

        try:
            endpoint = f"{self.base_url}/chat/completions"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    endpoint,
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                if "```" in content:
                    content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(content)

        except Exception as e:
            print(f"⚠️ AI Medical Necessity Check Failed: {e}")
            pass

        return {
            "is_medically_necessary": True,
            "reasoning": "Standard protocol (AI Check Skipped)",
            "confidence": 0.9,
        }


ai_service = AIService()
