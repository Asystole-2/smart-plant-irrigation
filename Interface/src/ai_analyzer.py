import os
import json
import logging
import google.generativeai as genai

class PlantCareAIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.logger = logging.getLogger(__name__)

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.logger.debug("Gemini AI initialized successfully.")
        else:
            self.logger.warning("GEMINI_API_KEY not found in environment.")

    def get_care_advice(self, plant_data):
        if not self.api_key:
            return self._get_default_advice(plant_data)

        try:
            # Detailed prompt for species-specific and long-form advice
            prompt = f"""
            Act as an expert botanist and smart irrigation specialist. 
            Provide a highly detailed, professional care analysis for a {plant_data['name']} (Species/Type) 
            located in {plant_data['location']} with the following environment: {plant_data.get('environment_desc')}.

            Current System Data:
            - Soil Moisture: {plant_data.get('last_moisture', 'unknown')}%

            Requirements:
            1. Differ your advice specifically for the biological needs of a {plant_data['name']}.
            2. Provide 2-3 detailed paragraphs for EACH category.
            3. For 'watering', explain how the current moisture of {plant_data.get('last_moisture')}% relates to this specific plant's needs.

            Return ONLY a JSON object with these keys: 
            "watering", "lighting", "fertilization", "other".
            """

            self.logger.debug(f"Requesting detailed AI analysis for: {plant_data['name']}")
            response = self.model.generate_content(prompt)

            # Clean and parse
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(raw_text)

        except Exception as e:
            self.logger.error(f"Detailed Gemini API Error: {str(e)}")
            return self._get_default_advice(plant_data)

    def _get_default_advice(self, plant_data):
        """Fallback advice to ensure UI remains functional"""
        self.logger.debug("Returning fallback care advice.")
        return {
            "watering": f"Monitor {plant_data['name']} moisture levels regularly. Water when topsoil feels dry.",
            "lighting": "Ensure plant receives adequate natural light based on its specific species needs.",
            "fertilization": "Use a balanced liquid fertilizer once a month during growing seasons.",
            "other": "Check leaves for dust or pests to maintain optimal plant health."
        }