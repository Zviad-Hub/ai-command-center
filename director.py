
import json
import re

from ai_brain import ask_ai
from config import DEPARTMENTS


VALID_DEPARTMENTS = {
    "media",
    "tenders",
    "finance",
    "business",
    "pentester",
    "technical",
    "audit"
}


DIRECTOR_PROMPT = """
You are the Chief AI Director of a multi-department AI organization.

Your CEO speaks Georgian.

Select only relevant departments from:
media, tenders, finance, business, pentester, technical, audit.

Rules:
- Video, YouTube, scripts and content production belong to media.
- Media production should also include audit for quality control.
- Historical fact-checking and source verification belong to audit.
- Software, programming, GitHub and infrastructure belong to technical.
- Financial analysis belongs to finance.
- Tender preparation belongs to tenders.
- Business planning belongs to business.
- Cybersecurity testing belongs to pentester.

SECURITY:
- Pentesting requires written authorization and explicit CEO approval.
- Never authorize testing automatically.
- Never initiate financial transactions.
- Never submit tenders or publish content without CEO approval.

Return ONLY valid JSON:

{
  "analysis": "Short explanation in Georgian",
  "departments": ["media", "audit"],
  "missions": {
    "media": "Mission",
    "audit": "Mission"
  },
  "requires_ceo_approval": true
}
"""


# ==================================================
# KEYWORD ROUTING
# ==================================================

def contains_any(text, keywords):

    return any(
        keyword in text
        for keyword in keywords
    )


def detect_departments(task):

    text = str(task).lower()

    selected = []

    media_keywords = [
        "youtube",
        "shorts",
        "video",
        "script",
        "screenplay",
        "narration",
        "voiceover",
        "thumbnail",
        "content creation",
        "media",
        "ვიდეო",
        "სცენარი",
        "იუთუბ",
        "მედია",
        "კონტენტი"
    ]

    audit_keywords = [
        "audit",
        "auditor",
        "fact-check",
        "fact check",
        "factcheck",
        "verify",
        "verification",
        "compliance",
        "quality control",
        "independent review",
        "აუდიტ",
        "ფაქტ-ჩეკ",
        "ფაქტჩეკ",
        "ფაქტების გადამოწმ",
        "დამოუკიდებელი შემოწმ",
        "ხარისხის კონტროლ",
        "ვერიფიკ"
    ]

    tender_keywords = [
        "tender",
        "procurement",
        "bid",
        "ტენდერ",
        "შესყიდვ"
    ]

    finance_keywords = [
        "finance",
        "financial",
        "budget",
        "accounting",
        "revenue",
        "profit",
        "ფინანს",
        "ბიუჯეტ",
        "ბუღალტერ",
        "შემოსავალ",
        "მოგება"
    ]

    pentester_keywords = [
        "pentest",
        "penetration test",
        "penetration testing",
        "cybersecurity",
        "vulnerability assessment",
        "შეღწევადობის ტესტ",
        "კიბერუსაფრთხო",
        "უსაფრთხოების ტესტ"
    ]

    technical_keywords = [
        "github",
        "python",
        "javascript",
        "programming",
        "software",
        "debug",
        "bug",
        "workflow",
        "api",
        "database",
        "server",
        "code",
        "coding",
        "technical",
        "პროგრამ",
        "კოდი",
        "შეცდომა",
        "ტექნიკურ",
        "სერვერ",
        "ბაზა"
    ]

    business_keywords = [
        "business",
        "ბიზნეს",
        "business plan",
        "business strategy",
        "market analysis",
        "business development",
        "ბიზნეს გეგმა",
        "ბიზნეს სტრატეგ",
        "ბაზრის ანალიზ",
        "ბიზნესის განვითარ"
    ]

    # Explicit exclusions must override keyword matches. This prevents a
    # diagnostic request saying "do not run Media" from launching Media.
    media_excluded = bool(re.search(
        r"(?:\bmedia\b.{0,40}\b(?:do not run|don't run|exclude|skip|not run)\b"
        r"|\b(?:do not run|don't run|exclude|skip|not run)\b.{0,40}\bmedia\b"
        r"|\bmedia\s+არ\s+(?:გაუშვა|გაუშვათ|ჩართო|გაუშვას))",
        text,
    ))

    # MEDIA ALWAYS GETS AN INDEPENDENT AUDIT when it is actually requested.
    if not media_excluded and contains_any(text, media_keywords):

        selected.extend([
            "media",
            "audit"
        ])

    # EXPLICIT AUDIT REQUEST

    elif contains_any(text, audit_keywords):

        selected.append("audit")

    if contains_any(text, tender_keywords):
        selected.append("tenders")

    if contains_any(text, finance_keywords):
        selected.append("finance")

    if contains_any(text, pentester_keywords):
        selected.append("pentester")

    if contains_any(text, technical_keywords):
        selected.append("technical")

    if contains_any(text, business_keywords):
        selected.append("business")

    # REMOVE DUPLICATES

    selected = list(dict.fromkeys(selected))

    return selected


# ==================================================
# MISSION GENERATOR
# ==================================================

