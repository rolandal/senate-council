---
pack: models
mode: models
resolved_at: 2026-06-25
description: >
  Mode 1 roster — the latest flagship model per lab, resolved live from the OpenRouter
  catalog by scripts/resolve_models.py. Re-run `python3 scripts/resolve_models.py --write
  --date <YYYY-MM-DD>` to refresh. Chair = Claude Opus (native).
---

# Models Roster (resolved 2026-06-25)

| Seat | OpenRouter model id | Lab |
|------|---------------------|-----|
| GPT 5.5 pro | `openai/gpt-5.5-pro` | openai |
| Gemini 3.1 pro preview | `google/gemini-3.1-pro-preview` | google |
| Grok 4.3 | `x-ai/grok-4.3` | x-ai |
| Claude opus 4.8 fast | `anthropic/claude-opus-4.8-fast` | anthropic |
| DeepSeek v4 pro | `deepseek/deepseek-v4-pro` | deepseek |

**Chairman:** Claude Opus (native `Agent`, not OpenRouter).

```json
{
  "resolved_at": "2026-06-25",
  "seats": [
    {
      "vendor": "openai",
      "model_id": "openai/gpt-5.5-pro",
      "label": "GPT 5.5 pro"
    },
    {
      "vendor": "google",
      "model_id": "google/gemini-3.1-pro-preview",
      "label": "Gemini 3.1 pro preview"
    },
    {
      "vendor": "x-ai",
      "model_id": "x-ai/grok-4.3",
      "label": "Grok 4.3"
    },
    {
      "vendor": "anthropic",
      "model_id": "anthropic/claude-opus-4.8-fast",
      "label": "Claude opus 4.8 fast"
    },
    {
      "vendor": "deepseek",
      "model_id": "deepseek/deepseek-v4-pro",
      "label": "DeepSeek v4 pro"
    }
  ],
  "chair": {
    "label": "Claude Opus",
    "native": true
  }
}
```
