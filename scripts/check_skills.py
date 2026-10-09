"""Check shared skill copies and relative Markdown file references."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote


def check_skills(root: Path) -> list[str]:
    canonical = root / '.agents' / 'skills'
    compatibility = root / '.claude' / 'skills'
    errors = []
    for file in sorted(compatibility.rglob('*')):
        if not file.is_file():
            continue
        peer = canonical / file.relative_to(compatibility)
        if not peer.is_file():
            errors.append(f'Missing canonical file: {peer.relative_to(root)}')
        elif file.read_bytes().replace(b'\r\n', b'\n') != peer.read_bytes().replace(b'\r\n', b'\n'):
            errors.append(f'Shared copies differ: {file.relative_to(compatibility)}')

    # Check entrypoints and their actual Markdown links, not example paths in code blocks.
    for entry in sorted(canonical.glob('*/SKILL.md')):
        source = entry.read_text(encoding='utf-8')
        if not re.match(r'^---\r?\n', source):
            errors.append(f'Missing frontmatter: {entry.relative_to(root)}')
        prose = re.sub(r'```.*?```', '', source, flags=re.DOTALL)
        prose = re.sub(r'`+[^`]*`+', '', prose)
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', prose):
            target = target.split('#', 1)[0]
            if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('/'):
                continue
            if not (entry.parent / unquote(target)).exists():
                errors.append(f'Broken link in {entry.relative_to(root)}: {target}')
    if not list(canonical.glob('*/SKILL.md')):
        errors.append('No project skill entrypoints found')
    return errors


if __name__ == '__main__':
    problems = check_skills(Path(__file__).resolve().parents[1])
    for problem in problems:
        print(problem)
    if problems:
        sys.exit(1)
    print('Skill checks passed: shared copies match and entrypoint links resolve')
