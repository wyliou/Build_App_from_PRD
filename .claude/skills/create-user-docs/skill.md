---
name: create-user-docs
description: Create end-user documentation and training materials
---

# Create User Documentation

**Goal:** Auto-generate end-user documentation by discovering context from existing project files.

**Your Role:** Technical writer. Produce clear, actionable documentation for end users — zero questions asked.

---

## WORKFLOW

### Phase 1: Auto-Discovery

Scan the project for context. Read every source found — do NOT ask the user for information that can be discovered.

**Search order (stop adding context when sufficient, but always check all sources):**

1. **Project docs** — scan `docs/` for any of: `prd.md`, `PRD.md`, `requirements.md`, `ux-design.md`, `project-charter.md`, `architecture.md`, `ARCHITECTURE.md`, `design.md`
2. **README** — read `README.md` or `README` at project root
3. **Config files** — read `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, or equivalent to identify project type, name, and dependencies
5. **CLI help** — if the project has a CLI entry point, check for argparse/click/clap definitions to extract commands and flags
6. **Source code** — scan entry points (`__main__.py`, `cli.py`, `main.py`, `index.ts`, `main.go`, etc.) for user-facing commands, options, and error handling
7. **Error/status codes** — search for error code catalogs, enums, or constants that define user-visible messages
8. **Config schemas** — read config file examples or schemas that users need to understand

**Extract and organize into these categories:**

| Category | What to Extract |
|----------|----------------|
| **Identity** | System name, version, one-line description, project type (CLI / Web App / API / Library / Desktop App) |
| **Access** | How users get and run it (install, URL, executable, package manager, etc.) |
| **Users** | User types/roles, their goals, technical level (infer from project type if not explicit) |
| **Commands / Actions** | All user-facing commands, flags, options, API endpoints, or UI actions |
| **Workflow** | Primary user journey from start to finish — the "happy path" |
| **Configuration** | Config files users need to know about, what they control, how to edit them |
| **Statuses / Outputs** | Status codes, output formats, result types users will see |
| **Errors & Warnings** | All user-visible error/warning codes with meanings and resolutions |
| **Edge Cases** | Known gotchas, limitations, common mistakes |

**If a category has no discoverable information**, omit it from the output — do NOT invent content or ask the user.

---

### Phase 2: Generate

Write the user guide directly to `docs/user-guide.md`. Do NOT use a template file — generate content based on what was discovered.

**Writing rules:**
- Friendly but professional tone
- Action-oriented: "Run `cmd`" not "You should run `cmd`"
- Assume no prior knowledge of the system
- Numbered steps for procedures, bullet points for lists
- Include expected outcomes: "You'll see..."
- Bold key terms, commands, and UI elements
- Only include sections where discovered content exists — never generate empty or placeholder sections

**Adapt the document structure to the project type:**

#### For CLI Tools:
```
# User Guide: {name}
## Getting Started        — what it is, who it's for, installation
## Quick Start            — first run, minimal example
## Commands               — each command/flag with usage and examples
## Configuration          — config files, what each setting does
## Output Format          — what the tool produces, how to read it
## Error Reference        — every error/warning code, meaning, resolution
## FAQ                    — common questions derived from edge cases
## Troubleshooting        — symptom → solution for common problems
## Getting Help           — support channels, what to include in a report
```

#### For Web Applications:
```
# User Guide: {name}
## Getting Started        — what it is, who it's for, how to access
## Quick Start            — login, first action, basic workflow
## How-To Guides          — task-based guides for each user action
## Reference              — field definitions, status meanings, shortcuts
## FAQ                    — common questions
## Troubleshooting        — common user problems
## Getting Help           — support contacts, feedback
```

#### For APIs:
```
# User Guide: {name}
## Getting Started        — what it does, authentication, base URL
## Quick Start            — first API call, minimal example
## Endpoints              — each endpoint with request/response examples
## Authentication         — how to get and use credentials
## Error Reference        — HTTP status codes, error response format
## Rate Limits & Usage    — quotas, best practices
## FAQ                    — common integration questions
## Getting Help           — support channels
```

#### For Libraries / SDKs:
```
# User Guide: {name}
## Getting Started        — what it does, installation
## Quick Start            — minimal usage example
## API Reference          — key classes/functions with examples
## Configuration          — options, settings, customization
## FAQ                    — common usage questions
## Troubleshooting        — common errors and fixes
## Getting Help           — issue tracker, contributing
```

**If project type doesn't match any above**, use the CLI structure as default and adapt section names as needed.

---

### Phase 3: Validate & Report

After writing the file, verify completeness:

| Check | Requirement |
|-------|-------------|
| Getting Started | Explains what, who, and how to access/install |
| Quick Start | A complete first-use walkthrough exists |
| Core content | At least 3 substantive how-to/command/endpoint sections |
| Error reference | All discovered error codes are documented (if any exist) |
| FAQ | At least 3 entries |
| No placeholders | No `{{template}}` variables, `TODO`, or `TBD` markers remain |

**Report to user (no confirmation needed):**
```
User guide saved to docs/user-guide.md

Coverage:
- Sections: {N}
- How-to / Command guides: {N}
- Error codes documented: {N}
- FAQ entries: {N}
```

---

## RULES

1. **Never ask the user questions.** Everything needed is in the project files. If something truly cannot be discovered (e.g., support email), omit the section.
2. **Never generate placeholder content.** Every sentence must be based on discovered facts.
3. **Never use a template file.** Generate content directly from extracted context.
4. **Adapt structure to project type.** Do not force a web-app structure onto a CLI tool.
5. **Be concise.** Prefer tables over paragraphs for reference material. Keep procedures to numbered steps.
6. **Include version and date.** Use project version from config if available, otherwise "1.0". Use today's date.
