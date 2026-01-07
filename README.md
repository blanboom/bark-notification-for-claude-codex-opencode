# Bark Notification for [Claude Code](https://code.claude.com/docs/en/overview)/[Codex CLI](https://github.com/openai/codex)/[OpenCode](https://opencode.ai)

Send push notifications to your iOS device via [Bark](https://github.com/Finb/Bark) when your AI coding agents complete tasks.

## Background

I use CLI-based AI coding agents during fragmented time slots (e.g., on the subway, waiting in line, before bed) by SSH-ing into my iMac from an iPhone or iPad. These agents help me add new features to [HEIF & HEVC Converter](https://apps.apple.com/app/heif-hevc-converter/id6744530166). I wanted to receive task completion notifications instantly on my mobile device, without constantly watching the terminal.

## Features

- **Unified Script**: One script works seamlessly with Claude Code, Codex CLI, and OpenCode
- **End-to-End Encryption**: Uses modern AES-256-GCM encryption, ensuring neither Apple nor the Bark server can read your notification content

## Prerequisites

- Python 3.x
- [Bark](https://apps.apple.com/app/id1403753865) app installed on iOS
- `cryptography` library: `pip install cryptography` (or `brew install cryptography` on macOS)

## Setup

### 1. Configure Bark Encryption

1. Open Bark app on your iOS device
2. Go to **Servers** > **Encryption Settings**
3. Choose **Algorithm**: `AES256GCM`
4. Set a **32-character key** and **12-character IV**
5. Copy your Bark push URL (e.g., `https://api.day.app/YOUR_DEVICE_KEY`)

### 2. Configure the Script

Edit `notify_claude_codex_bark.py` and update these constants:

```python
BARK_BASE = "https://api.day.app/YOUR_DEVICE_KEY"
ENCRYPTION_KEY = "your-32-character-encryption-key"
ENCRYPTION_IV = "your-12char-iv"
```

### 3. Configure Your Coding Agent

#### Claude Code

Edit `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Notification": [
      {
        "hooks": [
          {
            "command": "python3 /path/to/notify_claude_codex_bark.py",
            "type": "command"
          }
        ],
        "matcher": ""
      }
    ]
  }
}
```

#### Codex CLI

Edit `~/.codex/config.toml`:

```toml
notify = ["python3", "/path/to/notify_claude_codex_bark.py"]
```

#### OpenCode

OpenCode uses a plugin-based approach. Create a file at `~/.config/opencode/plugin/notify.ts`:

```typescript
import type { Plugin } from "@opencode-ai/plugin";

const NOTIFY_SCRIPT = "/Users/blanboom/.codex/notify_claude_codex_bark.py";

const plugin: Plugin = async ({ client, $ }) => {
  const notify = (type: string, message: string) => {
    const payload = JSON.stringify({ title: "OpenCode", type, message });
    $`echo ${payload} | python3 ${NOTIFY_SCRIPT}`.quiet().catch(() => {});
  };

  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        const { sessionID } = event.properties;
        const sessions = await client.session.list({ limit: 50 });
        const session = sessions.data?.find((s: { id: string }) => s.id === sessionID);
        if (!session || session.parentID) return;

        notify("session.idle", session.title || "Task completed");
      }

      if (event.type === "permission.asked") {
        const { permission, patterns } = event.properties;
        const detail = patterns.length ? `: ${patterns.join(", ")}` : "";
        notify("permission.asked", `${permission}${detail}`);
      }
    },
  };
};

export default plugin;

```

## How It Works

The script automatically detects which tool triggered the notification based on the payload structure:

- **Claude Code**: Identified by `hook_event_name`, `session_id`, or `transcript_path` fields
- **OpenCode**: Identified by session-related events or `OpenCode` in the title
- **Codex CLI**: Default fallback for other payloads

Each notification displays:
- Tool-specific title and icon
- Event type as subtitle
- Last assistant message or event summary as body

## Security

All notification content is encrypted locally using AES-256-GCM before transmission. The encryption ensures:

- Apple Push Notification service cannot read the content
- Bark server stores only encrypted data
- Only your device with the matching key can decrypt notifications

## Disclaimer

This README, script, and configuration files were generated with AI assistance. The author confirms that they are fully functional and actively in use.
