
from config import DEPARTMENTS


DEPARTMENT_DESCRIPTIONS = {
    "media": "ვიდეოები, ტრენდები, კვლევა და კონტენტი",
    "tenders": "სახელმწიფო ტენდერები და შესყიდვები",
    "finance": "ფინანსური და კრიპტო ბაზრის ანალიზი",
    "business": "ბიზნეს იდეები და ბაზრის კვლევა",
    "pentester": "კიბერუსაფრთხოება და ნებადართული პენტესტირება",
    "technical": "პროგრამირება და ტექნიკური ავტომატიზაცია",
    "audit": "შედეგების შემოწმება და ხარისხის კონტროლი"
}


def route_task(task):
    task_lower = task.lower()

    keywords = {
        "media": ["ვიდეო", "youtube", "ტიკტოკ", "ისტორია", "კონტენტი"],
        "tenders": ["ტენდერი", "შესყიდვა", "აუქციონი"],
        "finance": ["კრიპტო", "ბიტკოინი", "ფინანს", "ბირჟა"],
        "business": ["ბიზნეს", "კომპანია", "ბაზარი", "იდეა"],
        "pentester": ["pentest", "ჰაკ", "უსაფრთხოება", "შეღწევა"],
        "technical": ["კოდი", "პროგრამა", "შეცდომა", "ავტომატიზაცია"],
        "audit": ["აუდიტი", "შემოწმება", "გადამოწმება"]
    }

    selected = []

    for department, words in keywords.items():
        if any(word in task_lower for word in words):
            selected.append(department)

    if not selected:
        selected = ["technical"]

    return selected


def create_plan(task):
    departments = route_task(task)

    print("\nAI DIRECTOR — TASK ANALYSIS")
    print("-" * 40)
    print("CEO TASK:", task)

    for department in departments:
        print("\nMANAGER:", department.upper())
        print("MISSION:", DEPARTMENT_DESCRIPTIONS[department])

    if "pentester" in departments:
        print("\nSECURITY GATE ACTIVATED")
        print("Written authorization required.")
        print("CEO approval required.")
        print("No testing will start automatically.")

    print("\nSTATUS: PLAN CREATED")
    print("Execution is not yet enabled.")

    return departments


if __name__ == "__main__":
    task = input("CEO, enter your task: ")
    create_plan(task)
