import subprocess
import os
import folder_paths
import time
import random

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
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_video_path",)
    FUNCTION = "add_text_watermark"
    CATEGORY = "Luma"

    def add_text_watermark(self, video_path, watermark_text, position, margin_x, margin_y, font_size, font_color):
        if not video_path or not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")
        
        if not watermark_text:
            raise ValueError("水印文本不能为空")

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
        
        # 构建 ffmpeg 命令 - 添加更多编码参数确保兼容性
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", drawtext_filter,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",  # 确保兼容性，大多数播放器都支持
            "-movflags", "+faststart",  # 优化流媒体播放，允许边下载边播放
            "-c:a", "aac",  # 使用 aac 编码音频，确保兼容性
            "-b:a", "192k",
            "-avoid_negative_ts", "make_zero",  # 处理时间戳问题
            "-y",  # 覆盖输出文件
            output_path
        ]
        
        try:
            # 执行 ffmpeg 命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
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
            raise RuntimeError("未找到 ffmpeg，请确保已安装 FFmpeg 并添加到系统 PATH")

NODE_CLASS_MAPPINGS = {
    "AddVideoTextWatermark": AddVideoTextWatermark
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AddVideoTextWatermark": "Add Video Text Watermark"
}

