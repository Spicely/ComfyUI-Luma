import os
import json
import time
import random
import folder_paths
from typing import List, Dict, Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class Wav2Srt:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio_path": ("STRING", {"default": "", "multiline": False}),
                "api_url": ("STRING", {"default": "http://localhost:8080/v1/api/wav2SrtEntry", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")  # 返回JSON字符串、SRT文件路径和数组长度
    RETURN_NAMES = ("subtitles_json", "srt_file_path", "subtitles_count")
    FUNCTION = "wav2srt"
    CATEGORY = "Luma"

    def convert_time_to_srt_format(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def parse_time_to_seconds(self, time_str: str) -> float:
        """将时间字符串转换为秒数，支持多种格式"""
        if isinstance(time_str, (int, float)):
            return float(time_str)
        
        time_str = str(time_str).strip()
        
        # 尝试解析 ISO 格式 (HH:MM:SS.mmm 或 HH:MM:SS,mmm)
        if ':' in time_str:
            parts = time_str.replace(',', '.').split(':')
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        
        # 尝试直接解析为数字
        try:
            return float(time_str)
        except ValueError:
            return 0.0

    def subtitles_to_srt(self, subtitles: List[Dict[str, Any]], output_path: str):
        """将字幕数据转换为SRT格式文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for subtitle in subtitles:
                idx = subtitle.get("id", subtitle.get("ID", 0))
                start_time = subtitle.get("start", subtitle.get("Start", "00:00:00.000"))
                end_time = subtitle.get("end", subtitle.get("End", "00:00:00.000"))
                text = subtitle.get("text", subtitle.get("Text", ""))
                
                # 转换时间格式
                start_seconds = self.parse_time_to_seconds(start_time)
                end_seconds = self.parse_time_to_seconds(end_time)
                
                start_srt = self.convert_time_to_srt_format(start_seconds)
                end_srt = self.convert_time_to_srt_format(end_seconds)
                
                # 写入SRT格式
                f.write(f"{idx}\n")
                f.write(f"{start_srt} --> {end_srt}\n")
                f.write(f"{text}\n\n")

    def wav2srt_api(self, audio_path: str, api_url: str) -> List[Dict[str, Any]]:
        """通过API调用进行语音转字幕"""
        if not HAS_REQUESTS:
            raise RuntimeError("需要安装 requests 库: pip install requests")
        
        if not os.path.exists(audio_path):
            raise ValueError(f"音频文件不存在: {audio_path}")
        
        try:
            with open(audio_path, 'rb') as f:
                files = {'file': (os.path.basename(audio_path), f, 'audio/*')}
                response = requests.post(api_url, files=files, timeout=300)
                response.raise_for_status()
                
                result = response.json()
                
                # 处理API返回的数据格式
                # 假设API返回格式: {"code": 200, "data": [...]} 或直接是数组
                if isinstance(result, dict):
                    if "data" in result:
                        subtitles = result["data"]
                    elif "result" in result:
                        subtitles = result["result"]
                    else:
                        subtitles = result
                else:
                    subtitles = result
                
                # 确保返回的是列表格式
                if not isinstance(subtitles, list):
                    subtitles = [subtitles] if subtitles else []
                
                return subtitles
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API调用失败: {str(e)}")

    def wav2srt(self, audio_path: str, api_url: str):
        """主函数：语音转字幕"""
        if not audio_path or not os.path.exists(audio_path):
            raise ValueError(f"音频文件不存在: {audio_path}")
        
        # 调用API获取字幕
        subtitles = self.wav2srt_api(audio_path, api_url)
        
        # 转换为JSON字符串返回
        subtitles_json = json.dumps(subtitles, ensure_ascii=False, indent=2)
        
        # 获取数组长度
        subtitles_count = len(subtitles)
        
        # 生成SRT文件
        output_dir = folder_paths.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        timestamp = int(time.time() * 1000)
        random_suffix = random.randint(1000, 9999)
        srt_file_path = os.path.join(output_dir, f"{base_name}_subtitle_{timestamp}_{random_suffix}.srt")
        
        self.subtitles_to_srt(subtitles, srt_file_path)
        
        return (subtitles_json, srt_file_path, subtitles_count)


NODE_CLASS_MAPPINGS = {
    "Wav2Srt": Wav2Srt
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Wav2Srt": "Wav2Srt - Speech to Subtitle"
}

