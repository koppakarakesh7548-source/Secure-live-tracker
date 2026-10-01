import re

def parse_user_agent(ua_string):
    """
    Safely parse User-Agent string to extract general Browser and OS family.
    Does not perform any covert fingerprinting or canvas/hardware probes.
    Returns: (browser_name, os_name)
    """
    if not ua_string or not isinstance(ua_string, str):
        return ("Unknown Browser", "Unknown OS")

    ua = ua_string

    # 1. Determine Operating System
    os_name = "Unknown OS"
    if "Windows NT 10.0" in ua:
        os_name = "Windows 10/11"
    elif "Windows NT 6.3" in ua:
        os_name = "Windows 8.1"
    elif "Windows NT 6.2" in ua:
        os_name = "Windows 8"
    elif "Windows NT 6.1" in ua:
        os_name = "Windows 7"
    elif "Windows" in ua:
        os_name = "Windows"
    elif "Android" in ua:
        match = re.search(r'Android\s+([0-9\.]+)', ua)
        os_name = f"Android {match.group(1)}" if match else "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    elif "Macintosh" in ua or "Mac OS X" in ua:
        os_name = "macOS"
    elif "Linux" in ua:
        os_name = "Linux"
    elif "CrOS" in ua:
        os_name = "Chrome OS"

    # 2. Determine Browser
    browser_name = "Unknown Browser"
    if "Edg/" in ua or "Edge/" in ua:
        match = re.search(r'Edg[e]?\/([0-9\.]+)', ua)
        browser_name = f"Microsoft Edge {match.group(1).split('.')[0]}" if match else "Microsoft Edge"
    elif "OPR/" in ua or "Opera/" in ua:
        match = re.search(r'OPR\/([0-9\.]+)', ua)
        browser_name = f"Opera {match.group(1).split('.')[0]}" if match else "Opera"
    elif "Chrome/" in ua and "Chromium" not in ua and "Safari/" in ua:
        match = re.search(r'Chrome\/([0-9\.]+)', ua)
        browser_name = f"Chrome {match.group(1).split('.')[0]}" if match else "Chrome"
    elif "Firefox/" in ua:
        match = re.search(r'Firefox\/([0-9\.]+)', ua)
        browser_name = f"Firefox {match.group(1).split('.')[0]}" if match else "Firefox"
    elif "Safari/" in ua and "Chrome/" not in ua:
        match = re.search(r'Version\/([0-9\.]+).*Safari', ua)
        browser_name = f"Safari {match.group(1).split('.')[0]}" if match else "Safari"
    elif "curl" in ua.lower():
        browser_name = "cURL"
    elif "python" in ua.lower():
        browser_name = "Python Requests"

    return (browser_name, os_name)
