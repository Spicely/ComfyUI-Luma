import os
import hashlib
import folder_paths
import torch
import numpy as np
from PIL import Image, ImageOps

try:
    import requests
except ImportError:
    requests = None

class LoadImageByUrl:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "url": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "load_image"
    CATEGORY = "Luma"

    def load_image(self, url):
        if requests is None:
            raise ImportError("requests library is not installed. Please install it using 'pip install requests'")

        if not url or not url.startswith("http"):
             raise ValueError("Invalid URL provided")
             
        # Generate a unique filename based on the URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Try to extract extension from URL, default to .png if none or weird
        filename = os.path.basename(url.split("?")[0])
        _, ext = os.path.splitext(filename)
        if not ext.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']:
            ext = ".png"
            
        local_filename = f"url_image_{url_hash}{ext}"
        input_dir = folder_paths.get_input_directory()
        destination_path = os.path.join(input_dir, local_filename)
        
        # Download if file doesn't exist
        if not os.path.exists(destination_path):
            print(f"Downloading image from {url} to {destination_path}...")
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
                raise RuntimeError(f"Failed to download image: {str(e)}")
        
        # Load Image
        try:
            img = Image.open(destination_path)
            img = ImageOps.exif_transpose(img)
            
            # Convert to RGB to ensure consistency
            if img.mode == 'I':
                img = img.point(lambda i: i * (1 / 256)).convert('L')
                
            image = img.convert("RGB")
            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            
            # Handle Mask
            if 'A' in img.getbands():
                mask = np.array(img.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
                
            return (image, mask)
            
        except Exception as e:
             raise RuntimeError(f"Failed to load image from {destination_path}: {str(e)}")

NODE_CLASS_MAPPINGS = {
    "LoadImageByUrl": LoadImageByUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageByUrl": "Load Image By URL"
}
