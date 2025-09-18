import os
import torch
import random
import numpy as np
import gradio as gr
from pydub import AudioSegment
from src.translate.translate import TranscriptTranslator
from src.tts.tts import TextToSpeech
from src.utils.swap_audio import swap_audio
from src.utils.burn_subtitles import burn_subtitles

from lipsync import LipSync

import warnings

# Suppress specific torchaudio warnings
warnings.filterwarnings(
    "ignore",
    message=".*TorchCodec.*",
    category=UserWarning,
    module="torchaudio"
)

def set_seed(seed: int = 0):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def process_video(subtitles, translation_type, lipsync_model, padding, resize_factor, seed, video, transcript, progress=gr.Progress()):

    # Set seed for reproducibility
    set_seed(seed)

    # Set device
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Create temp folder for intermediate saving and final output
    os.makedirs('temp', exist_ok=True)

    # Translate transcript
    print('Translating EN transcript to DE.')
    progress(0, desc="Translating transcript...")
    translator = TranscriptTranslator(device)
    de_srt = translator.translate_srt(transcript)

    # Get audio from input video
    print('Splitting audio and video tracks.')
    progress(0.1, desc="Splitting audio and video tracks...")
    en_audio = 'temp/en_audio.wav'
    audio = AudioSegment.from_file(video)
    audio.export(en_audio, format="wav") # creates temp audio file

    # Generate audio from translated transcript
    print('Generating new audio in DE. Fighting hallucinations, aligning the timing...')
    progress(0.2, desc="Generating new audio…")
    tts = TextToSpeech(device=device)
    tts.set_voice(en_audio)
    de_audio, de_srt = tts.srt_to_audio(subs=de_srt) # creates temp audio file

    # Swap video with new audio
    print('Swapping the audio sources in the video.')
    progress(0.3, desc="Swapping audio source in the video...")
    swapped_mp4 = swap_audio(video, de_audio, translation_type) # creates temp mp4 file

    # Burn in subtitles, if requested
    if subtitles:
        print('Burning in subtitles.')
        progress(0.4, desc="Burning in subtitles...")
        swapped_mp4 = burn_subtitles(swapped_mp4, de_srt)

    output_mp4 = 'temp/output.mp4'
    if translation_type == 'LipSync':
        # Synchronize lips with new audio
        print('Synchronizing the lip movements.')
        progress(0.6, desc="Synchronizing the lip movements...")
        lip = LipSync(
            model='wav2lip',
            checkpoint_path=f'weights/{lipsync_model.lower()}.pth',
            img_size=96,
            pads=[int(x.strip()) for x in padding.split(",")],
            resize_factor=resize_factor,
            nosmooth=False,
            device=device,
            cache_dir='cache/',
            save_cache=False
        )
        lip.sync(
            swapped_mp4,
            de_audio,
            output_mp4,
        )
    else:
        os.rename(swapped_mp4, output_mp4)

    # Clean up temp folder except for outputs
    keep_files = [de_audio, output_mp4, de_srt]
    for fname in os.listdir('temp'):
        fpath = os.path.join('temp', fname)
        if fpath not in keep_files:
            try:
                os.remove(fpath)
            except Exception as e:
                print(f"Failed to remove {fpath}: {e}")

    print('Done.')
    progress(1.0, desc="Done!")

    return output_mp4, de_audio, de_srt

with gr.Blocks() as demo:
    gr.Markdown("# English to German Video Translation")

    gr.Markdown("### Upload Video and Original Transcript")
    with gr.Row():
        video = gr.File(label="Upload Video", file_types=[".mp4"])
        transcript = gr.File(label="Upload Transcript", file_types=[".srt"])

    gr.Markdown("### Subtitle, Translation, Audio Speed Settings")
    with gr.Row(variant='panel'):
        subtitles = gr.Checkbox(value=1, label='Subtitles Off/On')
        translation_type = gr.Dropdown(["Dub", "LipSync"], label="Translation Type")
        seed = gr.Slider(
                0, 100, value=0, step=1, 
                label="Random Seed"
            )

    gr.Markdown("### Advanced Settings (LipSync)")
    with gr.Accordion("LipSync Settings", open=False):  # closed by default
        with gr.Row(variant='panel'):
            lipsync_model = gr.Dropdown(
                ["Wav2Lip", "Wav2Lip_GAN"], 
                label="LipSync Model"
            )
            padding = gr.Textbox(
                value="0,30,0,0", 
                label="Lip Padding (top,bottom,left,right)"
            )
            resize_factor = gr.Slider(
                1, 4, value=1, step=1, 
                label="Processing Resize Factor"
            )

    btn = gr.Button("Run Translation", variant='huggingface')
    
    with gr.Row():
        with gr.Column(scale=2):  # Left column (wider)
            output_mp4 = gr.Video(label="Video Preview")
        with gr.Column(scale=1):  # Right column (narrower)
            output_wav = gr.File(label="Download Audio")
            output_srt = gr.File(label="Download Transcript")

    btn.click(process_video, [subtitles, translation_type, lipsync_model, padding, resize_factor, seed, video, transcript], [output_mp4, output_wav, output_srt])

demo.launch(share=True)