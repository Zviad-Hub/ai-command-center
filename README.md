# AI Command Center

**AI Command Center** is a multi-department AI organization controlled by a human CEO. You give the system a task; the AI Director selects the relevant department managers; managers coordinate their specialist workflows and return a recorded result.

> **Important:** This repository is under active development. Departments have different capabilities and strict operational limits; some workflows are advisory or passive-only. Read the capability and safety notes below before relying on an output.

## Contents

- [How the organization works](#how-the-organization-works)
- [Current department capabilities](#current-department-capabilities)
- [Requirements](#requirements)
- [Setup](#setup)
- [Run locally](#run-locally)
- [Run through GitHub Actions](#run-through-github-actions)
- [How to write a good CEO task](#how-to-write-a-good-ceo-task)
- [Task examples](#task-examples)
- [Task history](#task-history)
- [Safety and approval rules](#safety-and-approval-rules)
- [Troubleshooting](#troubleshooting)
- [Development status](#development-status)

## How the organization works

The normal task flow is:

1. **CEO (you):** describe the outcome you want, the scope, constraints and expected deliverables.
2. **AI Director:** analyzes the request and routes it to one or more departments. The current implementation uses keyword rules first and an AI fallback when no department is detected.
3. **Department Manager:** receives its own Director-generated mission, not just a copy of the generic CEO request.
4. **Specialists:** where implemented, perform their assigned work and return individual results.
5. **Task Manager:** preserves the original CEO request, passes prior department results to later managers, and records the complete task result in `tasks.json`.
6. **CEO:** reviews the result and decides whether to approve any consequential next step.

A department being selected does not mean every requested real-world action is authorized or has been completed. Check each result's `status`, `message`, approval flags and evidence.

## Current department capabilities

| Department | Current behavior | Important limitation |
|---|---|---|
| **Media** | Runs the media production pipeline for content tasks. | Content must be independently checked before publication. |
| **Audit** | Reviews the preceding Media result when one is available. | The current manager expects a Media result; a standalone audit request may return `REVIEW_REQUIRED`. |
| **Technical** | Creates a technical plan, assigns specialists, synthesizes their findings through an AI Technical Manager, and requires an independent Technical Quality Reviewer PASS before releasing the final report. | The workflow is advisory: it does not independently fetch repository files, edit project files, execute tests or deploy code. Specialists can analyze source material supplied in the task/context. |
| **Pentester** | Runs four defensive specialists (scope/authorization, web security, infrastructure security, vulnerability/risk) followed by a Pentester Manager and an independent Security Quality Reviewer. | Passive analysis and planning only. No scanning, probing, target connections, exploit generation or active penetration testing. A supplied scope/reference is not verified authorization. |
| **Finance** | Three specialists (financial analysis, risk control, budget/forecast planning) feed a Finance Manager; an independent reviewer checks the final advisory report. | No transactions, payments, investments or accounting-system changes. Research candidates are not independently verified; professional review may be needed for regulated advice. |
| **Tenders** | Three specialists (eligibility, compliance/documents, pricing/risk) feed a Tender Manager; an independent reviewer checks the final draft. | Does not submit bids or contact contracting authorities. Actual official tender documents and attachments are required for a specific compliance assessment. |
| **Business** | Three specialists (market/customer, strategy, operations/KPIs) feed a Business Manager; an independent reviewer checks the final advisory report. | Does not commit funds, sign agreements, contact third parties or execute business actions. Research candidates are not independently verified. |

The Director automatically adds Audit to Media tasks for a separate quality review. Routing is currently based on keywords, so describe the subject and desired department clearly. If a task is ambiguous, inspect the routing result rather than assuming the intended department was selected.

Finance, Business and Tenders now have an independent deterministic specialist-quality gate before manager synthesis. It checks that every required specialist returned a non-empty report with minimum role-relevant evidence markers. Missing or weak specialist output stops the workflow with `REVIEW_REQUIRED`; the manager and AI reviewer are not asked to approve it. Technical and Pentester retain their separate specialist/reviewer controls. These checks validate role coverage and report structure, not factual truth, and they do not replace human review.

## Requirements

- Python **3.11** (recommended; GitHub Actions uses 3.11)
- A Groq API key for AI calls
- A Tavily API key for research features that use Tavily
- Internet access for provider/API requests

Python packages are listed in `requirements.txt`.

## Setup

### 1. Get the project

Clone the repository and open its folder:

```bash
git clone https://github.com/Zviad-Hub/ai-command-center.git
cd ai-command-center
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS / Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure API keys

Create a local `.env` file in the project root:

```dotenv
GROQ_API_KEY=put_your_groq_key_here
TAVILY_API_KEY=put_your_tavily_key_here
```

Replace the example values locally. Never commit `.env`, paste API keys into task prompts, or share them in chat, screenshots or logs. Keep `.env` out of version control.

The application loads environment variables through `python-dotenv`. Groq is configured as the default AI provider. Tavily is used by research functionality where configured.

## Run locally

From the project root, with the virtual environment active and API keys configured:

```bash
python main.py
```

You will see the AI Command Center header and a prompt:

```text
CEO >
```

Enter one task per prompt. The system prints the task ID, selected departments and each manager's status/message.

To stop the application, type:

```text
exit
```

or press `Ctrl+C`.

## Run through GitHub Actions

You can submit a task without running Python locally:

1. Open the repository on GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Add these repository secrets:
   - `GROQ_API_KEY`
   - `TAVILY_API_KEY`
4. Open the **Actions** tab.
5. Select the **AI Command Center** workflow.
6. Click **Run workflow**.
7. Enter your task in the **CEO Task** field.
8. Start the workflow and wait for it to finish.
9. Open the run to inspect its logs and result.

The workflow runs `task_manager.submit_task()` with read-only repository permissions and stores its temporary history under the runner's temporary directory. It suppresses agent prompts and full reports from Actions logs. A complete report artifact is uploaded for 7 days only when the repository is private. Because this repository is currently public, full task reports are deliberately not uploaded; the public run shows only a task ID, status and department names. Make the repository private before running confidential tasks or expecting downloadable full reports. The workflow never pushes generated task history into a source branch.

A successful GitHub Actions run means the workflow completed; it does **not** automatically mean every department completed its mission or that its output is factually correct. Download and inspect the task-report artifact and each manager's result.

## How to write a good CEO task

Give agents enough context to do useful work. A good request normally includes:

1. **Goal:** what outcome do you need?
2. **Scope:** what should be included and excluded?
3. **Context:** relevant project, audience, market, files or background.
4. **Deliverables:** the exact format and items you expect.
5. **Constraints:** language, length, budget, deadline, tools or technical limits.
6. **Evidence:** whether sources, citations, calculations or test results are required.
7. **Approval boundary:** what the agents may analyze or prepare, and what must wait for your approval.

Use clear instructions and measurable acceptance criteria. Prefer one well-scoped task over several unrelated requests in one prompt.

### Recommended task template

Copy this template and replace the bracketed text:

```text
GOAL:
[What result do I want?]

CONTEXT:
[Background information the agents need.]

SCOPE:
[What to include.]

DO NOT:
[What must not be changed, assumed, published or executed.]

DELIVERABLES:
1. [Deliverable one]
2. [Deliverable two]
3. [Deliverable three]

QUALITY REQUIREMENTS:
[Sources, accuracy, format, tests, word count, language, etc.]

APPROVAL:
Analyze and prepare the work only. Do not publish, deploy,
submit, spend money, contact third parties or perform active
security testing without my separate explicit approval.
```

## Task examples

### Media production

```text
Create exactly one English YouTube Short about [TOPIC].
Target duration: 60 seconds.
Audience: general viewers.
Deliver: title, hook, narration, timestamped visual directions
and sources for factual claims.
Do not change the topic or invent sources.
Send the finished result to the independent Audit department.
Do not publish anything.
```

### Technical planning and review

```text
Review the [PROJECT / FEATURE] architecture.
Identify bugs, security risks and maintainability problems.
Have the relevant technical specialists provide separate findings.
Deliver: prioritized issues, file paths, explanations,
recommended fixes and a test plan.
Do not modify files, merge branches or deploy anything.
Clearly distinguish verified facts from assumptions.
```

### Independent audit

```text
Review the supplied Media output against the original task.
Check factual claims, source quality, completeness and compliance.
List each issue with evidence and a recommended correction.
Do not rewrite the original task or approve publication automatically.
```

**Note:** The current Audit manager is wired to review a preceding Media result. A standalone audit request may not have the input it needs.

### Business or financial analysis

```text
Prepare an analysis of [BUSINESS QUESTION].
Use the assumptions and figures I provide.
Separate confirmed inputs, assumptions and estimates.
Show the calculation method, risks and practical recommendations.
Do not make payments, move funds or enter into agreements.
```

**Note:** Finance and Business now produce advisory AI reports; optional Tavily research is treated as candidate evidence, not independently verified fact.

### Tender preparation

```text
Analyze this tender: [TENDER DETAILS].
Prepare an eligibility checklist, required documents,
compliance gaps, risks and a draft response outline.
Do not submit the tender or contact the contracting authority.
```

**Note:** Tenders now prepares an advisory analysis and draft checklist, but it cannot submit a bid. A specific tender still requires its complete official notice and attachments.

### Cybersecurity assessment

```text
Review the supplied architecture, application code and configuration.
Separate observed evidence from assumptions.
Identify likely risks, severity, confidence and remediation steps.
List the exact scope and written authorization evidence still required.
Do not scan, probe, connect to, exploit or modify any system.
```

**Note:** Pentester runs four defensive specialist analyses, creates a manager report, and sends it to an independent security reviewer. The report is released only after an explicit review PASS. This workflow is passive-only and cannot perform an active penetration test, even if scope or an authorization reference is supplied. Human scope review and separate CEO approval remain mandatory for any future active-testing capability.

#### Supplying evidence to Pentester

For deterministic file and line validation, include source excerpts in the CEO task context using this numbered manifest format. Repeat the `FILE:` header for each supplied file:

```text
FILE: src/auth.py
1: def login(user):
2:     if user.is_authenticated:
3:         return dashboard()
4:     return login_page()

FILE: config/settings.yaml
1: DEBUG: false
2: SESSION_COOKIE_SECURE: true
```

Cited references such as `src/auth.py:2-3` are checked against the supplied file and numbered lines. If artifacts are supplied in another format, references are treated as unverifiable and the report is held for review. With no artifacts and no confirmed claims, the validator reports `UNVERIFIED` rather than inventing evidence. CVE identifiers are checked only for a matching mention in the supplied material; this is not external CVE-database verification or proof that a vulnerability exists.

## Task history

Each submitted task is stored outside the repository in the operating system's private application-data directory. You can override the location with `AI_COMMAND_CENTER_TASKS_FILE`. On Windows the default is under `%LOCALAPPDATA%\\AI Command Center\\tasks.json`; on macOS it is under `~/Library/Application Support/AI Command Center/tasks.json`; on Linux it is under `$XDG_STATE_HOME/ai-command-center/tasks.json` or `~/.local/state/ai-command-center/tasks.json`. A legacy root-level `tasks.json` is migrated on first run if it is still present. **Before pulling this update in an older checkout, copy the file to the new private location first**, because Git will remove the tracked root-level file. Windows PowerShell: `New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\\AI Command Center" | Out-Null; Copy-Item .\\tasks.json "$env:LOCALAPPDATA\\AI Command Center\\tasks.json"`. Linux: `mkdir -p ~/.local/state/ai-command-center && cp tasks.json ~/.local/state/ai-command-center/tasks.json`. macOS: `mkdir -p "$HOME/Library/Application Support/AI Command Center" && cp tasks.json "$HOME/Library/Application Support/AI Command Center/tasks.json"`. If you use `AI_COMMAND_CENTER_TASKS_FILE` or `XDG_STATE_HOME`, copy it to that configured path instead. In GitHub Actions the file is temporary, and a full report artifact is created only for private repositories. The record includes:

- `id`: short task identifier
- `created_at`: UTC timestamp
- `task`: original CEO request
- `departments`: selected departments
- `routing`: Director's routing decision and missions
- `results`: department outputs

Use the task ID to identify a run. Treat the saved record as an execution log, not as proof that every claim or action in it is correct.

## Safety and approval rules

- **Human CEO remains in control.** AI output is advice or prepared work until reviewed.
- Never put API keys, passwords, tokens or private credentials in prompts.
- Task prompts and reports can contain confidential business or personal information. This repository is public; do not submit confidential tasks until the repository is made private. Public Actions runs intentionally do not publish full task reports.
- Do not ask agents to access systems, accounts or data you do not own or have permission to use.
- Pentester performs passive analysis only. Written authorization and exact scope require human verification; separate CEO approval is required for any future active testing. The current workflow cannot perform active testing.
- Do not publish media, submit tenders, make payments, contact third parties, merge code or deploy to production without the required explicit approval.
- Do not treat a plan, `RECEIVED`, `COMPLETED` or successful workflow run as automatic permission for a consequential action.
- Verify important facts, calculations, citations and code independently.
- Keep API secrets in local environment variables or GitHub Actions Secrets.

## Troubleshooting

| Problem | What to check |
|---|---|
| `GROQ_API_KEY` missing or authentication error | Check that the key is set in local `.env` or GitHub Actions Secrets. Never paste the key into an issue or task. |
| AI provider quota or rate limit | Check the provider account's quota and try again later. |
| No expected department selected | Review the Director's `routing` record. Use explicit task language and department-specific terms. |
| Audit says no Media result is available | The current Audit workflow expects a Media result earlier in the same task. |
| Technical result is `REVIEW_REQUIRED` | Inspect the manager plan, selected specialists and error details. A plan is not an implementation approval. |
| Finance, Business or Tenders returns `REVIEW_REQUIRED` | Inspect the AI/provider error, missing inputs and research warning. These workflows produce advisory reports only. |
| Pentester returns `PREPARATION_ONLY` or `PASSIVE_REVIEW_ONLY` | The department has prepared a defensive analysis only. Check the independent review and scope gaps; no active testing was performed. |
| GitHub Actions fails | Open the failed run, inspect the first failing step and its logs, and confirm dependencies and repository secrets are configured. Do not expose secret values in logs. |

## Development status

This is an actively developed project. The current regression suite contains 162 automated tests across Director routing, Task Manager orchestration, Technical Manager planning, Technical Department specialist orchestration, manager synthesis and independent-review gates, CEO console report rendering, Finance/Business/Tenders multi-specialist and independent-review workflows, Pentester specialist/reviewer safety gates, and redaction of internal provider and workflow errors across managers, specialists, research, routing, and CLI output. The dedicated GitHub Actions test workflow runs the suite on every Python source change and every workflow change in pull requests. Department coverage and specialist capabilities are being expanded incrementally.

When contributing:

1. Work on a separate branch.
2. Add or update automated tests for behavior changes.
3. Run the relevant test suite and report the actual result.
4. Keep secrets out of commits and logs.
5. Do not merge to `main` or deploy without CEO approval.

---

**Built for a human-led AI organization: the CEO sets the goal, the Director routes the work, departments contribute, and the CEO makes the final decisions.**


## Department stress testing

The deterministic Director routing stress suite is available in `stress_test_suite.py`.
It includes customer-style scenarios for every department and multi-department
requests. Run it with:

```bash
python -c "from stress_test_suite import run_routing_stress_tests; import json; print(json.dumps(run_routing_stress_tests(), ensure_ascii=False, indent=2))"
```

The suite checks routing only and does not call department AI agents or perform
external actions. GitHub Actions prints the live routing scorecard and fails the
job if any expected department route is incorrect. `evaluate_task_record(record)`
provides a structural 10-point quality and safety score for a saved orchestration record. A perfect
score is not proof of factual correctness; human review remains mandatory.

## Offline department quality regression tests

Run the deterministic evaluator tests without calling Groq, Tavily, or any external service:

```bash
python -m unittest tests.test_agent_quality_stress_test -v
```

These tests use controlled fixtures to verify each department's scoring rules, reviewer gates, evidence handling, safety flags, and provider-quota classification. They do **not** execute department agents and do not consume API quota. Use this offline suite for routine quality-regression checks; reserve the opt-in live test below for deliberate end-to-end evaluations when provider quota is available.

## Live AI department quality stress test

The opt-in live suite in `agent_quality_stress_test.py` evaluates real Finance,
Business, Tenders, Pentester and Technical department outputs. It checks
specialist participation, manager/reviewer gates, task-specific requirements,
honest uncertainty, arithmetic in the controlled Finance scenario, four
formula-backed Business KPIs and validation experiments, Tender deadline/evidence
honesty, and safety flags. It deliberately disables Tavily research so the test uses only the
controlled facts supplied in each scenario.

Run locally only when you intentionally want to spend Groq API quota:

```bash
python agent_quality_stress_test.py --live
```

The command writes `agent_quality_stress_report.json`. It is not run on every
pull request. In GitHub Actions, open **Actions → Technical Department Tests →
Run workflow**, set **Run real AI department quality tests** to `true`, and
start the run. The workflow uses the existing `GROQ_API_KEY` repository secret
and uploads `live-agent-quality-stress-report` for 14 days.

The live score is a heuristic quality gate, not proof that a factual claim is
true. A passing score never replaces human review. The suite does not perform
transactions, tender submissions, external contact, network scans, penetration
tests, code edits, test execution, merges, or deployments.

Each department entry in the JSON report includes a `diagnostics` list when
safe failure codes are available. These codes identify the failure category
without exposing raw provider messages, prompts or credentials. Examples:

| Diagnostic code | Meaning |
|---|---|
| `PROVIDER_RATE_LIMIT_EXHAUSTED` | The provider rate limit remained after retries. |
| `PROVIDER_DAILY_QUOTA_EXHAUSTED` | The provider's daily quota was exhausted. |
| `PROVIDER_TIMEOUT` | The provider request timed out. |
| `PROVIDER_CONNECTION_ERROR` | A provider connection could not be completed. |
| `PROVIDER_HTTP_ERROR` | The provider returned an unsuccessful HTTP response. |
| `PROVIDER_EMPTY_RESPONSE` | The provider returned no usable response content. |
| `INVALID_AGENT_RESPONSE` | An agent returned an invalid or unusable response. |
| `AGENT_PROCESSING_ERROR` | An unexpected internal processing error occurred. |

Use the `source` field to identify the affected manager or specialist. A
diagnostic code narrows down the failure category; it does not expose the full
provider response and does not by itself prove the underlying cause.
