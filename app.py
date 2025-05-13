import streamlit as st
import re
import tempfile
import io
import numpy as np
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

# Set page title
st.title("Family Drama Video Maker")

# Function to split text into slides
def split_into_slides(text):
    # Remove tone/direction tags like [DRAMATIC TONE] and split by [PAUSE]
    clean_text = re.sub(r'\[.*?\]', '', text).strip()
    sentences = clean_text.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    slides = []
    current_slide = ""
    
    for sentence in sentences:
        if len(current_slide.split()) + len(sentence.split()) <= 20:
            current_slide += " " + sentence + "."
        else:
            if current_slide:
                slides.append(current_slide.strip() + ".")
            current_slide = sentence + "."
    if current_slide:
        slides.append(current_slide.strip() + ".")
    return slides

# Function to create a text slide image
def create_text_slide(text, width=1920, height=1080, color="white"):
    img = Image.new("RGB", (width, height), color="black")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()
    # Use font.getbbox to get text dimensions
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]  # Right - Left
    text_height = bbox[3] - bbox[1]  # Bottom - Top
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.text((x, y), text, fill=color, font=font)
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    return np.array(Image.open(img_buffer))

# Function to generate voiceover using gTTS
def generate_voiceover(text, voice):
    clean_text = re.sub(r'\[.*?\]', '', text).strip()
    tts = gTTS(text=clean_text, lang='en', slow=False)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tts.save(tmp.name)
        return tmp.name

# Streamlit form for user input
story_text = st.text_area("Story Text", height=300, placeholder="Paste your Reddit story script here...")
text_color = st.selectbox("Text Color", ["White", "Red"])
music_url = st.text_input("Background Music URL", placeholder="Paste a direct MP3 link (e.g., from Pixabay)")

# Set voice to default (gTTS uses a default voice)
voice = "default"

# Generate video when the button is clicked
if st.button("Generate Video"):
    if not story_text or not music_url:
        st.error("Please provide both story text and a background music URL!")
    else:
        with st.spinner("Generating video..."):
            # Split story into slides
            slides = split_into_slides(story_text)
            if not slides:
                st.error("No valid slides created. Please check your story text.")
                st.stop()

            # Generate voiceover for the full story
            narration_file = generate_voiceover(story_text, voice)
            if not narration_file:
                st.error("Failed to generate narration!")
                st.stop()

            # Create image slides
            slide_images = [create_text_slide(slide, color=text_color.lower()) for slide in slides]

            # Load narration audio
            narration_audio = AudioFileClip(narration_file)
            narration_duration = narration_audio.duration
            narration_audio.close()

            # Calculate duration per slide
            total_slides = len(slides)
            duration_per_slide = narration_duration / total_slides if total_slides > 0 else narration_duration

            # Create video clips for each slide
            clips = []
            for img in slide_images:
                clip = ImageSequenceClip([img], fps=24)
                clip = clip.set_duration(duration_per_slide)
                clips.append(clip)

            # Concatenate all clips into a single video
            video = concatenate_videoclips(clips, method="compose")

            # Add narration audio
            video = video.set_audio(AudioFileClip(narration_file))

            # Add background music
            try:
                bg_music = AudioFileClip(music_url)
                bg_music = bg_music.volumex(0.1)  # Reduce volume to 10%
                final_audio = bg_music.set_duration(video.duration)
                video = video.set_audio(final_audio)
            except Exception as e:
                st.warning(f"Could not add background music: {e}")

            # Save the final video
            output_path = "family_drama_video.mp4"
            video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

            # Provide download link
            with open(output_path, "rb") as file:
                st.download_button(
                    label="Download Video",
                    data=file,
                    file_name="family_drama_video.mp4",
                    mime="video/mp4"
                )

            st.success("Video generated successfully!")
