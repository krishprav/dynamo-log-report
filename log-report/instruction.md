There is an Apache-style access log at `/app/access.log`. Each non-blank line is one HTTP request. Parse the log and write a JSON summary report to `/app/report.json`.

For each line, treat the first whitespace-separated field as the client IP. Extract the request path from the quoted request line in the form `"METHOD /path HTTP/x.x"`. Skip blank lines.

The report must be valid JSON with exactly these keys:
- `total_requests` — integer count of non-blank log lines
- `unique_ips` — integer count of distinct client IPs
- `top_path` — string path with the highest request count

Success criteria:
1. `/app/report.json` exists.
2. The file contains valid JSON with exactly the keys `total_requests`, `unique_ips`, and `top_path` (no extra keys).
3. `total_requests` equals 6.
4. `unique_ips` equals 3.
5. `top_path` equals `"/index.html"`.
