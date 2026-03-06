# MCP Server Connection Guide

This guide explains how to connect **MCP (Model Context Protocol) servers**
to the Football Odds Analysis project so that AI assistants (GitHub Copilot,
VS Code Copilot Chat, and other MCP-compatible tools) can interact with your
data sources.

---

## What Is MCP?

The **Model Context Protocol** is an open standard that lets AI assistants
communicate with external data sources and tools through a unified interface.
By configuring MCP servers you give your AI assistant access to live odds
data, databases, or custom analytics endpoints without hard-coding secrets
into your source code.

---

## Quick Start

### 1. Set Up Environment Variables

All secrets are stored in a `.env` file (never committed to Git).
Copy the example and fill in your real keys:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
# The-Odds-API key (required for live odds fetching)
ODDS_API_KEY=your_actual_api_key_here

# Optional: Google Stitch MCP API key
# Only needed if you want to connect the Google Stitch MCP server
GOOGLE_STITCH_API_KEY=your_google_stitch_api_key_here
```

### 2. VS Code / GitHub Copilot MCP Configuration

The repository includes a template at `.vscode/mcp.json`.
This file references environment variables so that **no secrets** are stored
in source control.

```jsonc
// .vscode/mcp.json (already included in the repo)
{
  "servers": {
    "football-odds-api": {
      "type": "http",
      "url": "https://api.the-odds-api.com/v4/sports/",
      "headers": {
        "Content-Type": "application/json"
      },
      "env": {
        "ODDS_API_KEY": "${ODDS_API_KEY}"
      }
    }
  }
}
```

### 3. Adding a Custom MCP Server (e.g., Google Stitch)

To connect an additional MCP server such as Google Stitch, add a new entry
to `.vscode/mcp.json`:

```jsonc
{
  "servers": {
    "football-odds-api": {
      "type": "http",
      "url": "https://api.the-odds-api.com/v4/sports/",
      "headers": {
        "Content-Type": "application/json"
      },
      "env": {
        "ODDS_API_KEY": "${ODDS_API_KEY}"
      }
    },
    "stitch": {
      "type": "http",
      "url": "https://stitch.googleapis.com/mcp",
      "headers": {
        "X-Goog-Api-Key": "${GOOGLE_STITCH_API_KEY}"
      }
    }
  }
}
```

> **⚠️ Security Note:** Never paste a raw API key into `mcp.json`.
> Always use `${ENV_VAR}` references and store the real value in `.env`
> (which is git-ignored).

---

## Supported MCP Server Types

| Type    | Description                                    |
| ------- | ---------------------------------------------- |
| `http`  | Connects over HTTPS to a remote MCP endpoint   |
| `stdio` | Launches a local process and communicates via standard I/O |
| `sse`   | Connects via Server-Sent Events                |

---

## Security Best Practices

1. **Never commit secrets.** API keys belong in `.env` (listed in
   `.gitignore`) or a secrets manager — never in source code or JSON
   config files.
2. **Use environment variable references.** MCP configs support `${VAR}`
   syntax so the tool reads the value at runtime.
3. **Rotate keys regularly.** If a key is accidentally exposed, revoke it
   immediately and generate a new one.
4. **Least privilege.** Use read-only API keys where possible.

---

## Troubleshooting

| Symptom | Possible Cause | Fix |
| ------- | -------------- | --- |
| `401 Unauthorized` | Missing or invalid API key | Verify `.env` contains the correct key |
| `Connection refused` | Wrong URL or server offline | Check the URL in `mcp.json` |
| `Timeout` | Network issue or slow endpoint | Check your network and firewall settings; if the MCP client supports a timeout option, increase it |
| AI assistant can't find server | `mcp.json` not in `.vscode/` | Move the file to `.vscode/mcp.json` |

---

## Further Reading

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [VS Code MCP Support](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)
- [The-Odds-API Documentation](https://the-odds-api.com/liveapi/guides/v4/)
