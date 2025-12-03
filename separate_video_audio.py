import subprocess
import os
import folder_paths
import time
import random
import shutil

class SeparateVideoAudio:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_path": ("STRING", {"default": "", "multiline": False}),
                "audio_format": (["mp3", "aac", "wav", "flac", "m4a"], {"default": "mp3"}),
                "video_codec": (["copy", "libx264", "h264_nvenc", "h264_videotoolbox"], {"default": "copy"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("video_path", "audio_path")
    FUNCTION = "separate"
    CATEGORY = "Luma"

    @staticmethod
    def find_ffmpeg():
        """查找ffmpeg可执行文件的路径"""
        # 首先尝试使用shutil.which（会检查PATH）
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path
        
        # 如果找不到，尝试常见的安装路径
        common_paths = [
            "/opt/homebrew/bin/ffmpeg",  # macOS Homebrew (Apple Silicon)
            "/usr/local/bin/ffmpeg",     # macOS Homebrew (Intel) / Linux
            "/usr/bin/ffmpeg",           # Linux系统路径
            "C:\\ffmpeg\\bin\\ffmpeg.exe",  # Windows常见路径
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",  # Windows另一个常见路径
        ]
        
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        
        return None

    def separate(self, video_path, audio_format, video_codec):
        if not video_path or not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")

        # 查找ffmpeg路径
        ffmpeg_path = self.find_ffmpeg()
        if not ffmpeg_path:
            raise RuntimeError("未找到 ffmpeg，请确保已安装 FFmpeg。常见路径: /opt/homebrew/bin/ffmpeg (macOS), /usr/local/bin/ffmpeg, /usr/bin/ffmpeg")

        # 获取输出目录
        output_dir = folder_paths.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名，添加时间戳和随机值确保唯一性
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳
        random_suffix = random.randint(1000, 9999)  # 4位随机数
        
        # 输出文件路径
        video_output_path = os.path.join(output_dir, f"{base_name}_video_{timestamp}_{random_suffix}.mp4")
        audio_output_path = os.path.join(output_dir, f"{base_name}_audio_{timestamp}_{random_suffix}.{audio_format}")

        # 分离音频
        audio_codec = self._get_audio_codec(audio_format)
        audio_cmd = [
            ffmpeg_path,
            "-i", video_path,
            "-vn",  # 不包含视频
            "-acodec", audio_codec,
            "-y",  # 覆盖输出文件
            audio_output_path
        ]
        
        # 添加音频格式特定参数
        if audio_format == "mp3":
            audio_cmd.extend(["-b:a", "192k"])
        elif audio_format == "aac" or audio_format == "m4a":
            audio_cmd.extend(["-b:a", "192k"])
        # WAV和FLAC不需要额外的比特率参数

        # 分离视频（移除音频轨道）
        video_cmd = [
            ffmpeg_path,
            "-i", video_path,
            "-an",  # 不包含音频
            "-c:v", video_codec,
            "-y",  # 覆盖输出文件
            video_output_path
        ]
        
        # 如果视频编码器不是copy，添加编码参数
        if video_codec != "copy":
            if video_codec == "libx264":
                video_cmd.extend(["-preset", "medium", "-crf", "23"])
            elif video_codec == "h264_nvenc":
                video_cmd.extend(["-preset", "p4", "-rc", "vbr", "-cq", "23", "-b:v", "0"])
            elif video_codec == "h264_videotoolbox":
                video_cmd.extend(["-allow_sw", "1", "-b:v", "5000k", "-realtime", "1"])
            
            video_cmd.extend(["-pix_fmt", "yuv420p"])

        try:
            # 执行分离音频命令
            result_audio = subprocess.run(
                audio_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy()
            )
            
            # 执行分离视频命令
            result_video = subprocess.run(
                video_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy()
            )
            
            # 验证输出文件
            if not os.path.exists(audio_output_path) or os.path.getsize(audio_output_path) == 0:
                raise RuntimeError(f"音频文件生成失败: {audio_output_path}")
            
            if not os.path.exists(video_output_path) or os.path.getsize(video_output_path) == 0:
                raise RuntimeError(f"视频文件生成失败: {video_output_path}")
            
            return (video_output_path, audio_output_path)
                
        except subprocess.CalledProcessError as e:
            error_output = e.stderr if e.stderr else e.stdout
            error_msg = f"FFmpeg 执行失败:\n命令: {' '.join(e.cmd if hasattr(e, 'cmd') else audio_cmd)}\n错误: {error_output}"
            raise RuntimeError(error_msg)
        except FileNotFoundError:
            raise RuntimeError(f"未找到 ffmpeg 可执行文件。已尝试路径: {ffmpeg_path}")

    @staticmethod
    def _get_audio_codec(audio_format):
        """根据音频格式返回对应的编码器"""
        codec_map = {
            "mp3": "libmp3lame",
            "aac": "aac",
            "wav": "pcm_s16le",
            "flac": "flac",
            "m4a": "aac"
        }
        return codec_map.get(audio_format, "libmp3lame")

NODE_CLASS_MAPPINGS = {
    "SeparateVideoAudio": SeparateVideoAudio
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SeparateVideoAudio": "Separate Video Audio"
}

