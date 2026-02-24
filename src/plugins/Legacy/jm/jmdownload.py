import asyncio
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple
from pathlib import Path

import jmcomic
import jmcomic.jm_exception

from src.common.config import global_config
from src.common.resource import resource_manager

# Get data directory: data/config/jm
data_dir = resource_manager.data_root / "config" / "jm"
data_dir.mkdir(parents=True, exist_ok=True)
img_path = data_dir / "src"
pdf_path = data_dir / "pdf"

# Ensure directories exist
img_path.mkdir(parents=True, exist_ok=True)
pdf_path.mkdir(parents=True, exist_ok=True)

option = None

def jm_init():
    global option
    # Convert Paths to string for jmcomic config
    img_dir_str = str(img_path.resolve()).replace("\\", "/")
    pdf_dir_str = str(pdf_path.resolve()).replace("\\", "/")
    
    option = jmcomic.create_option_by_str(
        f"""
download:
  cache: true
  image:
    suffix: .png
  threading:
    image: {global_config.jm_download_thread}

dir_rule:
  base_dir: {img_dir_str}
  rule: Bd_Aid

plugins:
  after_album:
    - plugin: img2pdf
      kwargs:
        pdf_dir: {pdf_dir_str}
        filename_rule: Aid
        delete_original_file: false
"""
    )


async def jm_download(code: str) -> Tuple[int, str]:
    if not code.isdecimal():
        return -1, None

    # Target PDF file path
    target_pdf = pdf_path / f"{code}.pdf"

    if target_pdf.exists():
        return 0, str(target_pdf)

    global option
    if option is None:
        jm_init()
        
    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        try:
            # download_album returns (album_id, downloader)
            _, downloader = await loop.run_in_executor(executor, jmcomic.download_album, code, option)
        except jmcomic.jm_exception.MissingAlbumPhotoException:
            return -1, "id不存在"
        except Exception as e:
            # Clean up if failed
            if target_pdf.exists():
                os.remove(target_pdf)
            return -1, f"下载异常: {str(e)}"
            
        if len(downloader.download_failed_list) != 0:
            if target_pdf.exists():
                os.remove(target_pdf)
            return -1, "部分图片下载失败"

    # Cleanup source images directory
    src_dir = img_path / code
    if src_dir.exists():
        try:
            shutil.rmtree(src_dir)
        except Exception:
            pass
            
    return 0, str(target_pdf)
