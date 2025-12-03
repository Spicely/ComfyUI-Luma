import subprocess
import os
import folder_paths
import time
import random
import platform
import shutil

class AddVideoTextWatermark:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_path": ("STRING", {"default": "", "multiline": False}),
                "watermark_text": ("STRING", {"default": "Watermark", "multiline": False}),
                "position": (["top-left", "top-right", "bottom-left", "bottom-right", "center"], {"default": "bottom-right"}),
                "margin_x": ("INT", {"default": 10, "min": 0, "max": 1000}),
                "margin_y": ("INT", {"default": 10, "min": 0, "max": 1000}),
                "font_size": ("INT", {"default": 24, "min": 10, "max": 200}),
                "font_color": ("STRING", {"default": "white", "multiline": False}),
                "use_gpu": (["cpu", "gpu"], {"default": "cpu"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_video_path",)
    FUNCTION = "add_text_watermark"
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

    @staticmethod
    def detect_available_encoders(ffmpeg_path):
        """检测系统可用的硬件编码器"""
        available_encoders = {
            "cpu": "libx264",  # 默认CPU编码器
            "nvenc": None,
            "videotoolbox": None,
            "qsv": None,
            "amf": None
        }
        
        if not ffmpeg_path:
            return available_encoders
        
        try:
            # 检查FFmpeg是否可用
            result = subprocess.run(
                [ffmpeg_path, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5,
                env=os.environ.copy()
            )
            
            encoders_output = result.stdout + result.stderr
            
            # 检测NVIDIA NVENC
            if "h264_nvenc" in encoders_output:
                available_encoders["nvenc"] = "h264_nvenc"
            
            # 检测Apple VideoToolbox (macOS)
            if platform.system() == "Darwin" and "h264_videotoolbox" in encoders_output:
                available_encoders["videotoolbox"] = "h264_videotoolbox"
            
            # 检测Intel Quick Sync Video
            if "h264_qsv" in encoders_output:
                available_encoders["qsv"] = "h264_qsv"
            
            # 检测AMD AMF
            if "h264_amf" in encoders_output:
                available_encoders["amf"] = "h264_amf"
                
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        
        return available_encoders

    @staticmethod
    def get_encoder_config(use_gpu, available_encoders):
        """根据选择获取编码器配置"""
        if use_gpu == "cpu":
            return {
                "encoder": "libx264",
                "preset": "medium",
                "crf": "23",
                "extra_args": []
            }
        
        # GPU模式：按优先级选择硬件编码器
        if available_encoders["nvenc"]:
            return {
                "encoder": "h264_nvenc",
                "preset": "p4",  # NVENC预设：p1-p7 (p4是平衡质量和速度)
                "crf": None,
                "extra_args": ["-rc", "vbr", "-cq", "23", "-b:v", "0"]  # NVENC使用CQ而不是CRF
            }
        elif available_encoders["videotoolbox"]:
            return {
                "encoder": "h264_videotoolbox",
                "preset": None,
                "crf": None,
                "extra_args": ["-allow_sw", "1", "-b:v", "5000k", "-realtime", "1"]
            }
        elif available_encoders["qsv"]:
            return {
                "encoder": "h264_qsv",
                "preset": "medium",
                "crf": "23",
                "extra_args": []
            }
        elif available_encoders["amf"]:
            return {
                "encoder": "h264_amf",
                "preset": "balanced",
                "crf": None,
                "extra_args": ["-quality", "balanced", "-rc", "vbr_peak", "-qmin", "18", "-qmax", "28"]
            }
        else:
            # 如果没有可用的硬件编码器，回退到CPU
            return {
                "encoder": "libx264",
                "preset": "medium",
                "crf": "23",
                "extra_args": []
            }

    def add_text_watermark(self, video_path, watermark_text, position, margin_x, margin_y, font_size, font_color, use_gpu):
        if not video_path or not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")
        
        if not watermark_text:
            raise ValueError("水印文本不能为空")

        # 查找ffmpeg路径
        ffmpeg_path = self.find_ffmpeg()
        if not ffmpeg_path:
            raise RuntimeError("未找到 ffmpeg，请确保已安装 FFmpeg。常见路径: /opt/homebrew/bin/ffmpeg (macOS), /usr/local/bin/ffmpeg, /usr/bin/ffmpeg")
        
        # 检测可用的编码器
        available_encoders = self.detect_available_encoders(ffmpeg_path)
        
        # 获取编码器配置
        encoder_config = self.get_encoder_config(use_gpu, available_encoders)
        
        # 如果选择GPU但没有可用硬件编码器，给出警告但继续使用CPU
        if use_gpu == "gpu" and encoder_config["encoder"] == "libx264":
            print("警告: 未检测到可用的GPU硬件编码器，将使用CPU编码")

        # 获取输出目录
        output_dir = folder_paths.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名，添加时间戳和随机值确保唯一性
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳
        random_suffix = random.randint(1000, 9999)  # 4位随机数
        output_path = os.path.join(output_dir, f"{base_name}_watermarked_{timestamp}_{random_suffix}.mp4")
        
        # 构建 ffmpeg drawtext 位置参数
        position_map = {
            "top-left": f"x={margin_x}:y={margin_y}",
            "top-right": f"x=w-tw-{margin_x}:y={margin_y}",
            "bottom-left": f"x={margin_x}:y=h-th-{margin_y}",
            "bottom-right": f"x=w-tw-{margin_x}:y=h-th-{margin_y}",
            "center": f"x=(w-tw)/2:y=(h-th)/2"
        }
        text_position = position_map.get(position, position_map["bottom-right"])
        
        # 转义文本中的特殊字符 - ffmpeg drawtext 需要转义的特殊字符
        # 转义顺序很重要：先转义反斜杠，再转义其他字符
        escaped_text = (watermark_text
                       .replace("\\", "\\\\")  # 先转义反斜杠
                       .replace("'", "\\'")   # 转义单引号
                       .replace(":", "\\:")   # 转义冒号
                       .replace("[", "\\[")    # 转义左方括号
                       .replace("]", "\\]")    # 转义右方括号
                       .replace("=", "\\=")    # 转义等号
                       .replace("%", "\\%"))   # 转义百分号
        
        # 构建 drawtext 滤镜参数
        # 使用单引号包裹文本，确保特殊字符被正确处理
        drawtext_filter = f"drawtext=text='{escaped_text}':{text_position}:fontsize={font_size}:fontcolor={font_color}"
        
        # 构建 ffmpeg 命令
        cmd = [
            ffmpeg_path,
            "-i", video_path,
            "-vf", drawtext_filter,
            "-c:v", encoder_config["encoder"],
        ]
        
        # 添加编码器特定参数
        if encoder_config["preset"]:
            cmd.extend(["-preset", encoder_config["preset"]])
        
        if encoder_config["crf"]:
            cmd.extend(["-crf", encoder_config["crf"]])
        
        # 添加额外参数
        cmd.extend(encoder_config["extra_args"])
        
        # 添加通用参数
        cmd.extend([
            "-pix_fmt", "yuv420p",  # 确保兼容性，大多数播放器都支持
            "-movflags", "+faststart",  # 优化流媒体播放，允许边下载边播放
            "-c:a", "aac",  # 使用 aac 编码音频，确保兼容性
            "-b:a", "192k",
            "-avoid_negative_ts", "make_zero",  # 处理时间戳问题
            "-y",  # 覆盖输出文件
            output_path
        ])
        
        try:
            # 执行 ffmpeg 命令，确保使用正确的环境变量
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy()
            )
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return (output_path,)
            else:
                raise RuntimeError(f"FFmpeg 执行成功但输出文件不存在或为空: {output_path}")
                
        except subprocess.CalledProcessError as e:
            error_output = e.stderr if e.stderr else e.stdout
            error_msg = f"FFmpeg 执行失败:\n命令: {' '.join(cmd)}\n错误: {error_output}"
            raise RuntimeError(error_msg)
        except FileNotFoundError:
            raise RuntimeError(f"未找到 ffmpeg 可执行文件。已尝试路径: {ffmpeg_path}")

NODE_CLASS_MAPPINGS = {
    "AddVideoTextWatermark": AddVideoTextWatermark
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AddVideoTextWatermark": "Add Video Text Watermark"
}

