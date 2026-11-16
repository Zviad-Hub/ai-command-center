
from config import APP_NAME, APP_VERSION, DEPARTMENTS


def show_dashboard():
    print("=" * 50)
    print(f"{APP_NAME} v{APP_VERSION}")
    print("AI ORGANIZATION CONTROL CENTER")
    print("=" * 50)

    print("\nCEO: SYSTEM OWNER")
    print("AI DIRECTOR: READY")

    print("\nDEPARTMENTS:")

    for department in DEPARTMENTS:
        print(f"[READY] {department.upper()} MANAGER")

    print("\nSECURITY PROTOCOL:")
    print("Pentesting requires:")
    print("- Written authorization document")
    print("- Document validation")
    print("- CEO approval")
    print("- Approved testing scope")

    print("\nSystem foundation initialized.")


if __name__ == "__main__":
    show_dashboard()
