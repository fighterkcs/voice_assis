import google.generativeai as genai
import os 
import re
from dotenv import load_dotenv
load_dotenv()
import streamlit as st

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

MODEL_NAME = "gemini-1.5-flash"

def _create_fresh_model():
    return genai.GenerativeModel(MODEL_NAME)

def normalize_hinglish_to_english(hinglish_text):
    if not hinglish_text or not hinglish_text.strip():
        return ""
    text = hinglish_text.strip()
    hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))
    total_chars = len(re.findall(r'[a-zA-Z\u0900-\u097F\s]', text))
    if total_chars > 0 and hindi_chars / total_chars < 0.2:
        return text
    normalization_prompt = f"""Convert this Hinglish (Hindi+English mix) text to clean English while preserving the exact meaning and intent.

Hinglish: {text}

Output ONLY the normalized English text, nothing else:"""
    try:
        model = _create_fresh_model()
        response = model.generate_content(normalization_prompt)
        if response and hasattr(response, 'text') and response.text:
            normalized = response.text.strip()
            normalized = re.sub(r'^(English:|Normalized:|\"|\')', '', normalized, flags=re.IGNORECASE).strip()
            normalized = normalized.strip('"\'')
            return normalized if normalized else text
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
            raise
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
    if not hinglish_text or not hinglish_text.strip():
        return "Welcome, dear one. Speak what troubles your heart."
    text_lower = hinglish_text.strip().lower()
    simple_greetings = ["hi", "hello", "hey", "hi there", "hello there", "hey there", "namaste", "namaskar"]
    if text_lower in simple_greetings or text_lower in ["how are you", "how are you?", "what's up", "what's up?", "good morning", "good afternoon", "good evening", "kaise ho", "kaise hain"]:
        return "Welcome, dear one. Speak what troubles your heart."
    normalized_text = normalize_hinglish_to_english(hinglish_text)
    intent_prompt = INTENT_PROMPT.format(text=normalized_text)
    intent = None
    try:
        model = _create_fresh_model()
        response = model.generate_content(intent_prompt)
        if response and hasattr(response, 'text') and response.text:
            response_text = response.text.strip()
            if "Intent:" in response_text:
                intent_line = [line for line in response_text.split('\n') if 'Intent:' in line]
                if intent_line:
                    intent = intent_line[0].split('Intent:')[-1].strip()
            if not intent or "no-intent" in intent.lower() or "casual greeting" in intent.lower():
                return "Welcome, dear one. Speak what troubles your heart."
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
            return "Krishna is momentarily unavailable due to API quota limits. Please try again shortly."
        intent = "Daily Struggles"
    if not intent:
        intent = "Daily Struggles"
    hinglish_prompt = HINGLISH_RESPONSE_PROMPT.format(
        intent=intent,
        normalized_text=normalized_text
    )
    try:
        model = _create_fresh_model()
        response = model.generate_content(hinglish_prompt)
        if response and hasattr(response, 'text') and response.text:
            hinglish_response = response.text.strip()
            hinglish_response = re.sub(r'^(Response:|Hinglish Response:|\"|\')', '', hinglish_response, flags=re.IGNORECASE).strip()
            hinglish_response = hinglish_response.strip('"\'')
            return hinglish_response if hinglish_response else "Welcome, dear one. Speak what troubles your heart."
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
            return "Krishna is momentarily unavailable due to API quota limits. Please try again shortly."
        return "Welcome, dear one. Speak what troubles your heart."
    return "Welcome, dear one. Speak what troubles your heart."
