import os
from google import genai
import logging
import time

class GeminiSummarizer:
    def __init__(self):
        api_key = os.environ["GEMINI_API_KEY"]
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables")
        
        # New SDK Client
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-3-flash-preview' # Default to 3 Flash as requested
        self.logger = logging.getLogger(__name__)

    def summarize(self, text, user_instruction=None):
        """
        Sends text to Gemini for summarization using google-genai SDK.
        """
        if not text or len(text.strip()) == 0:
            return "No content to summarize."

        # Construct Prompt
        if user_instruction:
            prompt = f"""
            You are a helpful assistant maximizing the utility of the user's Notion database.
            
            User's Instruction: "{user_instruction}"
            
            Please process the following text according to the user's instruction.
            If the instruction is a question, answer it based on the text.
            If it's a summary request, summarize accordingly.
            
            Text Content from Database:
            {text[:1000000]} 
            """
        else:
            prompt = f"""
            Please summarize the following text in Korean. 
            Capture the main points and key takeaways.
            
            Text:
            {text[:1000000]} 
            """ 
        
        # Retry Logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Sending request to Gemini ({self.model_name})...")
                # New SDK Usage
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                # Check for Quota Limit (429)
                error_str = str(e)
                if "429" in error_str or "Quota" in error_str or "quota" in error_str:
                    # Model Fallback Logic
                    if self.model_name == 'gemini-3-flash-preview':
                        self.logger.warning("⚠️ Gemini 3.0 Flash Quota Exceeded. Switching to 2.5 Flash...")
                        self.model_name = 'gemini-2.5-flash'
                        continue # Retry immediately with new model
                        
                    wait_time = 60
                    self.logger.warning(f"⚠️ Gemini API Quota exceeded (Attempt {attempt+1}/{max_retries}).")
                    self.logger.warning(f"   Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"Error generating summary: {e}")
                    return f"Failed to generate summary: {e}"
        
        return "Failed to generate summary after retries (Quota Limit)."
