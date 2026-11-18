"""Safe Markdown -> Telegram HTML. No raw HTML from the model is trusted."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from markdown_it import MarkdownIt

# Parsing raw HTML is intentionally disabled. Telegram supports only a small subset.
MD = MarkdownIt("commonmark", {"html": False, "linkify": False}).enable("table")


@dataclass(frozen=True)
class Span:
    text: str
    styles: tuple[tuple[str, str], ...] = ()


def _safe_link(href: str) -> str | None:
    if not href or len(href) > 1500:
        return None
    try:
        parsed = urlparse(href)
    except ValueError:
        return None
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        return None
    if any(c in href for c in '\r\n\x00'):
        return None
    return href


def _append(spans: list[Span], text: str, styles: list[tuple[str, str]]) -> None:
    if text:
        spans.append(Span(text, tuple(styles)))


def markdown_spans(markdown: str) -> list[Span]:
    """Extract text and styling using a real Markdown token parser."""
    spans: list[Span] = []
    stack: list[tuple[str, str]] = []
    list_stack: list[dict] = []

    def push(tag: str, attr: str = ""):
        stack.append((tag, attr))

    def pop(tag: str):
        for idx in range(len(stack) - 1, -1, -1):
            if stack[idx][0] == tag:
                del stack[idx:]
                return

    for tok in MD.parse(markdown):
        typ = tok.type
        if typ == "heading_open":
            push("b")
        elif typ == "heading_close":
            pop("b")
            _append(spans, "\n\n", stack)
        elif typ == "blockquote_open":
            push("blockquote")
        elif typ == "blockquote_close":
            pop("blockquote")
            _append(spans, "\n", stack)
        elif typ in ("bullet_list_open", "ordered_list_open"):
            list_stack.append({"ordered": typ == "ordered_list_open", "i": int(tok.attrGet("start") or 1)})
        elif typ in ("bullet_list_close", "ordered_list_close"):
            if list_stack:
                list_stack.pop()
            _append(spans, "\n", stack)
        elif typ == "list_item_open":
            if list_stack:
                item = list_stack[-1]
                prefix = f"{item['i']}. " if item["ordered"] else "• "
                _append(spans, "  " * (len(list_stack) - 1) + prefix, stack)
                item["i"] += 1
        elif typ == "list_item_close":
            _append(spans, "\n", stack)
        elif typ == "paragraph_close":
            if not list_stack:
                _append(spans, "\n\n", stack)
        elif typ == "fence" or typ == "code_block":
            lang = re.match(r"[A-Za-z0-9_+.-]{1,24}", (tok.info or "").strip())
            code_attrs = f'class="language-{lang.group(0)}"' if lang else ""
            _append(spans, tok.content.rstrip("\n"), stack + [("pre", ""), ("code", code_attrs)])
            _append(spans, "\n\n", stack)
        elif typ == "hr":
            _append(spans, "────────\n", stack)
        elif typ == "inline":
            inline_stack = stack.copy()
            for child in tok.children or []:
                t = child.type
                if t == "text":
                    _append(spans, child.content, inline_stack)
                elif t in ("softbreak", "hardbreak"):
                    _append(spans, "\n", inline_stack)
                elif t == "code_inline":
                    _append(spans, child.content, inline_stack + [("code", "")])
                elif t in ("strong_open", "em_open", "s_open"):
                    inline_stack.append(({"strong_open":"b", "em_open":"i", "s_open":"s"}[t], ""))
                elif t in ("strong_close", "em_close", "s_close"):
                    tag = {"strong_close":"b", "em_close":"i", "s_close":"s"}[t]
                    for i in range(len(inline_stack) - 1, -1, -1):
                        if inline_stack[i][0] == tag:
                            del inline_stack[i:]
                            break
                elif t == "link_open":
                    url = _safe_link(child.attrGet("href") or "")
                    if url:
                        inline_stack.append(("a", f'href="{html.escape(url, quote=True)}"'))
                elif t == "link_close":
                    if inline_stack and inline_stack[-1][0] == "a":
                        inline_stack.pop()
                elif t == "image":
                    _append(spans, child.content or "Изображение", inline_stack)
                elif t == "html_inline":
                    _append(spans, child.content, inline_stack)
        elif typ == "table_open":
            _append(spans, "\n", stack)
        elif typ == "tr_close":
            _append(spans, "\n", stack)
        elif typ == "th_close" or typ == "td_close":
            _append(spans, "  │  ", stack)
    return spans


def _style_html(styles: tuple[tuple[str, str], ...]) -> tuple[str, str]:
    open_tags = "".join(f"<{tag}{(' ' + attr) if attr else ''}>" for tag, attr in styles)
    close_tags = "".join(f"</{tag}>" for tag, _ in reversed(styles))
    return open_tags, close_tags


def telegram_html_parts(markdown: str, limit: int = 2800) -> list[str]:
    """Split at visible text boundaries; each chunk has balanced HTML tags."""
    if limit < 100:
        raise ValueError("limit too small")
    output: list[str] = []
    current: list[str] = []
    length = 0
    active: tuple[tuple[str, str], ...] = ()

    def close_current() -> None:
        nonlocal current, length, active
        if length == 0:
            return
        _, close_tags = _style_html(active)
        content = ("".join(current) + close_tags).strip()
        if content:
            output.append(content)
        current = []
        length = 0
        active = ()

    for span in markdown_spans(markdown):
        text = span.text
        while text:
            if length >= limit:
                close_current()
            if span.styles != active:
                _, close_tags = _style_html(active)
                current.append(close_tags)
                open_tags, _ = _style_html(span.styles)
                current.append(open_tags)
                active = span.styles
            free = limit - length
            piece = text[:free]
            current.append(html.escape(piece, quote=False))
            length += len(piece)
            text = text[len(piece):]
            if text:
                close_current()
    close_current()
    return output or ["Ответ пуст."]
