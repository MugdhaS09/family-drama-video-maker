import streamlit as st
import requests
import os
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, AudioFileClip, concatenate_videoclips, ImageSequenceClip
import numpy as np
from io import BytesIO
import tempfile

# Streamlit app title
st.title("Family Drama Video Maker")
st.write("Create a YouTube video like FamilialBonds Exposed with one dramatic story (>10 minutes).")

# Input fields
story_text = st.text_area("Story Text (include intro, story, commentary, outro)", height=300, help="Paste your anonymized Reddit story with emotional cues, e.g., [DRAMATIC TONE].")
voice_option = st.selectbox("Voice", ["Rachel", "Matthew"], help="Choose a dramatic voice.")
music_url = st.text_input("Background Music URL", "https://cdn.pixabay.com/audio/2022/03/14/audio_2b7e462d6b.mp3", help="Paste a royalty-free MP3 URL from Pixabay.")
text_color = st.selectbox("Text Color", ["White", "Red"], help="Color for on-screen text.")

# ElevenLabs API setup
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/"

# Function to generate voiceover
def generate_voiceover(text, voice):
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
    }
    voice_id = "EXAVITQu4vr4xnSDxMaL" if voice == "Rachel" else "pNInz6obpgDQGcFmaJgB"
    response = requests.post(f"{ELEVENLABS_API_URL}{voice_id}", json=data, headers=headers)
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(response.content)
            return tmp.name
    else:
        st.error("Voiceover generation failed!")
        return None

# Function to create text slide
def create_text_slide(text, width=1920, height=1080, color="white"):
    img = Image.new("RGB", (width, height), color="black")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()
    text_width, text_height = draw.textsize(text, font=font)
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.text((x, y), text, fill=color, font=font)
    img_buffer = BytesIO()
    img.save(img_buffer, format="PNG")
    return np.array(Image.open(img_buffer))

# Function to split text into slides
def split_text_to_slides(text, max_chars=200):
    words = text.split()
    slides = []
    current_slide = ""
    for word in words:
        if len(current_slide) + len(word) < max_chars:
            current_slide += word + " "
        else:
            slides.append(current_slide.strip())
            current_slide = word + " "
    if current_slide:
        slides.append(current_slide.strip())
    return slides

# Generate video button
if st.button("Generate Video"):
    if not story_text or not ELEVENLABS_API_KEY:
        st.error("Please provide story text and set ELEVENLABS_API_KEY in Streamlit secrets.")
    else:
        with st.spinner("Generating video..."):
            # Generate voiceover
            audio_file = generate_voiceover(story_text, voice_option)
            if not audio_file:
                st.stop()

            # Create text slides
            slides = split_text_to_slides(story_text)
            slide_images = [create_text_slide(slide, color=text_color.lower()) for slide in slides]

            # Create video clips for each slide
            audio = AudioFileClip(audio_file)
            duration_per_slide = audio.duration / len(slides)
            clips = [ImageSequenceClip([img], durations=[duration_per_slide]).set_duration(duration_per_slide) for img in slide_images]

            # Concatenate clips
            video = concatenate_videoclips(clips, method="compose")

            # Download and add background music
            music_response = requests.get(music_url)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as music_tmp:
                music_tmp.write(music_response.content)
                music_audio = AudioFileClip(music_tmp.name).volumex(0.15)
                if music_audio.duration < audio.duration:
                    music_audio = music_audio.fx(vfx.loop, duration=audio.duration)
                video = video.set_audio(audio.set_duration(video.duration).fx(vfx.fadein, 1).fx(vfx.fadeout, 1))
                video = video.set_audio(video.audio.set_volume(1).fx(vfx.audio_fadein, 1).fx(vfx.audio_fadeout, 1).composite(music_audio))

            # Save video
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as video_tmp:
                video.write_videofile(video_tmp.name, codec="libx264", audio_codec="aac", fps=24)
                st.success("Video generated!")
                with open(video_tmp.name, "rb") as f:
                    st.download_button("Download Video", f, file_name="family_drama_video.mp4")

            # Clean up
            os.unlink(audio_file)
            os.unlink(music_tmp.name)
            os.unlink(video_tmp.name)

# YouTube metadata suggestions
st.subheader("YouTube Metadata Suggestions")
st.write("**Title**: Shocking Family Betrayal EXPOSED! Reddit Story")
st.write("**Description**: A jaw-dropping Reddit story of family lies! Names changed for privacy. Credit: u/Username (r/RelationshipAdvice).\nMusic: Pixabay (royalty-free)\nSubscribe for more drama! #FamilyDrama #RedditStories\nDisclaimer: Story adapted for entertainment; contact us to remove.")
st.write("**Tags**: family drama, Reddit story, betrayal story, AI narration")
