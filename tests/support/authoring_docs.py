"""Read the Markdown headings and code fences used by the authoring guides."""

import re
from collections import Counter


def headings(text):
    seen = Counter()
    fence = False
    result = []
    for line in text.splitlines():
        if line.startswith('```'):
            fence = not fence
        elif not fence and (match := re.match(r'^(#{1,6}) (.+)$', line)):
            title = match[2]
            anchor = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
            number = seen[anchor]
            seen[anchor] += 1
            result.append((title, anchor + (f'-{number}' if number else '')))
    return result


def anchors(text):
    return {anchor for _, anchor in headings(text)} | set(re.findall(r'<a id="([^"]+)"></a>', text))


def fences(text):
    return re.findall(r'^```([^\n]*)\n(.*?)^```\s*$', text, re.MULTILINE | re.DOTALL)
