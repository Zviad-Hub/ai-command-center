"""Bound AI-to-AI report context so synthesis calls stay within provider limits."""

TRIM_MARKER = "\n\n[REPORT EXCERPT TRIMMED TO FIT THE CONTEXT BUDGET]\n\n"


def bounded_text(value, max_chars=4000):
    """Keep the beginning and end of evidence while enforcing a hard character limit."""
    text = str(value or "").strip()
    limit = max(0, int(max_chars))
    if len(text) <= limit:
        return text
    if limit <= len(TRIM_MARKER) + 2:
        return text[:limit]
    available = limit - len(TRIM_MARKER)
    head = (available * 2) // 3
    tail = available - head
    return text[:head].rstrip() + TRIM_MARKER + text[-tail:].lstrip()


def build_bounded_report_context(
    reports,
    max_chars_per_report=3000,
    max_total_chars=12000,
):
    """Format labelled reports under per-report and total request-size budgets."""
    sections = []
    used = 0
    omitted = 0

    for label, report in reports:
        heading = f"### {str(label or 'Specialist').strip()}\n"
        remaining = int(max_total_chars) - used
        if remaining <= len(heading) + 100:
            omitted += 1
            continue

        body_limit = min(int(max_chars_per_report), remaining - len(heading))
        body = bounded_text(report, body_limit)
        section = heading + (body or "No written report was returned.")
        if used + len(section) > int(max_total_chars):
            omitted += 1
            continue
        sections.append(section)
        used += len(section) + 2

    if omitted:
        note = (
            f"[{omitted} additional specialist report(s) omitted from the AI "
            "synthesis context because the shared size budget was reached. "
            "Their original reports remain in the task record.]"
        )
        if used + len(note) + 2 <= int(max_total_chars):
            sections.append(note)

    return "\n\n".join(sections)
