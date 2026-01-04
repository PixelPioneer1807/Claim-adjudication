import httpx
import base64
import json
from typing import List, Dict, Optional
from pathlib import Path
import asyncio
from .config import settings
from .schemas import ExtractedDataSchema


class AIService:
    """Service for interacting with OpenRouter API for document extraction and AI tasks"""

    def __init__(self):
        # OpenRouter API configuration
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
        print(f"   Base URL: {self.base_url}")
        print(f"   Model: {self.model}")

    async def extract_data_from_documents(self, document_paths: List[str]) -> Dict:
        """
        Extract structured data from medical documents using AI vision models.

        Args:
            document_paths: List of file paths to medical documents

        Returns:
            Dict containing extracted data and confidence score
        """
        # Convert images to base64
        base64_images = []
        for doc_path in document_paths:
            if Path(doc_path).exists():
                base64_img = self._encode_image_to_base64(doc_path)
                if base64_img:
                    base64_images.append(base64_img)

        if not base64_images:
            return {
                "extracted_data": {},
                "confidence_score": 0.0,
                "error": "No valid documents found",
            }

        try:
            # Build messages with images
            messages = self._build_vision_messages(base64_images)

            # OpenRouter endpoint
            endpoint = f"{self.base_url}/chat/completions"

            print(f"\n📤 Sending request to AI API")
            print(f"   Endpoint: {endpoint}")
            print(f"   Model: {self.model}")
            print(f"   Images: {len(base64_images)}")

            # Make API call
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

            print(f"📥 Response status: {response.status_code}")

            if response.status_code != 200:
                error_msg = response.text
                print(f"❌ AI API Error: {response.status_code}")
                print(f"   Error: {error_msg[:300]}")
                return {
                    "extracted_data": {},
                    "confidence_score": 0.0,
                    "error": f"API Error: {response.status_code} - {error_msg}",
                }

            # Parse response
            response_data = response.json()

            if "choices" not in response_data or len(response_data["choices"]) == 0:
                print(f"❌ Unexpected response format")
                return {
                    "extracted_data": {},
                    "confidence_score": 0.0,
                    "error": f"Unexpected response format: {response_data}",
                }

            response_text = response_data["choices"][0]["message"]["content"]
            print(f"✅ Got response from AI model")
            print(f"   Response length: {len(response_text)} chars")

            # Clean response text
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = (
                    response_text.replace("```json", "").replace("```", "").strip()
                )
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            # Parse JSON
            extracted_data = json.loads(response_text)
            print(f"✅ Successfully parsed JSON")

            # Calculate confidence
            confidence = self._calculate_confidence(extracted_data)

            return {
                "extracted_data": extracted_data,
                "confidence_score": confidence,
                "error": None,
            }

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {str(e)}")
            if "response_text" in locals():
                print(f"   Response text: {response_text[:300]}")
            return {
                "extracted_data": {},
                "confidence_score": 0.0,
                "error": f"JSON parsing error: {str(e)}",
            }
        except Exception as e:
            print(f"❌ Error in extract_data_from_documents: {str(e)}")
            import traceback

            traceback.print_exc()
            return {"extracted_data": {}, "confidence_score": 0.0, "error": str(e)}

    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Encode image file to base64 string."""
        try:
            with open(image_path, "rb") as image_file:
                base64_str = base64.standard_b64encode(image_file.read()).decode(
                    "utf-8"
                )
                print(f"   ✅ Encoded image: {Path(image_path).name}")
                return base64_str
        except Exception as e:
            print(f"   ❌ Error encoding image {image_path}: {e}")
            return None

    def _build_vision_messages(self, base64_images: List[str]) -> List[Dict]:
        """Build messages array with text and images."""
        content = [{"type": "text", "text": self._build_extraction_prompt()}]

        # Add images
        for i, base64_img in enumerate(base64_images):
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"},
                }
            )
            print(f"   ✅ Added image {i + 1} to message")

        return [{"role": "user", "content": content}]

    def _build_extraction_prompt(self) -> str:
        """Build detailed prompt for extracting medical document data"""
        return """You are an expert medical document analyzer for insurance claim processing.
