import concurrent.futures
import io
import urllib.parse
from typing import Sequence

from PIL import Image
import requests
from requests.sessions import HTTPAdapter
from urllib3 import Retry


def download_image(
    url: str,
    base_url: str = 'https://www.mtgnexus.com',
    session: requests.Session | None = None,
    timeout: int = 15,
) -> Image.Image:
    """
    Download a single image from a relative or absolute URL and return it as an RGB PIL Image.
    """
    full_url = urllib.parse.urljoin(base_url, url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    requester = session.get if session is not None else requests.get
    response = requester(full_url, headers=headers, timeout=timeout)
    response.raise_for_status()

    img = Image.open(io.BytesIO(response.content))
    return img.convert('RGB')


def download_images(
    urls: Sequence[str],
    base_url: str = 'https://www.mtgnexus.com',
    max_workers: int = 10,
    timeout: int = 15,
) -> list[Image.Image]:
    """
    Download multiple images concurrently while preserving their original order.
    """
    if not urls:
        return []

    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"POST"},
    )
    with requests.Session() as session:
        session.mount('https://', HTTPAdapter(max_retries=retries))
        def _fetch(url: str) -> Image.Image:
            return download_image(url, base_url=base_url, session=session, timeout=timeout)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(_fetch, urls))
