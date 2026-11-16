
    # NARRATION WORD COUNT

    narration = ""

    match = re.search(
        r"^\s*\*{0,2}(?:SCRIPT|NARRATION)"
        r"(?:\s*\([^)]*\))?\s*:\*{0,2}\s*"
        r"(.*?)"
        r"(?=^\s*\*{0,2}VISUAL DIRECTIONS\s*:\*{0,2})",
        edited,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    if match:
        narration = match.group(1).strip()

    narration = re.sub(r"\*\*|__", "", narration)

   
