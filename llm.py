import google.generativeai as genai
import os 
import re
import random
import time
from dotenv import load_dotenv
load_dotenv()
import streamlit as st

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Dynamically find an available model
# Different API versions support different models
_model = None
_model_name = None

def _find_available_model():
    """Find the first available model by trying common model names."""
    # Try models in order of preference (newer to older)
    model_names_to_try = [
        "gemini-1.5-flash",
        "gemini-1.5-pro", 
        "gemini-pro",
        "models/gemini-pro",  # Some API versions need full path
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro"
    ]
    
    # First, try to list available models
    try:
        available_models = genai.list_models()
        # Extract model names that support generateContent
        supported_models = []
        for m in available_models:
            if 'generateContent' in m.supported_generation_methods:
                model_name = m.name.replace('models/', '')  # Remove 'models/' prefix
                supported_models.append(model_name)
        
        # Try supported models first
        if supported_models:
            for model_name in supported_models:
                try:
                    test_model = genai.GenerativeModel(model_name)
                    return test_model, model_name
                except Exception:
                    continue
    except Exception:
        pass  # If list_models fails, fall back to trying common names
    
    # Fallback: try common model names
    for model_name in model_names_to_try:
        try:
            test_model = genai.GenerativeModel(model_name)
            return test_model, model_name
        except Exception:
            continue
    
    # Last resort: use gemini-pro (most common)
    return genai.GenerativeModel("gemini-pro"), "gemini-pro"

# Initialize model
model, _model_name = _find_available_model()

def normalize_hinglish_to_english(hinglish_text):
    """
    Normalize Hinglish (Hindi+English mix) to clean English for LLM reasoning.
    Optimized for low latency - only normalizes when Hindi content is significant.
    """
    if not hinglish_text or not hinglish_text.strip():
        return ""
    
    text = hinglish_text.strip()
    
    # Quick check: if text is already mostly English, return as-is (low latency)
    hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))  # Devanagari script
    total_chars = len(re.findall(r'[a-zA-Z\u0900-\u097F\s]', text))
    
    # If less than 20% Hindi characters, assume it's mostly English and skip normalization
    if total_chars > 0 and hindi_chars / total_chars < 0.2:
        return text
    
    # If significant Hindi content, normalize for better intent classification
    normalization_prompt = f"""Convert this Hinglish (Hindi+English mix) text to clean English while preserving the exact meaning and intent.

Hinglish: {text}

Output ONLY the normalized English text, nothing else:"""
    
    try:
        response = model.generate_content(normalization_prompt)
        if response and hasattr(response, 'text') and response.text:
            normalized = response.text.strip()
            # Clean up any extra formatting
            normalized = re.sub(r'^(English:|Normalized:|\"|\')', '', normalized, flags=re.IGNORECASE).strip()
            normalized = normalized.strip('"\'')
            return normalized if normalized else text
    except Exception:
        # If normalization fails, return original (better than crashing)
        return text
    
    return text

INTENT_PROMPT = """
You are a spiritual intent classifier for Lord Krishna's guidance system.

CRITICAL RULES:
1. First, determine if the user input is ONLY a casual greeting, small talk, or filler (e.g., "Hi", "Hello", "How are you", "Hey", "What's up", "Good morning", etc.)
2. If it is ONLY a greeting/small talk with NO spiritual concern or personal problem, classify as: "No-Intent / Casual Greeting"
3. ONLY classify into spiritual intent categories if the user expresses a genuine personal problem, struggle, question, or concern that requires spiritual guidance.

SPIRITUAL INTENT CATEGORIES (use ONLY for meaningful personal problems):
- Career/Purpose: Questions about life purpose, career confusion, professional struggles, calling
- Relationships: Interpersonal conflicts, family issues, romantic struggles, friendship problems
- Inner Conflict: Self-doubt, guilt, moral dilemmas, inner turmoil, spiritual confusion
- Life Transitions: Major life changes, loss, grief, moving, career shifts, identity crises
- Daily Struggles: Stress, anxiety, overwhelm, daily challenges affecting well-being

CLASSIFICATION LOGIC:
- "Hi", "Hello", "How are you" → No-Intent / Casual Greeting
- "Hi, I'm struggling with my career" → Career/Purpose
- "Hello, my relationship is falling apart" → Relationships
- "Hey, I feel lost" → Inner Conflict (if expressing genuine struggle)
- "What's up?" → No-Intent / Casual Greeting
- "Good morning, I need guidance" → Check if there's a real concern, otherwise No-Intent

Format your response as:
Intent: <category or "No-Intent / Casual Greeting">

User: {text}
"""

