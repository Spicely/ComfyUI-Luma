import os
import hashlib
import folder_paths

try:
    import requests
except ImportError:
    requests = None

class LoadVideoByUrl:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "url": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video",)
    FUNCTION = "load_video"
    CATEGORY = "Luma"

    def load_video(self, url):
        if requests is None:
            raise ImportError("requests library is not installed. Please install it using 'pip install requests'")
            
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
        
        # Return the absolute path as a string (compatible with SeparateVideoAudio and others)
        return (destination_path, )

NODE_CLASS_MAPPINGS = {
    "LoadVideoByUrl": LoadVideoByUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadVideoByUrl": "Load Video By URL"
}
