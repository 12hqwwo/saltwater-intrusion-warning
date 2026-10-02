# Security rules

- Never commit API keys, PostgreSQL passwords, tokens, or `.env`.
- Do not print full API keys in debug output.
- Use environment variables or local-only settings.
- Treat MRC license/receipt files as source evidence; do not modify them.
- Keep `.claude/settings.local.json` local-only.
- Do not run `git push`, `git reset --hard`, `git clean -fd`, destructive SQL, or database
  drops without explicit user approval.
- SQL generated from external text must use safe literal handling / parameters.
- DB migrations must guard `current_database()`.
- Keep raw data immutable; corrected/derived versions go to interim/processed layers.
- Do not use model output as an operational gate command. Human approval remains required.
