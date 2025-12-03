import torch

class GetDeviceType:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {}
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("device_type",)
    FUNCTION = "get_device_type"
    CATEGORY = "Luma"

    def get_device_type(self):
        if torch.cuda.is_available():
            device_type = "cuda"
        else:
            device_type = "cpu"
        return (device_type,)

NODE_CLASS_MAPPINGS = {
    "GetDeviceType": GetDeviceType
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GetDeviceType": "Get Device Type"
}

