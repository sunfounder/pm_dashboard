# Change log

## 1.3.18
- Fix path traversal in log file APIs (CVE-2026-25069): validate filename for get-log and delete-log-file
- Harden API: mask secrets in get-config, whitelist history keys, restrict CORS to same-origin