def create_missions(task, departments):

    missions = {}

    mission_templates = {

        "media": (
            "შექმენი CEO-ს მოთხოვნის შესაბამისი მედია პროდუქტი. "
            "არ შეცვალო ორიგინალური თემა. "
            "არ გამოიგონო ფაქტები ან წყაროები."
        ),

        "audit": (
            "დამოუკიდებლად შეამოწმე მიღებული შედეგი. "
            "შეამოწმე მოთხოვნების შესრულება, მტკიცებულებები, "
            "წყაროები, ტექსტის სისრულე და უსაფრთხოება. "
            "შეცდომები დააფიქსირე გულწრფელად."
        ),

        "technical": (
            "შეასრულე ტექნიკური დავალება. "
            "შეამოწმე კოდი, სისტემის მუშაობა და შეცდომები."
        ),

        "finance": (
            "შეასრულე ფინანსური ანალიზი. "
            "ფინანსური ოპერაციები CEO-ს თანხმობის გარეშე აკრძალულია."
        ),

        "tenders": (
            "მოამზადე სატენდერო ანალიზი და დოკუმენტაცია. "
            "ტენდერის გაგზავნა CEO-ს თანხმობის გარეშე აკრძალულია."
        ),

        "business": (
            "შეასრულე ბიზნეს ანალიზი და მოამზადე რეკომენდაციები."
        ),

        "pentester": (
            "შეაფასე კიბერუსაფრთხოების დავალება. "
            "აქტიური ტესტირება დაბლოკილია წერილობითი "
            "ავტორიზაციისა და CEO-ს ცალკე ნებართვის გარეშე."
        )
    }

    for department in departments:

        missions[department] = (
            mission_templates.get(
                department,
                "შეასრულე CEO-ს დავალება."
            )
            + "\n\nCEO ORIGINAL TASK:\n"
            + str(task)
        )

    return missions


# ==================================================
# AI FALLBACK
# ==================================================

def ai_route_task(task):

    prompt = f"""
CEO TASK:

{task}

Select the relevant departments.
Return valid JSON only.
"""

    response = ask_ai(
        DIRECTOR_PROMPT,
        prompt
    )

    response = str(response).strip()

    # HANDLE MARKDOWN JSON FENCES

    response = re.sub(
        r"^```(?:json)?\s*",
        "",
        response
    )

    response = re.sub(
        r"\s*```$",
        "",
        response
    )

    # EXTRACT JSON OBJECT

    start = response.find("{")
    end = response.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object returned")

    data = json.loads(
        response[start:end + 1]
    )

    departments = data.get("departments", [])

    if not isinstance(departments, list):
        raise ValueError("Departments must be a list")

    departments = [
        department
        for department in departments
        if department in VALID_DEPARTMENTS
        and department in DEPARTMENTS
    ]

    departments = list(dict.fromkeys(departments))

    if not departments:
        raise ValueError("No valid department selected")

    return {
        "analysis": str(data.get("analysis", "")),
        "departments": departments,
        "missions": create_missions(task, departments),
        "requires_ceo_approval": True,
        "routing_method": "AI"
    }


# ==================================================
# MAIN DIRECTOR
# ==================================================

def route_task(task):

    print("\n" + "=" * 50)
    print("CHIEF AI DIRECTOR")
    print("=" * 50)

    print("\nAnalyzing CEO task...")

    # 1. RULE-BASED ROUTING FIRST

    departments = detect_departments(task)

    if departments:

        missions = create_missions(
            task,
            departments
        )

        print("\nRouting method: KEYWORD RULES")
        print("Selected departments:", departments)

        return {
            "analysis": (
                "დავალება გაანალიზებულია. "
                "დეპარტამენტები შეირჩა დავალების შინაარსის მიხედვით."
            ),
            "departments": departments,
            "missions": missions,
            "requires_ceo_approval": True,
            "routing_method": "RULE_BASED"
        }

    # 2. AI FOR UNKNOWN TASKS

    try:

        result = ai_route_task(task)

        print("\nRouting method: AI")
        print("Selected departments:", result["departments"])

        return result

    except Exception as error:

        print("\nDIRECTOR ROUTING ERROR: internal details withheld.")

        # NEVER SILENTLY PRETEND ROUTING SUCCEEDED

        return {
            "analysis": (
                "დირექტორმა დეპარტამენტის ზუსტად განსაზღვრა ვერ შეძლო. "
                "დავალება გადაეცემა ტექნიკურ დეპარტამენტს "
                "მხოლოდ საწყისი შეფასებისთვის."
            ),
            "departments": ["technical"],
            "missions": {
                "technical": (
                    "შეაფასე დავალება და დააფიქსირე "
                    "რომ საჭიროა დირექტორის ხელახალი მარშრუტიზაცია.\n\n"
                    + str(task)
                )
            },
            "requires_ceo_approval": True,
            "routing_method": "SAFE_FALLBACK",
            "routing_error": "AI_ROUTING_FAILED"
        }


# ==================================================
# DIRECTOR CONSOLE
# ==================================================

def create_plan(task):

    plan = route_task(task)

    print("\nAI DIRECTOR — ANALYSIS")
    print("-" * 45)

    print(plan["analysis"])

    print("\nROUTING METHOD:")
    print(plan.get("routing_method"))

    for department in plan["departments"]:

        print("\nMANAGER:", department.upper())

        print(
            "MISSION:",
            plan["missions"][department]
        )

    if "pentester" in plan["departments"]:

        print("\nSECURITY GATE ACTIVATED")
        print("Written authorization required.")
        print("Separate CEO approval required.")
        print("Testing remains blocked.")

    print(
        "\nCEO APPROVAL REQUIRED:",
        plan["requires_ceo_approval"]
    )

    return plan["departments"]


if __name__ == "__main__":

    task = input("CEO > ")

    create_plan(task)
