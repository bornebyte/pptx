# MCP icons and metadata

The `/mcp` endpoint is implemented in the existing Flask JSON-RPC handler. This repository does not depend on or pin the official Python `mcp` SDK; there is no installed MCP SDK version to report. The implementation follows the wire schemas in the current MCP specification (`2026-07-28`) while retaining the `2025-11-25` and earlier initialize flows already supported by this app. The official Python SDK documents the same `icons` metadata model in its [server media guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/servers/media.md).

## Discovery and icon URLs

MCP does not define a separate HTTP well-known URL for server branding. Clients discover the server through the standard protocol:

- `initialize` returns `serverInfo` for legacy protocol versions. The `icons`, `title`, `description`, and `websiteUrl` fields are included only when the client negotiates `2025-11-25` or later.
- `server/discover` returns the current implementation metadata under `_meta["io.modelcontextprotocol/serverInfo"]` for `2026-07-28` clients.
- `tools/list` includes an `icons` entry on `generate_ppt` when the negotiated protocol version supports it.

The icon is served from `GET https://<same-host>/mcp/icon.png`. The handler is public and does not require OAuth credentials, returns `image/png`, allows anonymous cross-origin image fetches, validates the bundled image as a 128×128 PNG under 1 MiB, and sets a one-day public cache lifetime with stale-while-revalidate. Set the canonical public application URL before deploying:

```dotenv
PUBLIC_BASE_URL=https://your-public-host.example
```

Only an absolute HTTPS value is used to construct icon and website URLs. If it is missing or invalid, icon and website URL fields are omitted; this avoids deriving public metadata from an untrusted request `Host` header. Ensure the MCP endpoint and `/mcp/icon.png` are served through the same public authority. Existing MCP tool behavior is unchanged.

The protocol defines `icons` as optional metadata. The icon field uses the standardized `src`, `mimeType`, and `sizes` members; clients may ignore it without affecting tool discovery or invocation. The PNG is used instead of SVG for broad rendering support and to avoid SVG script handling concerns.

## Client behavior

Automatic icon display depends on each host, not just on protocol conformance. These statuses reflect vendor documentation reviewed on 2026-11-10; “undocumented” means there is no verified vendor statement that the client renders protocol icon metadata, not proof that it never does.

| Client or provider | MCP connection documented | Automatic protocol icon display | Practical setup |
| --- | --- | --- | --- |
| VS Code with GitHub Copilot | Yes | **Documented.** VS Code says it adopted SEP-973 server, resource, and tool icons. For HTTP MCP servers, the icon must use the same authority as the server. | Add the MCP URL in VS Code; keep `PUBLIC_BASE_URL` on the same authority. |
| ChatGPT / OpenAI MCP API | Yes | **Undocumented for remote MCP metadata.** OpenAI documents MCP tool discovery, but its remote-server guide does not promise `serverInfo.icons` rendering. ChatGPT plugin packages have a separate `composerIcon` asset. | Configure the remote MCP server; use the plugin package’s icon configuration when publishing through that separate plugin workflow. |
| Claude Desktop, Claude Code, Claude.ai | Yes | **Undocumented.** Anthropic documents MCP connections, but the reviewed connection docs do not confirm automatic rendering of protocol icons. | Add the server through the client’s MCP configuration. Treat any branded listing icon as client/catalog configuration. |
| Cursor | Yes | **Undocumented.** Cursor documents MCP transports, server setup, and image results, but not automatic `serverInfo.icons` rendering. | Configure the server in Cursor; do not rely on its UI showing the protocol icon. |
| Windsurf / Devin Desktop | Yes | **Undocumented.** Vendor MCP setup documentation describes server configuration but does not promise protocol icon rendering. | Configure the server in the MCP panel/configuration file; icon display may depend on the client version. |
| Gemini API / Gemini-based clients | Yes for the Gemini Interactions API remote MCP feature | **Undocumented.** Google documents the MCP server name and URL inputs, but not display of protocol icon metadata. Other Gemini-based clients have their own MCP implementations. | Supply the server name and URL in the client configuration. |
| Other MCP clients | Varies | **Client-specific.** The MCP spec makes icons optional, so a client can be fully compatible while ignoring them. | Configure the server normally; provide a manual catalog/listing icon if that client offers one. |

Sources: [MCP 2026-07-28 schema](https://modelcontextprotocol.io/specification/2026-07-28/schema), [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle), [VS Code MCP specification update](https://code.visualstudio.com/updates/v1_105), [OpenAI MCP server guide](https://developers.openai.com/api/docs/guides/tools-connectors-mcp), [OpenAI plugin icon field](https://developers.openai.com/plugins/build/plugins), [Anthropic MCP docs](https://docs.anthropic.com/en/docs/mcp), [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol), [Gemini remote MCP docs](https://ai.google.dev/gemini-api/docs/function-calling).

## Authentication boundary

This app currently exposes `/mcp` without OAuth, as documented in the main README. The icon is served by a separate public route and is not tied to MCP tool authorization. If OAuth protection is added to MCP later, keep `/mcp/icon.png` publicly reachable so clients can load it before or during connection setup.
