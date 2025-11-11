import asyncio
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

import jmcomic
import jmcomic.jm_exception

from .config import Config


def jm_init():
    global option
    option = jmcomic.create_option_by_str(
        f"""
download:
  cache: true
  image:
    suffix: .png
  threading:
    image: {Config.download_thread}

dir_rule:
  base_dir: {Config.img_path}
  rule: Bd_Aid

plugins:
  after_album:
    - plugin: img2pdf
      kwargs:
        pdf_dir: {Config.pdf_path}
        filename_rule: Aid
        delete_original_file: false
"""
    )


async def jm_download(code: str) -> Tuple[int, str]:
    if not code.isdecimal():
        return -1, None

    pdf_path = os.path.abspath(os.path.join(Config.pdf_path, f"{code}.pdf"))

    if os.path.exists(pdf_path):
        return 0, pdf_path

    global option
    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        try:
            _, downloader = await loop.run_in_executor(executor, jmcomic.download_album, code, option)
        except jmcomic.jm_exception.MissingAlbumPhotoException:
            return -1, "id不存在"
        except:
            os.remove(pdf_path)
            return -1, "未成功下载"
        if len(downloader.download_failed_list) != 0:
            os.remove(pdf_path)
            return -1, "未成功下载"
    shutil.rmtree(os.path.abspath(os.path.join(Config.img_path, code)))
    return 0, pdf_path
