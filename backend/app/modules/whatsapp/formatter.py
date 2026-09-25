"""
WhatsApp message formatter.

Converts LLM/Markdown output to WhatsApp-compatible formatting syntax.

WhatsApp formatting reference:
- *text*     → bold
- _text_     → italic
- ~text~     → strikethrough
- ```text``` → monospace
"""

import re
from typing import Optional


def clean_markdown_for_whatsapp(text: str) -> str:
    """
    Convert Markdown/LLM output to WhatsApp-compatible format.

    Conversion table:
      **text** / __text__  →  *text*    (bold)
      *text* / _text_      →  _text_    (italic)
      ~~text~~             →  ~text~    (strikethrough)
      `code`               →  ```code```
      ```block```          →  ```block``` (unchanged)
      # Heading            →  *Heading*
      - item / * item      →  • item
      [text](url)          →  text (url)
      ---                  →  (removed)
      3+ blank lines       →  2 blank lines
    """
    if not text:
        return text

    # ── 1. Remove HTML tags ───────────────────────────────────────────────────
    text = re.sub(r"<[^>]+>", "", text)

    # ── 2. Protect existing triple-backtick code blocks ──────────────────────
    # Extract them, replace with placeholders so nothing else mangles them.
    code_blocks: list[str] = []

    def stash_code_block(m: re.Match) -> str:
        code_blocks.append(m.group(0))
        return f"\x00CODEBLOCK{len(code_blocks) - 1}\x00"

    text = re.sub(r"```[\s\S]*?```", stash_code_block, text)

    # ── 3. Convert Markdown links: [text](url) → text (url) ──────────────────
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

    # ── 4. Bold: **text** and __text__ → WhatsApp *text* ─────────────────────
    # Use a placeholder to avoid confusing single-* italic detection later.
    bold_spans: list[str] = []

    def stash_bold(m: re.Match) -> str:
        bold_spans.append(m.group(1))
        return f"\x00BOLD{len(bold_spans) - 1}\x00"

    text = re.sub(r"\*\*(.+?)\*\*", stash_bold, text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__", stash_bold, text, flags=re.DOTALL)

    # ── 5. Italic: remaining *text* and _text_ → WhatsApp _text_ ─────────────
    # At this point any remaining *x* is italic (bold was stashed above).
    text = re.sub(r"\*([^*\n]+?)\*", r"_\1_", text)
    # _text_ in Markdown is already _ so it stays as-is (correct for WhatsApp)

    # ── 6. Restore bold placeholders as WhatsApp *text* ──────────────────────
    for i, content in enumerate(bold_spans):
        text = text.replace(f"\x00BOLD{i}\x00", f"*{content}*")

    # ── 7. Strikethrough: ~~text~~ → ~text~ ──────────────────────────────────
    text = re.sub(r"~~(.+?)~~", r"~\1~", text, flags=re.DOTALL)

    # ── 8. Inline code: `code` → ```code``` ──────────────────────────────────
    # (triple-backtick blocks are stashed so this only hits single backticks)
    text = re.sub(r"`([^`\n]+)`", r"```\1```", text)

    # ── 9. Restore code blocks ────────────────────────────────────────────────
    for i, block in enumerate(code_blocks):
        text = text.replace(f"\x00CODEBLOCK{i}\x00", block)

    # ── 10. Headers: # Heading → *Heading* ───────────────────────────────────
    text = re.sub(r"^#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # ── 11. Horizontal rules → remove ────────────────────────────────────────
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # ── 12. Bullet lists: - item / * item → • item ────────────────────────────
    text = re.sub(r"^[ \t]*[-*]\s+", "• ", text, flags=re.MULTILINE)

    # ── 13. Clean up excess blank lines ──────────────────────────────────────
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ── Legacy helpers kept for backwards compatibility ───────────────────────────


def format_for_whatsapp(text: str) -> str:
    """Alias for clean_markdown_for_whatsapp (legacy name)."""
    return clean_markdown_for_whatsapp(text)


def add_whatsapp_emoji_formatting(text: str) -> str:
    """Placeholder for future emoji enhancements."""
    return text


def preserve_existing_whatsapp_format(text: str) -> str:
    """Safety no-op: returns text unchanged."""
    return text
