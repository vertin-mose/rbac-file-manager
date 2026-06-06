---
name: readme-sync-policy
description: README.md must be updated whenever code changes, and after every git pull to ensure documentation matches actual system state.
metadata:
  type: feedback
---

After every code change that affects functionality, update the corresponding sections in README.md. After every `git pull`, review the pulled changes and update README.md to match.

**Why:** Previous README had multiple inconsistencies with the actual system (e.g., claimed ADMIN has `system:backup` when it doesn't, wrong SQLAlchemy model counts). User explicitly requires README to be the single source of truth.

**How to apply:** Every time you make a code modification (API routes, permissions, security features, database schema, frontend components, Docker config), check if the README's corresponding section needs updating. After any `git pull`, read the diff to identify what changed and reflect those changes in the README.
