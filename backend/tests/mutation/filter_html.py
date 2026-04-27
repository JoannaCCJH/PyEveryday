#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def filter_per_file(html: str) -> str:
    return re.sub(r'<h2>Skipped</h2>.*?(?=</body>)', '', html, flags=re.DOTALL)


_ROW_RE = re.compile(
    r'<tr><td><a href="([^"]+)">([^<]+)</a></td>'
    r'<td>(\d+)</td><td>(\d+)</td><td>(\d+)</td><td>([0-9.]+)</td><td>(\d+)</td>'
)


def filter_index(html: str) -> str:
    html = html.replace('<th>Skipped</th>', '')

    totals = {'effective': 0, 'killed': 0}

    def fix_row(m):
        href, name, total, skipped, killed, _pct, survived = m.groups()
        effective = int(total) - int(skipped)
        new_pct = (int(killed) / effective * 100) if effective else 0.0
        totals['effective'] += effective
        totals['killed'] += int(killed)
        return (f'<tr><td><a href="{href}">{name}</a></td>'
                f'<td>{effective}</td><td>{killed}</td>'
                f'<td>{new_pct:.2f}</td><td>{survived}</td>')

    html = _ROW_RE.sub(fix_row, html)

    if totals['effective']:
        html = re.sub(
            r'Killed \d+ out of \d+ mutants',
            f"Killed {totals['killed']} out of {totals['effective']} mutants",
            html,
        )
    return html


def main():
    if len(sys.argv) != 2:
        print('Usage: filter_html.py <html_dir>', file=sys.stderr)
        sys.exit(64)

    html_dir = Path(sys.argv[1])
    if not html_dir.is_dir():
        print(f'Not a directory: {html_dir}', file=sys.stderr)
        sys.exit(1)

    index_path = html_dir / 'index.html'
    for path in html_dir.rglob('*.html'):
        text = path.read_text()
        if path.resolve() == index_path.resolve():
            text = filter_index(text)
        else:
            text = filter_per_file(text)
        path.write_text(text)


if __name__ == '__main__':
    main()
