""""Bound AI-to-AI report context so synthesis calls stay within provider limits."""

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
    total_limit = max(0, int(max_total_chars))
    if total_limit == 0:
        return ""

    sections = []
    used = 0
    omitted = 0
    report_items = list(reports)

    for index, (label, report) in enumerate(report_items):
        heading = f"### {str(label or 'Specialist').strip()}\n"
        separator_cost = 2 if sections else 0
        remaining = total_limit - used
        # Reserve room for the omission notice if later reports may not fit.
        reserve = 160 if index < len(report_items) - 1 else 0
        body_budget = remaining - separator_cost - len(heading) - reserve
        if body_budget < 100:
            omitted += len(report_items) - index
            break

        body_limit = min(max(0, int(max_chars_per_report)), body_budget)
        body = bounded_text(report, body_limit)
        section = heading + (body or "No written report was returned.")
        addition = separator_cost + len(section)
        if used + addition + reserve > total_limit:
            omitted += len(report_items) - index
            break
        sections.append(section)
        used += addition

    if omitted:
        note = (
            f"[{omitted} additional specialist report(s) omitted from the AI "
            "synthesis context because the shared size budget was reached. "
            "Their original reports remain in the task record.]"
        )
        addition = (2 if sections else 0) + len(note)
        if used + addition <= total_limit:
            sections.append(note)

    return "\n\n".join(sections)
