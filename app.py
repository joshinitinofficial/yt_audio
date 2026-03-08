import os
import shutil
import tempfile
from pathlib import Path

import ffmpeg
import streamlit as st


def ffmpeg_installed() -> bool:
    return shutil.which("ffmpeg") is not None


def process_video(input_video_path: str, output_video_path: str) -> None:
    temp_audio = str(Path(output_video_path).with_name("temp_audio.wav"))
    processed_audio = str(Path(output_video_path).with_name("processed_audio.wav"))

    audio_filters = (
        "equalizer=f=90:width_type=h:width=150:g=9,"
        "equalizer=f=250:width_type=h:width=300:g=4,"
        "equalizer=f=6000:width_type=h:width=4000:g=6,"
        "acompressor=threshold=-20dB:ratio=4:attack=200:release=1000,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        "alimiter=limit=-1dB"
    )

    (
        ffmpeg.input(input_video_path)
        .output(temp_audio, acodec="pcm_s16le", ac=2, ar="44100")
        .run(overwrite_output=True)
    )

    (
        ffmpeg.input(temp_audio)
        .output(processed_audio, af=audio_filters)
        .run(overwrite_output=True)
    )

    video_stream = ffmpeg.input(input_video_path)
    audio_stream = ffmpeg.input(processed_audio)

    (
        ffmpeg.output(
            video_stream.video,
            audio_stream.audio,
            output_video_path,
            vcodec="copy",
            acodec="aac",
            strict="experimental",
        ).run(overwrite_output=True)
    )

    if os.path.exists(temp_audio):
        os.remove(temp_audio)
    if os.path.exists(processed_audio):
        os.remove(processed_audio)


st.set_page_config(page_title="Video Audio Enhancer", page_icon="🎬", layout="centered")
st.title("Video Audio Enhancer")
st.write("Upload a raw video, process it, and download the final output.")

if not ffmpeg_installed():
    st.error("FFmpeg executable not found on your system PATH.")
    st.markdown(
        "Install FFmpeg (system binary), then restart terminal/IDE and run app again.\n\n"
        "Windows quick option:\n"
        "- `winget install Gyan.FFmpeg`"
    )
    st.stop()

uploaded_video = st.file_uploader(
    "Upload your raw video",
    type=["mp4", "mov", "mkv", "avi", "webm"],
)

if uploaded_video is not None:
    st.video(uploaded_video)

    if st.button("Process Video", type="primary"):
        temp_dir = tempfile.mkdtemp(prefix="video_app_")
        try:
            input_path = os.path.join(temp_dir, uploaded_video.name)
            output_name = f"final_{Path(uploaded_video.name).stem}.mp4"
            output_path = os.path.join(temp_dir, output_name)

            with open(input_path, "wb") as f:
                f.write(uploaded_video.getbuffer())

            with st.spinner("Processing video. This may take a few minutes..."):
                process_video(input_path, output_path)

            with open(output_path, "rb") as f:
                output_bytes = f.read()

            st.success("Processing complete.")
            st.download_button(
                label="Download Final Video",
                data=output_bytes,
                file_name=output_name,
                mime="video/mp4",
            )
        except ffmpeg.Error as e:
            error_message = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            st.error("FFmpeg processing failed.")
            st.code(error_message)
        except FileNotFoundError as e:
            if "ffmpeg" in str(e).lower():
                st.error("FFmpeg executable not found. Install FFmpeg and ensure it is in PATH.")
                st.code("winget install Gyan.FFmpeg")
            else:
                st.error(f"File not found: {e}")
        except Exception as e:  # noqa: BLE001
            st.error(f"Unexpected error: {e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
