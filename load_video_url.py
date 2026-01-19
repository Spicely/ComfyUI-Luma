import os
import hashlib
import folder_paths
import torch
import numpy as np

try:
    import requests
except ImportError:
    requests = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import torchaudio
except ImportError:
    torchaudio = None

class LoadVideoByUrl:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "url": ("STRING", {"default": "", "multiline": True}),
                "frame_limit": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "start_frame": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "step": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "STRING", "FLOAT")
    RETURN_NAMES = ("images", "audio", "video_path", "fps")
    FUNCTION = "load_video"
    CATEGORY = "Luma"

    def load_video(self, url, frame_limit=0, start_frame=0, step=1):
        if requests is None:
            raise ImportError("requests library is not installed. Please install it using 'pip install requests'")
            
        if cv2 is None:
            raise ImportError("opencv-python library is not installed. Please install it using 'pip install opencv-python'")

        if not url or not url.startswith("http"):
             raise ValueError("Invalid URL provided")
             
        # Generate a unique filename based on the URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Try to extract extension from URL
        filename = os.path.basename(url.split("?")[0])
        _, ext = os.path.splitext(filename)
        
        # Default to .mp4 if no extension found
        if not ext:
            ext = ".mp4" 
            
        local_filename = f"url_video_{url_hash}{ext}"
        input_dir = folder_paths.get_input_directory()
        destination_path = os.path.join(input_dir, local_filename)
        
        # Download if file doesn't exist
        if not os.path.exists(destination_path):
            print(f"Downloading video from {url} to {destination_path}...")
            try:
                response = requests.get(url, stream=True, timeout=60)
                response.raise_for_status()
                
                with open(destination_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except Exception as e:
                # Clean up if download failed
                if os.path.exists(destination_path):
                    os.remove(destination_path)
                raise RuntimeError(f"Failed to download video: {str(e)}")
        
        # Load Video Frames
        cap = cv2.VideoCapture(destination_path)
        if not cap.isOpened():
             raise RuntimeError(f"Failed to open video file: {destination_path}")

        # Get FPS
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Handle frame skipping and limits
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate start and end frames
        start_frame = max(0, start_frame)
        if frame_limit > 0:
            end_frame = min(total_frames, start_frame + frame_limit * step)
        else:
            end_frame = total_frames

        images = []
        current_frame = 0
        frames_loaded = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if current_frame >= end_frame:
                break
                
            if current_frame >= start_frame and (current_frame - start_frame) % step == 0:
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Convert to numpy array and normalize to 0-1
                frame = frame.astype(np.float32) / 255.0
                # Extract tensor
                image_tensor = torch.from_numpy(frame)
                images.append(image_tensor)
                frames_loaded += 1
                
                # Check if we hit limit (if not using end_frame logic, but simpler here)
                if frame_limit > 0 and frames_loaded >= frame_limit:
                    break
            
            current_frame += 1
            
        cap.release()
        
        if not images:
             raise RuntimeError("No frames could be loaded from the video.")

        # Stack images into a batch [B, H, W, C]
        images_output = torch.stack(images)

        # Load Audio (Optional)
        audio_output = None
        if torchaudio is not None:
             try:
                 waveform, sample_rate = torchaudio.load(destination_path)
                 audio_output = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
             except Exception:
                 # It's okay if audio fails or doesn't exist, just return empty/None for audio
                 pass
        
        if audio_output is None:
             # Create a dummy silent audio
             audio_output = {"waveform": torch.zeros(1, 1, 0), "sample_rate": 44100}

        return (images_output, audio_output, destination_path, float(fps))

NODE_CLASS_MAPPINGS = {
    "LoadVideoByUrl": LoadVideoByUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadVideoByUrl": "Load Video By URL"
}
