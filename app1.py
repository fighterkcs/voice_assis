# import streamlit as st
# from audio_recorder_streamlit import audio_recorder
# import openai
# import os
# import base64

# def setup_openai_api(api_key):
#     return openai.OpenAI(api_key=api_key)

# #function to transcribe audio
# def transcribe_audio(openai_client, audio_bytes):
#     with open(audio_bytes, "rb")as audio_file:
#         transcript = openai_client.audio.transcriptions.create(model ="whisper-1", file=audio_file)
#         return transcript.text
    
# def fetch_ai_response(openai_client, input_text):
#     messages=[{"role":"user","content":input_text}]
#     response  = openai_client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=messages
#     )
#     return response.choices[0].message.content

# #convert text to speech
# def text_to_audio(openai_client, response_text,audio_path):
#     response = openai_client.audio.speech.create(model="tts-1", voice="acho", input=response_text)
#     response.stream_to_file(audio_path)


# def main():
#     st.title("Voice Assistant")
#     st.sidebar.title("API KEY ")
#     api_key= st.sidebar.text_input("Enter your OpenAI API Key:", type="password")
#     st.title("Krishna Voice Assistant")
#     st.write("Talk to Krishna, your personal voice assistant")
#     if api_key:
#         openai_client = setup_openai_api(api_key) 
#         recorderd_audio = audio_recorder()

    

# if __name__ == "__main__":
#     main()
