# Flip the spine to private (10 minutes, do when postmortem data accumulates)
1. GitHub repo -> Settings -> General -> Danger Zone -> Change visibility -> Private.
2. Create token: Settings (profile) -> Developer settings -> Fine-grained tokens -> Generate.
   Repository access: only sports-intel-spine. Permissions: Contents = Read-only. 90-day expiry; calendar the renewal.
3. GPT Action changes:
   - Server URL becomes https://api.github.com/repos/OWNER/sports-intel-spine/contents
   - Auth: API Key, header name "Authorization", value "Bearer <token>"
   - Add header "Accept: application/vnd.github.raw+json" per operation.
4. Re-run the eval battery (docs section in DEPLOYMENT_PLAN) to confirm identical behavior.
