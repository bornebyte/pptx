# PowerPoint Generator

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A Flask application for creating PowerPoint presentations from JSON. Generate files in the web interface, through the HTTP API, or from an AI client connected to the remote MCP server.

## Features

- Generate `.pptx` files from JSON presentations.
- Format headings, paragraphs, bullets, numbered lists, tables, text boxes, and images.
- Add academic title slides for individual or group projects.
- Connect ChatGPT, Claude, or another remote MCP client to generate a presentation and receive a download link.
- Store generation analytics and MCP download files in the configured SQL database.

## Quick Start

Requirements: Python 3.10+ and Git. uv is recommended; pip is also supported.

```bash
git clone https://github.com/bornebyte/ppt-generator.git
cd ppt-generator
uv sync
uv run python main.py
```

If you prefer pip, create the same `.venv` environment and install from `requirements.txt`:

```bash
# Linux or macOS
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

On Windows, use `py -m venv .venv`, then `.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.venv\Scripts\python.exe main.py`. The launchers use the environment interpreter directly, so they work whether uv or pip created the environment.

Open <http://localhost:5000>. Application code, templates, and static assets live under `src/`; examples are in `src/examples/`. The root `main.py` is a compatibility entry point for Vercel and existing launch commands. Installers are grouped under `installers/`, app launchers under `launchers/`, and setup/maintenance utilities under `scripts/`.

Run `./installers/install.sh` on Linux/macOS, `installers\\install.bat` in Windows Command Prompt, or `installers\\install.ps1` in PowerShell. To launch a checkout that already has a virtual environment, use `./launchers/pptgen`, `launchers\\pptgen.bat`, or `launchers\\pptgen.ps1` for your shell. The installer also provides a `pptgen` command after setup.

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

Supported content block kinds include `heading`, `paragraph`, `bullets`, `numbered_list`, `table`, `text_box`, and `images`. See [the enhanced example](src/examples/example_enhanced.json) for a larger example.

## Remote MCP Server

Deploy this app to a publicly reachable HTTPS host, then connect an MCP client to:

```text
https://your-domain.example/mcp
```

In ChatGPT, choose **No authentication** for this server. The current endpoint is unauthenticated and does not implement OAuth; OAuth metadata discovery URLs therefore return 404. `ADMIN_API_KEY` only protects admin analytics APIs, not `/mcp`.

The `generate_ppt` tool accepts a `presentation` object with `meta` and `slides`, plus optional `file_name` and `academic_details`. Every content slide must have a title and at least one substantive body block. When academic details are supplied, the title slide is enabled automatically and defaults to single-student mode; group mode is used only when explicitly requested or multiple presenters are supplied. A requested total slide count includes the cover slide. The tool returns a download link and generation ID. MCP requests use the same generation and student analytics records as web requests. The PPTX is stored in the `generated_files` database table and downloaded from `/downloads/<token>`.

The endpoint supports 2025 Streamable HTTP clients and the 2026-07-28 request-metadata format. MCP generations and download links persist across restarts when `DATABASE_URL` points to a persistent database.

The MCP server advertises its public PNG icon and standardized metadata to protocol versions that support icons. Set `PUBLIC_BASE_URL` to the public HTTPS origin so MCP clients can fetch the icon at `/mcp/icon.png`. Client rendering varies; see [MCP icons and metadata](docs/mcp-icons.md) for verified provider differences and manual setup notes.

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

For a production WSGI server, install the requirements with either package manager, then run:

```bash
.venv/bin/python -m gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 main:app
```

On serverless hosting, configure a persistent external SQL database. The default local SQLite database is not suitable for storing data across independent serverless instances.

The Linux/macOS and Windows installers prefer uv when it is installed and fall back to pip otherwise. Both install dependencies into `.venv`; you can also manage dependencies manually with `uv sync` or `python -m pip install -r requirements.txt`.

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
