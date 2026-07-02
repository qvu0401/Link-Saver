import re
import httpx

def fetch_title(url: str) -> str:
    try:
        response = httpx.get(url, timeout=5.0, follow_redirects=True)
        response.raise_for_status()
        match = re.search(r"<title>(.*?)</title>", response.text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return url
    except Exception:
        return url