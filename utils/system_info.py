"""
System info — detect OS, Python version, GPU/VRAM, RAM, and scan time estimation.
Used for diagnostics, time estimates, and adaptive configuration.
"""
import platform
import re
import subprocess
import sys
import shutil
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


def get_system_info() -> dict:
    """
    Collect system information including OS, Python version,
    available disk space, memory, and GPU details.
    """
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "cpu_cores": _get_cpu_cores(),
    }

    # Available disk space on home directory
    try:
        usage = shutil.disk_usage(Path.home())
        info["disk_free_gb"] = round(usage.free / (1024 ** 3), 2)
        info["disk_total_gb"] = round(usage.total / (1024 ** 3), 2)
    except Exception:
        info["disk_free_gb"] = None
        info["disk_total_gb"] = None

    # RAM
    ram = _get_ram_gb()
    info["ram_total_gb"] = ram

    # GPU
    gpu_info = _detect_gpu()
    info["gpu_name"] = gpu_info["name"]
    info["gpu_vram_gb"] = gpu_info["vram_gb"]

    return info


def _get_cpu_cores() -> int:
    """Return the number of logical CPU cores."""
    import os
    return os.cpu_count() or 1


def _get_ram_gb() -> float | None:
    """Return total system RAM in GB."""
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        # Fallback for Windows
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["wmic", "computersystem", "get", "totalphysicalmemory"],
                    capture_output=True, text=True, timeout=5,
                )
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if line.isdigit():
                        return round(int(line) / (1024 ** 3), 1)
            except Exception:
                pass
        return None


def _detect_gpu() -> dict:
    """
    Detect NVIDIA GPU name and VRAM using nvidia-smi.
    Returns {"name": str|None, "vram_gb": float|None}.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            name = parts[0].strip()
            vram_mb = float(parts[1].strip()) if len(parts) > 1 else 0
            vram_gb = round(vram_mb / 1024, 1)
            return {"name": name, "vram_gb": vram_gb}
    except Exception:
        pass
    return {"name": None, "vram_gb": None}


def get_python_version_tuple() -> tuple:
    """Return Python version as a tuple (major, minor, micro)."""
    return sys.version_info[:3]


def is_gpu_available() -> bool:
    """Check if an NVIDIA GPU is available via nvidia-smi."""
    info = _detect_gpu()
    return info["name"] is not None


# ─── Time Estimation ────────────────────────────────────────────────────────

def _parse_model_size(model_name: str) -> float:
    """
    Extract the model size in billions from the model name string.
    e.g. "qwen2.5-coder:7b" → 7.0, "llama3:latest" → 8.0
    """
    # Match patterns like "7b", "13b", "32b", "6.7b"
    match = re.search(r'(\d+\.?\d*)\s*[bB]', model_name)
    if match:
        return float(match.group(1))
    # Common model defaults when size isn't in the name
    name_lower = model_name.lower()
    if "llama3" in name_lower or "llama-3" in name_lower:
        return 8.0
    if "llama2" in name_lower:
        return 7.0
    if "mistral" in name_lower:
        return 7.0
    if "phi" in name_lower:
        return 3.8
    # Default assumption
    return 7.0


def _model_size_factor(size_b: float) -> float:
    """Return a speed multiplier based on model size."""
    if size_b <= 8:
        return 1.0
    elif size_b <= 14:
        return 2.0
    elif size_b <= 34:
        return 4.0
    else:
        return 6.0


def estimate_scan_time(
    file_count: int,
    model_name: str,
    gpu_vram_gb: float | None,
    avg_file_chars: int = 3000,
) -> dict:
    """
    Estimate total scan time based on file count, model size, and hardware.

    Returns dict with:
      - hardware: str description of detected hardware
      - per_file_s: (min, max) seconds per LLM call
      - total_s: (min, max) total estimated seconds
      - total_human: human-readable string
      - model_size_b: detected model size
    """
    model_size = _parse_model_size(model_name)
    size_factor = _model_size_factor(model_size)

    # Base per-LLM-call time in seconds based on hardware
    if gpu_vram_gb and gpu_vram_gb >= 8:
        base_min, base_max = 20, 45
        hardware = f"GPU ({gpu_vram_gb:.0f}GB VRAM)"
    elif gpu_vram_gb and gpu_vram_gb >= 4:
        base_min, base_max = 60, 120
        hardware = f"GPU ({gpu_vram_gb:.0f}GB VRAM)"
    else:
        base_min, base_max = 150, 300
        hardware = "CPU-only mode"

    per_call_min = base_min * size_factor
    per_call_max = base_max * size_factor

    # Chunking: files > 8000 chars get split into multiple LLM calls
    CHUNK_SIZE = 8000
    chunks_per_file = max(1, avg_file_chars // CHUNK_SIZE)

    # Retries: ~50% of chunks may need one retry
    retry_factor = 1.5

    total_calls = file_count * chunks_per_file * retry_factor
    total_min = per_call_min * total_calls
    total_max = per_call_max * total_calls

    return {
        "hardware": hardware,
        "per_file_s": (per_call_min, per_call_max),
        "total_s": (total_min, total_max),
        "total_human": _format_time_range(total_min, total_max),
        "model_size_b": model_size,
    }


def _format_time_range(min_s: float, max_s: float) -> str:
    """Format a time range into a human-readable string."""
    def fmt(s: float) -> str:
        if s < 60:
            return f"{int(s)}s"
        elif s < 3600:
            m = int(s // 60)
            r = int(s % 60)
            return f"{m}m {r}s" if r else f"{m}m"
        else:
            h = int(s // 3600)
            m = int((s % 3600) // 60)
            return f"{h}h {m}m"
    return f"~{fmt(min_s)} — {fmt(max_s)}"


def format_eta(elapsed_s: float, current: int, total: int) -> str:
    """Calculate and format ETA based on elapsed time and progress."""
    if current == 0:
        return "calculating..."
    avg_per_file = elapsed_s / current
    remaining = (total - current) * avg_per_file
    if remaining < 60:
        return f"~{int(remaining)}s"
    elif remaining < 3600:
        m = int(remaining // 60)
        s = int(remaining % 60)
        return f"~{m}m {s}s"
    else:
        h = int(remaining // 3600)
        m = int((remaining % 3600) // 60)
        return f"~{h}h {m}m"
