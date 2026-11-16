
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

    # Remove Markdown formatting
    narration = re.sub(r"\*\*|__", "", narration)

    word_count = len(
        re.findall(r"\b[\w’'-]+\b", narration)
    )

    word_count_ok = (
        125 <= word_count <= 140
        if narration
        else False
    )

    checks.append(check_result(
        "Narration word count",
        word_count_ok,
        f"Detected words: {word_count}; Required: 125-140"
    ))