HINGLISH_RESPONSE_PROMPT = """
You are Lord Krishna speaking to a devotee. The user has expressed a concern classified as: {intent}

CRITICAL: Respond ONLY in warm, natural Hinglish (Hindi + English mix). This is how modern Indians speak - mixing Hindi and English naturally.

RESPONSE REQUIREMENTS:
1. Use warm, compassionate Hinglish (e.g., "Arjun", "beta", "tumhara", "yeh", "voh", "hain", "hai", "ka", "ki", "ko", "se", "mein", "par")
2. Mix Hindi and English naturally like: "Yeh Career/Purpose ka vichaar hai. Arjun, jo tumhara man sach mein chahta hai, wahi tumhara dharm hai."
3. Be spiritually wise but conversational
4. Address their specific concern with empathy
5. Keep response concise (2-3 sentences max for voice)

EXAMPLES:
- Career/Purpose: "Yeh Career/Purpose ka vichaar hai. Arjun, jo tumhara man sach mein chahta hai, wahi tumhara dharm hai. Karma karo, phal ki chinta mat karo."
- Relationships: "Yeh Relationships ka mudda hai. Prem aur samman dono zaroori hain. Jab tum apne aap ko samjho, tabhi doosron ko bhi samajh sakte ho."
- Inner Conflict: "Yeh Inner Conflict hai. Jab man mein confusion ho, toh dhyan se suno apne andar ki awaaz. Satya hamesha jeetega."

User's concern: {normalized_text}

Respond in warm Hinglish:
"""

