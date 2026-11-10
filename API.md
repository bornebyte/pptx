# PPT Generator API Documentation

This document describes all API endpoints, request/response formats, and supported query parameters.

## Base URL
- Local: `http://localhost:5000`

## Authentication
Some endpoints require an API key if `ADMIN_API_KEY` is set in the server environment.

Accepted headers:
- `X-API-Key: <key>`
- `Authorization: Bearer <key>`

If `ADMIN_API_KEY` is not set, these endpoints are open.

---

## 1) Health

### GET `/health`

**Description**: Health check endpoint.

**Auth**: Not required.

**Response**
```json
{
  "status": "healthy",
  "service": "ppt-generator",
  "version": "1.0.0"
}
```

---

## 2) Generate PPT

### POST `/generate_ppt`

**Description**: Generates a PPTX from JSON content. Tracks generation data in the database.

**Auth**: Not required.

**Content-Type**: `application/json`

**Request Body**
```json
{
  "file_name": "presentation",
  "json_data": "{ ... }",
  "jain_data": {
    "enabled": true,
    "type": "single",
    "college_name": "College Name",
    "title": "Presentation Title",
    "student_name": "Student Name",
    "usn": "USN123",
    "course": "BCA",
    "semester": "5th",
    "professor": "Prof Name"
  }
}
```

**Notes**
- `json_data` must be a stringified JSON with `meta` and `slides`.
- `jain_data` is optional. If `enabled=true`, it is stored in DB and used for a college title slide.
- For `type=group`, use:
```json
{
  "enabled": true,
  "type": "group",
  "college_name": "College Name",
  "title": "Presentation Title",
  "students": [
    {"name": "Student A", "usn": "USN1"},
    {"name": "Student B", "usn": "USN2"}
  ],
  "professor": "Prof Name"
}
```

**Response**
- Success: `200` with a downloadable `.pptx` file.
- Errors: JSON error payload with `error` field.

---

## 3) MCP Server

### POST `/mcp`

**Description**: Stateless Streamable HTTP MCP endpoint for ChatGPT, Claude, and other MCP clients. Supports the 2025 Streamable HTTP versions and the 2026-07-28 request-metadata format.

**MCP tool**: `generate_ppt`

Tool arguments:
- `presentation` (required object): same JSON format used by `/generate_ppt`, with `meta` and `slides`.
- `file_name` (optional string): desired file name without `.pptx`.
- `jain_data` (optional object): same academic title slide information accepted by `/generate_ppt`.

Successful tool results include a Markdown download link and structured content:
```json
{
  "generation_id": 42,
  "file_name": "quarterly-review.pptx",
  "download_url": "https://your-domain.example/downloads/<opaque-token>",
  "download_markdown": "[Download quarterly-review.pptx](https://your-domain.example/downloads/<opaque-token>)"
}
```

MCP calls create the same `generations` and `students` records as web requests. The PPTX bytes are stored in the additive `generated_files` table and served by `GET /downloads/<opaque-token>`, so download links work across app workers and restarts as long as the configured database persists.

Set `PUBLIC_BASE_URL` to the public HTTPS base URL when the app runs behind a reverse proxy or hosting platform. `MCP_ALLOWED_ORIGINS` adds exact comma-separated browser origins allowed to call `/mcp`; ChatGPT and Claude web origins are allowed by default. MCP clients without an `Origin` header can connect directly.

---

## 4) Generations List (Advanced Filters)

### GET `/api/generations`

**Description**: List generation records with advanced filtering, sorting, and pagination.

**Auth**: Required if `ADMIN_API_KEY` is set.

**Query Parameters**

Pagination:
- `limit` (int, default `50`, max `200`)
- `offset` (int, default `0`)

Payload control:
- `include_students` (`true|false`, default `true`) - include student list in each record

Text filters (case-insensitive, partial match):
- `file_name`
- `title`
- `subtitle`
- `college_name`
- `presentation_title`
- `course`
- `semester`
- `professor_name`
- `ip`
- `user_agent`
- `error_message`
- `content_summary`

