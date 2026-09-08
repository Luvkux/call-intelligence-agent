import os
import sys
import glob
import shutil
import subprocess
from typing import Optional
from pathlib import Path
import imageio_ffmpeg
import config


def verify_ffmpeg_executable(binary_path: str) -> bool:
    """
    Verifies that a given executable path exists and can execute 'ffmpeg -version'.
    """
    if not binary_path or not os.path.isfile(binary_path):
        return False
    
    try:
        res = subprocess.run(
            [binary_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return res.returncode == 0 and "ffmpeg" in res.stdout.lower()
    except Exception:
        return False

def find_ffmpeg_executable() -> Optional[str]:
    """
    Finds a valid ffmpeg executable using multiple strategies:
    1. Configured environment variable FFMPEG_PATH or config.FFMPEG_PATH.
    2. FFmpeg bundled with imageio-ffmpeg.
    3. System PATH via shutil.which("ffmpeg").
    4. Local project bin/ffmpeg.exe.
    5. Windows WinGet package directory.
    6. Windows User Registry PATH.

    Returns the absolute path to a valid FFmpeg executable,
    or None if FFmpeg cannot be found.
    """

    # 1. Check FFMPEG_PATH environment variable / config
    env_ffmpeg = os.getenv("FFMPEG_PATH") or getattr(config, "FFMPEG_PATH", "")

    if env_ffmpeg and verify_ffmpeg_executable(env_ffmpeg):
        bin_dir = os.path.dirname(os.path.abspath(env_ffmpeg))

        if bin_dir not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + bin_dir

        return os.path.abspath(env_ffmpeg)

    # 2. Check FFmpeg bundled with imageio-ffmpeg
    try:
        import imageio_ffmpeg

        bundled_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        if bundled_ffmpeg and verify_ffmpeg_executable(bundled_ffmpeg):
            bin_dir = os.path.dirname(os.path.abspath(bundled_ffmpeg))

            if bin_dir not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + bin_dir

            return os.path.abspath(bundled_ffmpeg)

    except Exception:
        pass

    # 3. Check system PATH via shutil.which
    which_ffmpeg = shutil.which("ffmpeg")

    if which_ffmpeg and verify_ffmpeg_executable(which_ffmpeg):
        return os.path.abspath(which_ffmpeg)

    # 4. Check local project bin directory
    project_root = Path(__file__).resolve().parent.parent.parent

    local_bin = project_root / "bin" / (
        "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    )

    if local_bin.exists() and verify_ffmpeg_executable(str(local_bin)):
        bin_dir = str(local_bin.parent)

        if bin_dir not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + bin_dir

        return str(local_bin)

    # 5. Windows specific: Search WinGet Packages directory
    if sys.platform == "win32":

        local_app_data = (
            os.getenv("LOCALAPPDATA")
            or str(Path.home() / "AppData" / "Local")
        )

        winget_packages_dir = os.path.join(
            local_app_data,
            "Microsoft",
            "WinGet",
            "Packages"
        )

        if os.path.exists(winget_packages_dir):

            pattern = os.path.join(
                winget_packages_dir,
                "**",
                "ffmpeg.exe"
            )

            matches = glob.glob(pattern, recursive=True)

            for match in matches:

                if verify_ffmpeg_executable(match):

                    bin_dir = os.path.dirname(
                        os.path.abspath(match)
                    )

                    if bin_dir not in os.environ["PATH"]:
                        os.environ["PATH"] += os.pathsep + bin_dir

                    return os.path.abspath(match)

        # 6. Windows Registry search for User PATH
        try:

            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
                0,
                winreg.KEY_READ
            )

            user_path, _ = winreg.QueryValueEx(
                key,
                "Path"
            )

            winreg.CloseKey(key)

            for path_entry in user_path.split(os.pathsep):

                path_entry = path_entry.strip()

                if path_entry and os.path.exists(path_entry):

                    target_exe = os.path.join(
                        path_entry,
                        "ffmpeg.exe"
                    )

                    if verify_ffmpeg_executable(target_exe):

                        if path_entry not in os.environ["PATH"]:
                            os.environ["PATH"] += (
                                os.pathsep + path_entry
                            )

                        return os.path.abspath(target_exe)

        except Exception:
            pass

    return None

def check_ffmpeg_installed() -> bool:
    """
    Returns True if a valid ffmpeg executable is found and runnable.
    """
    return find_ffmpeg_executable() is not None

def get_ffmpeg_instructions() -> str:
    """
    Return human-friendly installation instructions for FFmpeg on Windows/Mac/Linux.
    """
    return """
### ⚠️ FFmpeg is missing from your system environment!

**FFmpeg** is required by speech-to-text engines to read and decode audio files (.mp3, .wav, .m4a, .ogg).

#### Quick Setup Instructions:

**On Windows (Recommended):**
1. Open PowerShell terminal and run:
   ```bash
   winget install Gyan.FFmpeg
   ```
2. Restart your terminal / Streamlit server.

*Alternatively (Manual):*
1. Download static build from [Gyan.dev FFmpeg Builds](https://www.gyan.dev/ffmpeg/builds/) (ffmpeg-git-full.7z).
2. Extract `ffmpeg.exe` into a `bin/` folder inside this project (`c:\\Agentic AI\\Call-Intelligence-Agent\\bin\\ffmpeg.exe`).

**On macOS:**
```bash
brew install ffmpeg
```

**On Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install -y ffmpeg
```
"""
