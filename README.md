# PowerPoint Generator

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A Flask application for creating PowerPoint presentations from JSON. Generate files in the web interface, through the HTTP API, or from an AI client connected to the remote MCP server.

## Features

- Generate `.pptx` files from JSON presentations.
- Format headings, paragraphs, bullets, numbered lists, tables, text boxes, and images.
- Add academic title slides for individual or group projects.
- Connect ChatGPT, Claude, or another remote MCP client to generate a presentation and receive a download link.
- Store generation analytics and MCP download files in the configured SQL database.

## Quick Start

Requirements: Python 3.8+, pip, and Git.

```bash
git clone https://github.com/bornebyte/ppt-generator.git
cd ppt-generator
python -m venv .venv
```

Activate the virtual environment, then install dependencies and start the app:

```bash
# Linux or macOS
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

On Windows, activate with `.venv\Scripts\activate` (PowerShell) or `.venv\Scripts\activate.bat` (Command Prompt), then run the same `pip` and Python commands.

Open <http://localhost:5000>. The app uses `content.json` as its example presentation. The `pptgen`, `pptgen.bat`, and `pptgen-launcher.py` launchers are also available.

## Create a Presentation

In the web interface, paste presentation JSON, enter a file name, and select **Generate PPT**. The basic format is:

```json
{
  "meta": {
    "title": "Quarterly Review",
    "subtitle": "Q3 results"
  },
  "slides": [
    {
      "type": "content",
      "title": "Highlights",
      "blocks": [
        {"kind": "paragraph", "text": "A short introduction."},
        {"kind": "bullets", "items": ["Revenue grew 12%", "Retention improved"]}
      ],
      "notes": "Optional speaker notes."
    }
  ]
}
```

Supported content block kinds include `heading`, `paragraph`, `bullets`, `numbered_list`, `table`, `text_box`, and `images`. See `example_enhanced.json` for a larger example.

## Remote MCP Server

Deploy this app to a publicly reachable HTTPS host, then connect an MCP client to:

```text
https://your-domain.example/mcp
```

The `generate_ppt` tool accepts a `presentation` object with `meta` and `slides`, plus an optional `file_name` and `jain_data`. It returns a download link and generation ID. MCP requests use the same generation and student analytics records as web requests. The PPTX is stored in the `generated_files` database table and downloaded from `/downloads/<token>`.

The endpoint supports 2025 Streamable HTTP clients and the 2026-07-28 request-metadata format. MCP generations and download links persist across restarts when `DATABASE_URL` points to a persistent database.

## Configuration and Deployment

Copy `.env.example` to `.env` and update the values for your environment. Important settings:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQL database URL for analytics and stored MCP files. |
| `SECRET_KEY` | Flask session signing key. Set a unique value in production. |
| `PUBLIC_BASE_URL` | Public HTTPS base URL used to construct MCP download links. Set this behind a proxy or hosting platform. |
| `MCP_ALLOWED_ORIGINS` | Optional comma-separated browser origins permitted to call `/mcp`. ChatGPT and Claude web origins are allowed by default. |
| `PORT` | HTTP port; defaults to `5000`. |
| `MAX_CONTENT_LENGTH` | Maximum request size in bytes; defaults to 16 MiB. |

For local/container deployment, Docker Compose mounts `./instance` so the SQLite database persists:

```bash
docker compose up --build
```

For a production WSGI server, install the requirements and run:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 main:app
```

On serverless hosting, configure a persistent external SQL database. The default local SQLite database is not suitable for storing data across independent serverless instances.

## HTTP Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Web interface. |
| `GET` | `/health` | Health check. |
| `POST` | `/generate_ppt` | Generate and directly download a PPTX. |
| `POST` | `/mcp` | MCP protocol endpoint for AI clients. |
| `GET` | `/downloads/<token>` | Download an MCP-generated PPTX. |
| `GET` | `/api/generations` | List generation analytics. |
| `GET` | `/api/generations/<id>` | Get a generation record. |
| `GET` | `/api/generations/export` | Export generation analytics. |
| `POST` | `/api/feedback` | Submit feedback. |

Admin analytics endpoints can require `ADMIN_API_KEY` when it is configured.

## License

This project is licensed under the [MIT License](LICENSE).

## Maintainer

Created by [Shubham Shah](https://github.com/bornebyte).