Analyze the provided medical documents (prescriptions, bills, diagnostic reports) and extract structured information.

Return ONLY a valid JSON object (no markdown, no explanations, just pure JSON) with this exact structure:

{
  "patient_name": "Full name of patient or null",
  "patient_age": "Age as string or null",
  "patient_gender": "Male/Female/Other or null",
  "doctor_name": "Full name with title or null",
  "doctor_registration": "Registration in STATE/NUMBER/YEAR format or null",
  "clinic_hospital_name": "Name of clinic or hospital or null",
  "treatment_date": "Date in YYYY-MM-DD format or null",
  "diagnosis": "Primary diagnosis/condition or null",
  "chief_complaints": ["List of symptoms"] or null,
  "medicines_prescribed": [
    {
      "name": "Medicine name with strength",
      "dosage": "Dosage pattern",
      "duration": "Duration"
    }
  ] or null,
  "diagnostic_tests": ["CBC", "X-Ray"] or null,
  "procedures_performed": ["List of procedures"] or null,
  "consultation_fee": 1000.0 or null,
  "diagnostic_charges": 500.0 or null,
  "medicine_charges": 300.0 or null,
  "procedure_charges": 0.0 or null,
  "total_amount": 1800.0 or null,
  "bill_number": "Bill/Invoice number or null",
  "payment_mode": "Cash/Card/UPI or null",
  "extraction_confidence": 0.95
}

CRITICAL RULES:
1. Extract ONLY information clearly visible in documents
2. Use null for missing/unclear fields (NOT empty strings)
3. Amounts must be numeric floats (remove ₹, Rs, currency symbols)
4. All dates in YYYY-MM-DD format
5. Doctor registration: STATE/NUMBER/YEAR (e.g., KA/45678/2015)
6. extraction_confidence: 0.0-1.0 based on document clarity (0.9+ for clear docs)
7. Return ONLY the JSON object - no explanations or markdown"""

    def _calculate_confidence(self, extracted_data: Dict) -> float:
        """Calculate confidence score based on data completeness."""
        if "extraction_confidence" in extracted_data:
            model_confidence = extracted_data.get("extraction_confidence", 0.7)
            try:
                return round(float(model_confidence), 2)
            except (ValueError, TypeError):
                pass

        critical_fields = [
            "patient_name",
            "doctor_name",
            "doctor_registration",
            "diagnosis",
            "treatment_date",
            "total_amount",
        ]

        present_fields = sum(
            1 for field in critical_fields if extracted_data.get(field) is not None
        )

        base_confidence = present_fields / len(critical_fields)
        return round(base_confidence, 2)

    async def process_claim_with_ai(self, claim_data: Dict, policy_terms: Dict) -> Dict:
        """Use AI to determine if claim meets medical necessity requirements."""
        prompt = f"""Analyze this medical claim for medical necessity and return ONLY JSON (no markdown).

CLAIM DATA:
- Diagnosis: {claim_data.get("diagnosis")}
- Medicines: {claim_data.get("medicines_prescribed")}
- Tests: {claim_data.get("diagnostic_tests")}

Return ONLY this JSON:
{{
  "is_medically_necessary": true or false,
  "reasoning": "explanation",
  "confidence": 0.0-1.0
}}"""

        try:
            endpoint = f"{self.base_url}/chat/completions"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    endpoint,
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                    },
                )

            if response.status_code == 200:
                response_data = response.json()
                response_text = response_data["choices"]["message"]["content"]

                # Clean markdown
                response_text = response_text.strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()

                return json.loads(response_text)
            else:
                return {
                    "is_medically_necessary": True,
                    "reasoning": "Could not verify",
                    "confidence": 0.5,
                }
        except Exception as e:
            print(f"❌ Error in AI assessment: {str(e)}")
            return {
                "is_medically_necessary": True,
                "reasoning": f"Error: {str(e)}",
                "confidence": 0.5,
            }


# Create singleton instance
ai_service = AIService()
