from html.parser import HTMLParser
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent'))

from telegram_render import telegram_html_parts

class Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
    def handle_starttag(self, tag, attrs):
        assert tag in {'b','i','s','a','code','pre','blockquote'}
        self.stack.append(tag)
        if tag == 'a':
            assert dict(attrs)['href'].startswith(('https://','http://'))
    def handle_endtag(self, tag):
        assert self.stack and self.stack.pop() == tag


def test_markdown_tags_and_escaping():
    parts = telegram_html_parts('## Test **strong** _italic_ `x < 10`\n\n```python\nprint("hello")\n```\n[website](https://example.com/?x=1&y=2)')
    whole = '\n'.join(parts)
    assert '<b>' in whole and '<i>' in whole and '<pre>' in whole
    assert '&lt; 10' in whole
    assert 'https://example.com/?x=1&amp;y=2' in whole
    for part in parts:
        parser = Checker()
        parser.feed(part)
        assert not parser.stack


def test_markdown_long_code_chunks():
    parts = telegram_html_parts('```python\n' + ('print(42)\n' * 1400) + '```', limit=2800)
    assert len(parts) > 2
    for part in parts:
        assert len(part) < 3500
        parser = Checker()
        parser.feed(part)
        assert not parser.stack


def test_link_scheme_rejection():
    html = ''.join(telegram_html_parts('[click](javascript:alert(1)) **safe** <script>'))
    assert '<a ' not in html
    assert '<script>' not in html
    assert '&lt;script&gt;' in html
