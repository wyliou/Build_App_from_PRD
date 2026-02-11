# Build Skill Context Optimization

## Lessons from 2026-02-06 Build

### Problem 1: Plan subagents can't write files
- Plan subagents are read-only (no Write tool)
- Forces main agent to copy subagent output into Write calls
- build-plan.md was ~500 lines copied through main context
- **Fix**: Use general-purpose subagent for any task that must produce files

### Problem 2: Separate discover + plan phases are redundant
- Phase 1 (discover) reads PRD + architecture, returns brief
- Phase 2 (plan) reads the SAME files again, plus receives the brief
- Main agent pastes the discovery brief into the plan prompt (more context waste)
- **Fix**: Merge into single subagent that discovers, plans, and writes both files

### Problem 3: Delegation prompts inline interface signatures
- Each module delegation had 50+ lines of EXPORTS/IMPORTS signatures
- 11 modules x 50 lines = ~550 lines of main context on prompt construction
- These signatures were already in build-plan.md
- **Fix**: Tell subagents "Read build-plan.md section X for your interfaces"

### Problem 4: Phase 6 (Simplify) incorrectly skipped
- Old skip condition: "< 5 modules or test suite is already clean"
- "Test suite is already clean" was misread as "tests pass"
- But passing tests says nothing about code duplication
- **Fix**: Only skip if single batch (no parallel subagents built modules)

## Main Agent's Ideal Role
The main agent should ONLY do:
1. Orchestration (launch subagents, batch ordering)
2. Gate enforcement (run tests + lint between batches)
3. Quick fixes (lint auto-fix, minor import typos)
4. Task tracking
5. User communication

Everything else = delegate to subagents that read/write files directly.