Exact-match filters:
- `status` (e.g., `success`, `failed`, `processing`)
- `student_type` (`single` | `group`)

Boolean filters:
- `has_tables` (`true|false`)
- `has_images` (`true|false`)
- `has_charts` (`true|false`)

Range filters:
- `min_slides`, `max_slides` (int)
- `min_file_size`, `max_file_size` (int, bytes)
- `min_time`, `max_time` (float, seconds)

Date/time filters (ISO 8601):
- `start` (e.g., `2025-01-01` or `2025-01-01T10:30:00`)
- `end` (e.g., `2025-12-31` or `2025-12-31T23:59:59`)

Global search:
- `q` (searches in: `file_name`, `title`, `subtitle`, `college_name`, `presentation_title`, `professor_name`, `content_summary`)

Student filters:
- `student_name` (partial match)
- `student_usn` (partial match)

Sorting:
- `sort_by` one of: `timestamp`, `file_name`, `title`, `num_slides`, `file_size`, `generation_time`, `status`, `college_name`
- `sort_dir` (`asc` | `desc`, default `desc`)

**Response**
```json
{
  "total": 123,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "timestamp": "2025-01-01T12:34:56.123456",
      "file_name": "presentation",
      "title": "Intro",
      "subtitle": "Overview",
      "num_slides": 10,
      "file_size": 123456,
      "college_name": "College Name",
      "presentation_title": "Title",
      "student_type": "single",
      "course": "BCA",
      "semester": "5th",
      "professor_name": "Prof Name",
      "ip_address": "127.0.0.1",
      "user_agent": "...",
      "generation_time": 1.23,
      "status": "success",
      "error_message": null,
      "content_summary": null,
      "has_tables": false,
      "has_images": false,
      "has_charts": false,
      "students": [
        {"id": 1, "name": "Student Name", "usn": "USN123"}
      ]
    }
  ]
}
```

---

## 5) Generation Detail

### GET `/api/generations/<id>`

**Description**: Fetch a single generation record by ID.

**Auth**: Required if `ADMIN_API_KEY` is set.

**Path Params**
- `id` (int)

**Response**
Same shape as a single item in the list endpoint.

---

## 6) Export (Admin-Only API Endpoint)

### GET `/api/generations/export`

**Description**: Export generation records with the same filters as `/api/generations`. Not exposed in frontend.

**Auth**: Required if `ADMIN_API_KEY` is set.

**Query Parameters**
All query parameters from `/api/generations` are supported, plus:
- `format` (`csv` | `json`, default `csv`)
- `limit` (int, default `5000`, max `10000`)
- `offset` (int, default `0`)

**Response**
- `format=csv`: returns `text/csv` file download
- `format=json`: JSON payload

**CSV Columns**
- `id`, `timestamp`, `file_name`, `title`, `subtitle`, `num_slides`, `file_size`,
  `college_name`, `presentation_title`, `student_type`, `course`, `semester`,
  `professor_name`, `ip_address`, `user_agent`, `generation_time`, `status`,
  `error_message`, `content_summary`, `has_tables`, `has_images`, `has_charts`,
  `student_names`, `student_usns` (if `include_students=true`)

---

## Common Error Responses

### 400 Bad Request
```json
{ "error": "Invalid format. Use csv or json." }
```

### 401 Unauthorized
```json
{ "error": "Unauthorized" }
```

### 404 Not Found
Returned when an ID does not exist.

---

## Quick Examples

List filtered by college and date range:
```
GET /api/generations?college_name=Jain&start=2025-01-01&end=2025-12-31
```

Filter by student name and min slides, sorted by slides desc:
```
GET /api/generations?student_name=Rahul&min_slides=10&sort_by=num_slides&sort_dir=desc
```

Export CSV without students:
```
GET /api/generations/export?include_students=false
```
