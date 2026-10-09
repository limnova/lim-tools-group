"""Check or sync the explicitly shared Claude/Codex configuration (Python 3.11+)."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib

from run_mcp import VARIABLE


ROOT = Path(__file__).resolve().parents[1]
ENV_REF = re.compile(r'^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def toml_value(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return '[' + ', '.join(toml_value(item) for item in value) + ']'
    if isinstance(value, dict):
        return '{ ' + ', '.join(f'{toml_value(k)} = {toml_value(v)}' for k, v in value.items()) + ' }'
    raise ValueError('Unsupported TOML value type')


def patch_mcp_toml(source, servers):
    """Replace named MCP tables only; preserve all unrelated settings and comments."""
    parsed = tomllib.loads(source)
    changed = {name: value for name, value in servers.items()
               if parsed.get('mcp_servers', {}).get(name) != value}
    if not changed:
        return source
    parts = re.split(r'(?m)^(?=\[)', source)
    kept = []
    removed = set()
    for part in parts:
        header = part.splitlines()[0] if part else ''
        try:
            table = tomllib.loads(header).get('mcp_servers', {})
        except tomllib.TOMLDecodeError:
            table = {}
        if set(table) & changed.keys():
            removed.update(set(table) & changed.keys())
        else:
            kept.append(part)
    existing = set(parsed.get('mcp_servers', {})) & changed.keys()
    if existing - removed:
        raise ValueError('MCP tables must use [mcp_servers.NAME] syntax before syncing')
    output = ''.join(kept).rstrip() + '\n\n'
    for name, value in changed.items():
        output += f'[mcp_servers.{toml_value(name)}]\n'
        output += ''.join(f'{toml_value(k)} = {toml_value(v)}\n' for k, v in value.items()) + '\n'
    expected = dict(parsed)
    expected['mcp_servers'] = {**parsed.get('mcp_servers', {}), **servers}
    if tomllib.loads(output) != expected:
        raise ValueError('TOML update would change unrelated configuration')
    return output


def claude_to_codex(server):
    """Convert supported project fields; reject unsupported fields instead of losing them."""
    transport = server.get('type', 'stdio')
    allowed = {'type', 'command', 'args', 'env'} if transport == 'stdio' else {'type', 'url', 'headers'}
    if transport not in ('stdio', 'http') or set(server) - allowed:
        raise ValueError('Unsupported Claude MCP transport or fields')
    result = {k: v for k, v in server.items() if k != 'type'}
    if transport == 'http':
        if 'headers' in result:
            result['http_headers'] = result.pop('headers')
        if '${' in json.dumps(result):
            raise ValueError('HTTP environment expansion requires explicit Codex configuration')
    else:
        if not server.get('command'):
            raise ValueError('STDIO MCP requires a command')
        literals, inherited = {}, []
        for key, value in result.pop('env', {}).items():
            match = ENV_REF.fullmatch(value)
            if match and match.group(1) == key:
                inherited.append(key)
            elif '${' in value:
                raise ValueError('Only same-name environment references can be converted')
            else:
                literals[key] = value
        if '${' in json.dumps(result):
            raise ValueError('Command/argument environment expansion cannot be copied to Codex')
        if literals:
            result['env'] = literals
        if inherited:
            result['env_vars'] = inherited
    return result


def codex_to_claude(server):
    # Keep Codex timeouts, tool filters and approval settings in Codex itself.
    if server.get('enabled') is False:
        raise ValueError('Disabled Codex server cannot be enabled in Claude implicitly')
    if 'command' in server:
        if server.get('cwd') or server.get('experimental_environment'):
            raise ValueError('Codex working directory/remote execution requires a Claude adapter')
        result = {'type': 'stdio', 'command': server['command'], 'args': server.get('args', [])}
        env = dict(server.get('env', {}))
        for name in server.get('env_vars', []):
            if not isinstance(name, str):
                raise ValueError('Remote environment forwarding cannot be converted')
            env.setdefault(name, '${' + name + '}')
        if env:
            result['env'] = env
        return result
    raise ValueError('Personal sync currently supports STDIO servers only')


def project_server(server, root, name):
    if server.get('type', 'stdio') == 'stdio' and '${' in json.dumps(server):
        if set(server) - {'type', 'command', 'args', 'env'}:
            raise ValueError('Unsupported Claude MCP fields')
        variables = sorted({match.group(1) for match in VARIABLE.finditer(json.dumps(server))})
        return {
            'command': sys.executable,
            'args': [str(root / 'scripts/run_mcp.py'), '--config', str(root / '.mcp.json'), '--server', name],
            'env_vars': variables,
        }
    return claude_to_codex(server)


class Plan:
    def __init__(self, backup_root):
        self.backup_root = backup_root
        self.writes = {}
        self.originals = {}

    def write(self, path, content):
        path = Path(path).absolute()
        original = path.read_bytes() if path.exists() else None
        if original != content:
            self.writes[path] = content
            self.originals[path] = original

    def apply(self):
        # Detect edits made while planning, before touching any destination.
        for path, original in self.originals.items():
            current = path.read_bytes() if path.exists() else None
            if current != original:
                raise ValueError(f'File changed during planning: {path}')
        if not self.writes:
            return
        self.backup_root.mkdir(parents=True, exist_ok=False)
        manifest = []
        for index, (path, original) in enumerate(self.originals.items()):
            backup = f'{index:04d}.bak' if original is not None else None
            if backup:
                (self.backup_root / backup).write_bytes(original)
            manifest.append({'path': str(path), 'backup': backup})
        (self.backup_root / 'manifest.json').write_bytes(json_bytes(manifest))
        for path, content in self.writes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                tmp.write(content)
                temporary = Path(tmp.name)
            try:
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)


def sync_skills(plan, source, destination, excluded=()):
    entries = sorted(source.glob('*/SKILL.md'))
    if not entries:
        raise ValueError(f'No source skills found: {source}')
    for entry in entries:
        if entry.parent.name.startswith('.') or entry.parent.name in excluded:
            continue
        for path in sorted(entry.parent.rglob('*')):
            if path.is_file() and not {'.git', '__pycache__'} & set(path.parts):
                plan.write(destination / path.relative_to(source), path.read_bytes())


def build_plan(root, home, personal=False):
    policy = read_json(root / '.agents/sync.json')
    plan = Plan(home / '.agents/backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    plugins = read_json(root / '.claude/settings.json').get('enabledPlugins', {})
    excluded = policy['claude_plugin_skills']
    for skill, plugin in excluded.items():
        if not plugins.get(plugin):
            raise ValueError(f'Claude plugin for {skill} is not enabled: {plugin}')
    sync_skills(plan, root / '.agents/skills', root / '.claude/skills', excluded)
    mcp_path = root / '.mcp.json'
    if mcp_path.exists():
        servers = {name: project_server(value, root, name) for name, value in read_json(mcp_path)['mcpServers'].items()}
        codex_path = root / '.codex/config.toml'
        source = codex_path.read_text('utf-8-sig') if codex_path.exists() else ''
        plan.write(codex_path, patch_mcp_toml(source, servers).encode('utf-8'))
    else:
        print('Project MCP not configured; see .mcp.example.json')
    if personal:
        sync_skills(plan, home / '.codex/skills', home / '.claude/skills')
        source = home / '.codex/AGENTS.md'
        plan.write(home / '.claude/CLAUDE.md', source.read_bytes())
        config = tomllib.loads((home / '.codex/config.toml').read_text('utf-8-sig'))
        claude_path = home / '.claude.json'
        claude = read_json(claude_path)
        before = json_bytes(claude)
        for name in policy['personal_mcp_servers']:
            server = config.get('mcp_servers', {}).get(name)
            if server is None:
                raise ValueError(f'Missing personal Codex MCP: {name}')
            claude.setdefault('mcpServers', {})[name] = codex_to_claude(server)
        if before != json_bytes(claude):
            plan.write(claude_path, json_bytes(claude))
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Report drift without writes (default)')
    mode.add_argument('--apply', action='store_true', help='Back up and apply changes')
    parser.add_argument('--personal', action='store_true', help='Also sync personal skills, rules and allowlisted MCPs')
    args = parser.parse_args()
    try:
        plan = build_plan(ROOT, Path.home(), args.personal)
        counts = {}
        for path in plan.writes:
            label = 'personal' if path.is_relative_to(Path.home()) else 'project'
            counts[label] = counts.get(label, 0) + 1
        print('Files needing sync:', counts or 'none')
        if args.apply:
            plan.apply()
            if plan.writes:
                print('Backup:', plan.backup_root)
            print('Sync complete')
            return 0
        return 1 if plan.writes else 0
    except (json.JSONDecodeError, tomllib.TOMLDecodeError):
        # Parser messages may include credential-bearing source text.
        print('Sync stopped: invalid JSON/TOML; check configuration syntax.', file=sys.stderr)
        return 2
    except ValueError as error:
        print(f'Sync stopped: {error}', file=sys.stderr)
        return 2
    except (KeyError, OSError) as error:
        print(f'Sync stopped ({type(error).__name__}); check source files and required fields.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
