import jmcomic
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import jmcomic.jm_exception


def jm_init():
    global option
    option = jmcomic.create_option_by_str(
        """
download:
    cache: true
    image:
        suffix: .png
    threading:
        image: 16

dir_rule:
    base_dir: ./jmcache/src/

plugins:
    after_album:
        - plugin: img2pdf
          kwargs:
              pdf_dir: ./jmcache/pdf/
              filename_rule: Aid
              delete_original_file: false
"""
    )


async def jm_download(code: str) -> tuple[int, str]:
    if not code.isdecimal():
        return -1, None

    pdf_path = os.path.abspath(os.path.join("./jmcache/pdf/", f"{code}.pdf"))

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

    return 0, pdf_path
