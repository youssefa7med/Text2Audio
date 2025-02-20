import requests
import os
import streamlit as st
from transformers import pipeline
from langchain_community.llms import HuggingFaceHub
from langchain import PromptTemplate, LLMChain
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Validate Image URL
def is_valid_image_url(url):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200 and response.headers["Content-Type"].startswith("image"):
            return True
    except Exception:
        return False
    return False

# Image to Text Function
def img2text_url(image_url):
    API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
    headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACEHUB_API_TOKEN')}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": image_url})
        response.raise_for_status()
        return response.json()[0]["generated_text"]
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

# Generate Story Function
def generate_story(scenario):
    template = """
    You are a story teller;
    You can generate a very short story based on a simple narrative, be creative and the story should be between 10 to 50 words;
    CONTEXT: {scenario}
    STORY:
    """
    prompt = PromptTemplate(template=template, input_variables=["scenario"])
    
    models = [
        "HuggingFaceH4/zephyr-7b-beta",  # Lightweight model
        "deepseek-ai/DeepSeek-R1",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
    ]
    
    for model in models:
        retry_attempts = 3
        for attempt in range(retry_attempts):
            try:
                story_llm = LLMChain(
                    llm=HuggingFaceHub(repo_id=model, 
                                       model_kwargs={"temperature":1, "max_length":512}), 
                    prompt=prompt
                )
                story = story_llm.predict(scenario=scenario)
                return story.split('\n')[-1].strip()
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {model}: {e}")
                time.sleep(2**attempt)  # Exponential backoff (2s, 4s, 8s)
    
    return "Error: Unable to generate story after multiple attempts."

# Text to Speech Function
def text2speech(message):
    API_URL = "https://api-inference.huggingface.co/models/espnet/kan-bayashi_ljspeech_vits"
    headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACEHUB_API_TOKEN')}"}
    payload = {'inputs': message}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        audio_path = "audio.flac"
        with open(audio_path, "wb") as file:
            file.write(response.content)
        return audio_path
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

# Streamlit UI
def main():
    st.set_page_config(page_title="AI-Powered Story Generator", layout="centered")
    st.title("📖 AI Story Generator from Image URL")
    
    st.sidebar.title("Settings")
    st.sidebar.write("Enter an image URL to generate a short story!")
    
    image_url = st.text_input("🔗 Enter Image URL")
    
    if image_url:
        if is_valid_image_url(image_url):
            st.image(image_url, caption="Uploaded Image", use_container_width =True)
            
            progress = st.progress(0)
            progress.progress(25)
            caption = img2text_url(image_url)
            if "Error" in caption:
                st.error(f"❌ Failed to generate caption: {caption}")
                return
            st.success("✅ Image caption generated successfully!")
            progress.progress(50)
            
            story = generate_story(caption)
            if "Error" in story:
                st.error(f"❌ Failed to generate story: {story}")
                return
            st.success("✅ Story generated successfully!")
            progress.progress(75)
            
            audio_file = text2speech(story)
            if "Error" in audio_file:
                st.error(f"❌ Failed to generate audio: {audio_file}")
                return
            st.success("✅ Audio generated successfully!")
            progress.progress(100)
            
            with st.expander("📷 See Image Caption"):
                st.write(caption)
            
            with st.expander("📖 Read Generated Story"):
                st.write(story)
            
            if audio_file:
                with st.expander("🔊 Listen to the Story"):
                    st.audio(audio_file, format="audio/flac")
        else:
            st.error("❌ Invalid image URL. Please enter a valid image link.")

if __name__ == "__main__":
    main()
