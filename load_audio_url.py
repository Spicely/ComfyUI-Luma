import os
import hashlib
import torch
import folder_paths

try:
    import requests
except ImportError:
    requests = None

try:
    import torchaudio
except ImportError:
    torchaudio = None

class LoadAudioByUrl:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "url": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "load_audio"
    CATEGORY = "Luma"

    def load_audio(self, url):
        if requests is None:
            raise ImportError("requests library is not installed. Please install it using 'pip install requests'")
        
        if torchaudio is None:
            raise ImportError("torchaudio library is not installed.")
            
        if not url or not url.startswith("http"):
             raise ValueError("Invalid URL provided")
             
        # Generate a unique filename based on the URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Try to extract extension from URL
        filename = os.path.basename(url.split("?")[0])
        _, ext = os.path.splitext(filename)
        
        # Map common content types if extension is missing (simplified)
        # For now, if no extension, default to .wav or let torchaudio handle it if possible, 
        # but torchaudio usually needs extension hint or valid header.
        if not ext:
            ext = ".wav" 
            
        local_filename = f"url_audio_{url_hash}{ext}"
        input_dir = folder_paths.get_input_directory()
        destination_path = os.path.join(input_dir, local_filename)
        
        # Download if file doesn't exist
        if not os.path.exists(destination_path):
            print(f"Downloading audio from {url} to {destination_path}...")
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                # Check header for extension if we defaulted? (Optional improvement)
                
                with open(destination_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except Exception as e:
                # Clean up if download failed
                if os.path.exists(destination_path):
                    os.remove(destination_path)
                raise RuntimeError(f"Failed to download audio: {str(e)}")
        
        try:
            # Load audio using torchaudio
            waveform, sample_rate = torchaudio.load(destination_path)
        except Exception as e:
             raise RuntimeError(f"Failed to load audio file {destination_path}: {str(e)}")
        
        # Convert to ComfyUI AUDIO format: {"waveform": [batch, channels, samples], "sample_rate": int}
        # torchaudio.load returns [channels, samples]
        audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
        
        return (audio, )

NODE_CLASS_MAPPINGS = {
    "LoadAudioByUrl": LoadAudioByUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadAudioByUrl": "Load Audio By URL"
}
