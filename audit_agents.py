
def extract_visual_ranges(text):
    text = str(text)

    # Normalize different dash characters
    text = re.sub(r"[‐‑‒–—−]", "-", text)

    pattern = (
        r"(?m)^\s*"
        r"(?:[-*]\s*)?"
        r"(\d{1,2}:\d{2})\s*-\s*"
        r"(\d{1,2}:\d{2})"
    )

    return re.findall(pattern, text)
