# AI Command Center

**AI Command Center** is a multi-department AI organization controlled by a human CEO. You give the system a task; the AI Director selects the relevant department managers; managers coordinate their specialist workflows and return a recorded result.

> **Important:** This repository is under active development. Some departments are working pipelines, while others are currently placeholders. Read the capability and safety notes below before relying on an output.

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
| **Technical** | Creates a technical plan and assigns selected specialist agents for analysis and reports. | The specialist workflow is advisory: it does not currently edit project files, execute tests or deploy code. |
| **Pentester** | Receives cybersecurity requests and applies a safety gate. | Active testing is currently blocked by the manager. Do not treat task submission as authorization or as a completed security test. |
| **Finance** | Produces an AI-assisted advisory report with calculations, assumptions, risks and missing inputs; can attach optional Tavily research candidates. | No transactions, payments, investments or accounting-system changes. Professional review may be needed for regulated advice. |
| **Tenders** | Prepares tender-analysis reports, eligibility/document checklists, compliance gaps and draft response plans. | Does not submit bids or contact contracting authorities. Actual tender documents are required for a specific compliance assessment. |
| **Business** | Produces strategy reports, options, trade-offs, risks and measurable KPI recommendations, with optional research candidates. | Does not commit funds, sign agreements, contact third parties or execute business actions. |

The Director automatically adds Audit to Media tasks for a separate quality review. Routing is currently based on keywords, so describe the subject and desired department clearly. If a task is ambiguous, inspect the routing result rather than assuming the intended department was selected.

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

The current workflow runs `task_manager.submit_task()` with read-only repository permissions. It uploads `tasks.json` as the `ai-command-center-task-report` artifact (available from the workflow run) for 14 days. It does not push generated task history into a source branch.

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
Prepare a passive security review plan for assets that I own
or am explicitly authorized to assess.
Identify the written scope, permitted methods, exclusions
and evidence required.
Do not scan, exploit, access or modify any system.
Wait for separate written authorization and CEO approval.
```

**Note:** The current Pentester manager blocks active testing. A task prompt alone cannot unlock it.

## Task history

Each submitted task is stored locally in `tasks.json`. In GitHub Actions, this file is uploaded as a workflow artifact named `ai-command-center-task-report` and retained for 14 days. The record includes:

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
- Do not ask agents to access systems, accounts or data you do not own or have permission to use.
- Pentesting requires a defined authorized scope and explicit approval; the current Pentester manager blocks active testing.
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
| Finance, Business or Tenders returns `RECEIVED` | These departments are placeholders while their specialist workflows are being built. |
| Pentester returns `BLOCKED` | This is the current safety behavior; active testing is not enabled. |
| GitHub Actions fails | Open the failed run, inspect the first failing step and its logs, and confirm dependencies and repository secrets are configured. Do not expose secret values in logs. |

## Development status

This is an actively developed project. The current regression suite contains 23 automated tests across Director routing, Task Manager orchestration, Technical Manager planning, Technical Department execution gates, CEO console report rendering, and Finance/Business/Tenders advisory workflows. The dedicated GitHub Actions test workflow runs the suite on relevant pull-request changes. Department coverage and specialist capabilities are being expanded incrementally.

When contributing:

1. Work on a separate branch.
2. Add or update automated tests for behavior changes.
3. Run the relevant test suite and report the actual result.
4. Keep secrets out of commits and logs.
5. Do not merge to `main` or deploy without CEO approval.

---

**Built for a human-led AI organization: the CEO sets the goal, the Director routes the work, departments contribute, and the CEO makes the final decisions.**