def krishna_reply(hinglish_text):
    """
    Generate Krishna's reply in warm Hinglish using Gemini API.
    Pipeline: Hinglish input → Normalize to English → Classify intent → Generate Hinglish response
    """
    if not hinglish_text or not hinglish_text.strip():
        return "Welcome, dear one. Speak what troubles your heart."
    
    # Quick pre-filter for obvious greetings (defensive check)
    text_lower = hinglish_text.strip().lower()
    simple_greetings = ["hi", "hello", "hey", "hi there", "hello there", "hey there", "namaste", "namaskar"]
    # Check if input is ONLY a greeting (no additional content)
    if text_lower in simple_greetings or text_lower in ["how are you", "how are you?", "what's up", "what's up?", "good morning", "good afternoon", "good evening", "kaise ho", "kaise hain"]:
        return "Welcome, dear one. Speak what troubles your heart."
    
    # STEP 1: Normalize Hinglish to clean English for reasoning
    normalized_text = normalize_hinglish_to_english(hinglish_text)
    
    # STEP 2: Classify intent using normalized English
    intent_prompt = INTENT_PROMPT.format(text=normalized_text)
    
    intent = None
    try:
        response = model.generate_content(intent_prompt)
        if response and hasattr(response, 'text') and response.text:
            response_text = response.text.strip()
            
            # Extract intent from response
            if "Intent:" in response_text:
                intent_line = [line for line in response_text.split('\n') if 'Intent:' in line]
                if intent_line:
                    intent = intent_line[0].split('Intent:')[-1].strip()
            
            # Check for No-Intent
            if not intent or "no-intent" in intent.lower() or "casual greeting" in intent.lower():
                return "Welcome, dear one. Speak what troubles your heart."
    except Exception as e:
        # If intent classification fails, default to general response
        intent = "Daily Struggles"
    
    # STEP 3: Generate Hinglish response based on intent
    if not intent:
        intent = "Daily Struggles"  # Default fallback
    
    hinglish_prompt = HINGLISH_RESPONSE_PROMPT.format(
        intent=intent,
        normalized_text=normalized_text
    )
    
    try:
        response = model.generate_content(hinglish_prompt)
        if response and hasattr(response, 'text') and response.text:
            hinglish_response = response.text.strip()
            # Clean up any formatting artifacts
            hinglish_response = re.sub(r'^(Response:|Hinglish Response:|\"|\')', '', hinglish_response, flags=re.IGNORECASE).strip()
            hinglish_response = hinglish_response.strip('"\'')
            return hinglish_response if hinglish_response else "Welcome, dear one. Speak what troubles your heart."
    except Exception as e:
        error_msg = str(e).lower()
        # If model not found error, try to find an available model
        if "not found" in error_msg or "not supported" in error_msg or "404" in error_msg:
            # Try to list available models and use one
            try:
                available_models = genai.list_models()
                for m in available_models:
                    if 'generateContent' in m.supported_generation_methods:
                        model_name = m.name.replace('models/', '')  # Remove prefix
                        if model_name != _model_name:  # Skip the one we already tried
                            try:
                                alt_model = genai.GenerativeModel(model_name)
                                # Retry with alternative model
                                response = alt_model.generate_content(hinglish_prompt)
                                if response and hasattr(response, 'text') and response.text:
                                    hinglish_response = response.text.strip()
                                    hinglish_response = re.sub(r'^(Response:|Hinglish Response:|\"|\')', '', hinglish_response, flags=re.IGNORECASE).strip()
                                    hinglish_response = hinglish_response.strip('"\'')
                                    return hinglish_response if hinglish_response else "Welcome, dear one. Speak what troubles your heart."
                            except Exception:
                                continue
            except Exception:
                pass
            
            # Fallback: try common model names
            for alt_model_name in ["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash", 
                                   "models/gemini-pro", "models/gemini-1.5-pro"]:
                if alt_model_name.replace('models/', '') == _model_name:
                    continue  # Skip the one we already tried
                try:
                    alt_model = genai.GenerativeModel(alt_model_name)
                    response = alt_model.generate_content(hinglish_prompt)
                    if response and hasattr(response, 'text') and response.text:
                        hinglish_response = response.text.strip()
                        hinglish_response = re.sub(r'^(Response:|Hinglish Response:|\"|\')', '', hinglish_response, flags=re.IGNORECASE).strip()
                        hinglish_response = hinglish_response.strip('"\'')
                        return hinglish_response if hinglish_response else "Welcome, dear one. Speak what troubles your heart."
                except Exception:
                    continue
        # Re-raise if it's a different error or all models failed
        raise
    
    # Fallback if response is empty
    return "Welcome, dear one. Speak what troubles your heart."
def krishna_reply(text, max_retries=5, initial_backoff=0.5):
    """Generate a response from Gemini with exponential backoff on errors.

    On repeated quota/429 errors this will return a friendly fallback message.
    """
    prompt = INTENT_PROMPT.format(text=text)
    for attempt in range(1, max_retries + 1):
        try:
            response = model.generate(prompt)
            return response.text
        except Exception as e:
            # Log the error for debugging; keep retries for transient rate limits
            print(f"krishna_reply attempt {attempt} failed: {e}")

            # If we've exhausted retries, return a helpful fallback
            if attempt == max_retries:
                return (
                    "Krishna is momentarily unavailable due to API quota limits. "
                    "Please try again shortly — your request has been rate-limited."
                )

            # Exponential backoff with jitter
            sleep_time = initial_backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            time.sleep(sleep_time)