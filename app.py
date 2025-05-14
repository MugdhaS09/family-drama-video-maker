import streamlit as st
import re
import tempfile
import io
import requests
import numpy as np
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips, TextClip
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Set page title
st.title("RedditTales Exposed Video Maker")

# Constants
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/"
CHANNEL_NAME = "RedditTales Exposed"
HEADLINE = "Sister’s Secret Betrayal Exposed!"
BACKGROUND_IMAGE_URL = "https://via.placeholder.com/1920x1080/000000.png"  # Placeholder; update with your black pixel image URL

# Function to download the background image
@st.cache_data
def download_background_image(url):
    response = requests.get(url)
    img = Image.open(io.BytesIO(response.content))
    return img.resize((1920, 1080))

# Function to create the start screen
def create_start_screen(width=1920, height=1080):
    # Download and use the background image
    bg_img = download_background_image(BACKGROUND_IMAGE_URL)
    img = bg_img.copy()
    draw = ImageDraw.Draw(img)
    
    # White box for channel name and headline
    box_width, box_height = 1000, 400
    box_x = (width - box_width) // 2
    box_y = (height - box_height) // 2
    draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height], fill="white")
    
    # Text setup
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    # Channel name
    channel_text = CHANNEL_NAME
    bbox = font.getbbox(channel_text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = box_x + (box_width - text_width) // 2
    text_y = box_y + 50
    draw.text((text_x, text_y), channel_text, fill="black", font=font)
    
    # Headline
    headline_text = HEADLINE
    bbox = font.getbbox(headline_text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = box_x + (box_width - text_width) // 2
    text_y = text_y + text_height + 20
    draw.text((text_x, text_y), headline_text, fill="black", font=font)
    
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    return np.array(Image.open(img_buffer))

# Function to split text into slides
def split_into_slides(text):
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

# Function to create a text slide with subtitles
def create_text_slide(text, width=1920, height=1080, color="white"):
    # Use the background image
    bg_img = download_background_image(BACKGROUND_IMAGE_URL)
    img = bg_img.copy()
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()
    
    # Center the text
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.text((x, y), text, fill=color, font=font)
    
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    return np.array(Image.open(img_buffer))

# Function to generate voiceover using ElevenLabs
def generate_voiceover(text, voice):
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": st.secrets["ELEVENLABS_API_KEY"]
    }
    data = {
        "text": re.sub(r'\[.*?\]', '', text).strip(),
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
    }
    voice_id = "EXAVITQu4vr4xnSDxMaL" if voice == "Rachel" else "pNInz6obpgDQGcFmaJgB"  # Rachel, Matthew
    response = requests.post(f"{ELEVENLABS_API_URL}{voice_id}", json=data, headers=headers)
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(response.content)
            return tmp.name
    else:
        st.error("Voiceover generation failed! Check logs for details.")
        return None

# Streamlit form for user input
story_text = st.text_area("Story Text", height=300, placeholder="Paste your Reddit story script here...")
voice = st.selectbox("Voice", ["Rachel", "Matthew"])
text_color = st.selectbox("Text Color", ["White", "Red"])
music_url = st.text_input("Background Music URL", placeholder="Paste a direct MP3 link (e.g., from Pixabay)")

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

            # Generate voiceover
            narration_file = generate_voiceover(story_text, voice)
            if not narration_file:
                st.stop()

            # Create start screen
            start_screen = create_start_screen()

            # Create image slides
            slide_images = [create_text_slide(slide, color=text_color.lower()) for slide in slides]

            # Load narration audio
            narration_audio = AudioFileClip(narration_file)
            narration_duration = narration_audio.duration

            # Calculate duration per slide
            total_slides = len(slides)
            duration_per_slide = narration_duration / total_slides if total_slides > 0 else narration_duration

            # --- Regular Video (1920x1080) ---
            clips = []
            # Add start screen (5 seconds)
            start_clip = ImageSequenceClip([start_screen], fps=24)
            start_clip = start_clip.set_duration(5)
            clips.append(start_clip)

            # Add story slides with subtitles
            for i, (img, slide_text) in enumerate(zip(slide_images, slides)):
                clip = ImageSequenceClip([img], fps=24)
                clip = clip.set_duration(duration_per_slide)
                # Add subtitle
                subtitle = TextClip(slide_text, fontsize=40, color=text_color.lower(), font="Arial", size=(1920, 1080), method='caption', align='south')
                subtitle = subtitle.set_duration(duration_per_slide).set_position(('center', 'bottom'))
                clip = clip.set_position('center').set_audio(None)
                clip_with_subtitle = concatenate_videoclips([clip, subtitle], method="compose")
                clips.append(clip_with_subtitle)

            # Concatenate all clips
            video = concatenate_videoclips(clips, method="compose")

            # Add narration audio
            video = video.set_audio(narration_audio)

            # Add background music
            try:
                bg_music = AudioFileClip(music_url)
                bg_music = bg_music.volumex(0.1).set_duration(video.duration)
                final_audio = bg_music
                video = video.set_audio(final_audio)
            except Exception as e:
                st.warning(f"Could not add background music: {e}")

            # Auto-name the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            regular_filename = f"sisters_secret_betrayal_exposed_regular_{timestamp}.mp4"

            # Save regular video
            video.write_videofile(regular_filename, fps=24, codec="libx264", audio_codec="aac")

            # --- Shorts Video (1080x1920, first 60 seconds) ---
            shorts_clips = []
            # Resize start screen for Shorts
            start_screen_resized = np.array(Image.fromarray(start_screen).resize((1080, 1920)))
            start_clip = ImageSequenceClip([start_screen_resized], fps=24).set_duration(5)
            shorts_clips.append(start_clip)

            # Use first few slides for Shorts (up to 60 seconds)
            shorts_duration = 0
            for i, (img, slide_text) in enumerate(zip(slide_images, slides)):
                if shorts_duration >= 55:  # Keep under 60 seconds
                    break
                clip = ImageSequenceClip([np.array(Image.fromarray(img).resize((1080, 1920)))], fps=24)
                clip = clip.set_duration(duration_per_slide)
                subtitle = TextClip(slide_text, fontsize=30, color=text_color.lower(), font="Arial", size=(1080, 1920), method='caption', align='south')
                subtitle = subtitle.set_duration(duration_per_slide).set_position(('center', 'bottom'))
                clip_with_subtitle = concatenate_videoclips([clip, subtitle], method="compose")
                shorts_clips.append(clip_with_subtitle)
                shorts_duration += duration_per_slide

            shorts_video = concatenate_videoclips(shorts_clips, method="compose")
            shorts_video = shorts_video.set_audio(narration_audio.set_duration(shorts_video.duration))

            # Add background music to Shorts
            try:
                bg_music = AudioFileClip(music_url)
                bg_music = bg_music.volumex(0.1).set_duration(shorts_video.duration)
                shorts_video = shorts_video.set_audio(bg_music)
            except Exception as e:
                st.warning(f"Could not add background music to Shorts: {e}")

            shorts_filename = f"sisters_secret_betrayal_exposed_shorts_{timestamp}.mp4"
            shorts_video.write_videofile(shorts_filename, fps=24, codec="libx264", audio_codec="aac")

            # Provide download links
            st.subheader("Download Files")
            
            # Narration MP3
            with open(narration_file, "rb") as file:
                st.download_button(
                    label="Download Narration (.mp3)",
                    data=file,
                    file_name=f"sisters_secret_betrayal_exposed_narration_{timestamp}.mp3",
                    mime="audio/mpeg"
                )

            # Regular Video
            with open(regular_filename, "rb") as file:
                st.download_button(
                    label="Download Regular Video (.mp4)",
                    data=file,
                    file_name=regular_filename,
                    mime="video/mp4"
                )

            # Shorts Video
            with open(shorts_filename, "rb") as file:
                st.download_button(
                    label="Download Shorts Video (.mp4)",
                    data=file,
                    file_name=shorts_filename,
                    mime="video/mp4"
                )

            st.success("Videos generated successfully!")
