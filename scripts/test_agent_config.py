"""Regression checks using temporary config trees; never reads personal credentials."""

import json
from pathlib import Path
import tempfile
import tomllib
import unittest

from run_mcp import command_for

from check_skills import check_skills
from sync_agent_config import Plan, claude_to_codex, codex_to_claude, patch_mcp_toml, sync_skills


class ConfigTests(unittest.TestCase):
    def test_launcher_expands_default_and_keeps_parent_environment(self):
        source = {'command': 'tool', 'args': ['${HOST:-127.0.0.1}', '${PASSWORD}'], 'env': {'MODE': '${MODE:-restricted}'}}
        parent = {'PASSWORD': 'synthetic-test-value', 'PATH': 'keep'}
        command, env = command_for(source, parent)
        self.assertEqual(command, ['tool', '127.0.0.1', 'synthetic-test-value'])
        self.assertEqual(env['MODE'], 'restricted')
        self.assertEqual(env['PATH'], 'keep')
        self.assertNotIn('MODE', parent)
        with self.assertRaisesRegex(ValueError, '^Missing environment variable: PASSWORD$'):
            command_for(source, {})

    def test_toml_preserves_unrelated_tables_and_runtime(self):
        source = '''# user settings
model = "keep-model"
[mcp_servers.node_repl]
command = "runtime"
[mcp_servers."sample".env]
OLD = "old"
[features]
enabled = true
'''
        servers = {'sample': {'command': 'C:\\tools\\mcp.exe', 'args': ['--read-only'], 'env': {'X': 'a"b\\c\n'}}}
        result = patch_mcp_toml(source, servers)
        parsed = tomllib.loads(result)
        self.assertEqual(parsed['model'], 'keep-model')
        self.assertEqual(parsed['mcp_servers']['node_repl'], {'command': 'runtime'})
        self.assertTrue(parsed['features']['enabled'])
        self.assertEqual(parsed['mcp_servers']['sample'], servers['sample'])
        self.assertTrue(result.startswith('# user settings'))
        self.assertEqual(patch_mcp_toml(result, servers), result)

    def test_environment_round_trip_keeps_references_not_secrets(self):
        server = {'type': 'stdio', 'command': 'tool', 'args': [], 'env': {'TOKEN': '${TOKEN}', 'BASE': 'literal'}}
        converted = claude_to_codex(server)
        self.assertEqual(converted['env_vars'], ['TOKEN'])
        self.assertNotIn('TOKEN', converted['env'])
        self.assertEqual(codex_to_claude(converted), server)

    def test_unsupported_conversion_fails_closed(self):
        for server in [
            {'type': 'sse', 'url': 'https://example.test'},
            {'command': 'tool', 'env': {'TOKEN': '${DIFFERENT}'}},
            {'command': 'tool', 'args': ['${TOKEN}']},
            {'command': 'tool', 'unexpected': True},
        ]:
            with self.subTest(server=server), self.assertRaises(ValueError):
                claude_to_codex(server)
        for extra in [{'enabled': False}, {'cwd': '/other'}, {'env_vars': [{'name': 'X', 'source': 'remote'}]}]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                codex_to_claude({'command': 'tool', **extra})

    def test_dry_run_backup_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'config.json'
            target.write_bytes(b'original')
            new_file = root / 'new/skill.md'
            plan = Plan(root / 'backup')
            plan.write(target, b'updated')
            plan.write(new_file, b'new')
            self.assertEqual(target.read_bytes(), b'original')
            self.assertFalse(new_file.exists())
            plan.apply()
            manifest = json.loads((root / 'backup/manifest.json').read_text())
            self.assertEqual((root / 'backup' / manifest[0]['backup']).read_bytes(), b'original')
            self.assertIsNone(manifest[1]['backup'])
            self.assertEqual(target.read_bytes(), b'updated')
            again = Plan(root / 'unused-backup')
            again.write(target, b'updated')
            again.apply()
            self.assertFalse((root / 'unused-backup').exists())

    def test_concurrent_edit_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'config'
            path.write_bytes(b'before')
            plan = Plan(root / 'backup')
            plan.write(path, b'ours')
            path.write_bytes(b'user edit')
            with self.assertRaises(ValueError):
                plan.apply()
            self.assertEqual(path.read_bytes(), b'user edit')

    def test_skill_copy_preserves_local_extras_and_skips_system(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['one', '.system']:
                entry = root / 'source' / name / 'SKILL.md'
                entry.parent.mkdir(parents=True)
                entry.write_text('skill')
            extra = root / 'dest/custom/SKILL.md'
            extra.parent.mkdir(parents=True)
            extra.write_text('custom')
            plan = Plan(root / 'backup')
            sync_skills(plan, root / 'source', root / 'dest')
            plan.apply()
            self.assertTrue((root / 'dest/one/SKILL.md').exists())
            self.assertFalse((root / 'dest/.system').exists())
            self.assertEqual(extra.read_text(), 'custom')

    def test_checker_detects_missing_copy_and_plugin_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ['.agents/skills/shared', '.agents/skills/design', '.claude/skills/shared']:
                (root / folder).mkdir(parents=True)
            (root / '.agents/sync.json').write_text(json.dumps({'claude_plugin_skills': {'design': 'design@official'}}))
            (root / '.claude/settings.json').write_text(json.dumps({'enabledPlugins': {'design@official': True}}))
            source = '---\nname: sample\ndescription: example\n---\n'
            for folder in ['.agents/skills/shared', '.agents/skills/design', '.claude/skills/shared']:
                (root / folder / 'SKILL.md').write_text(source)
            self.assertEqual(check_skills(root), [])
            (root / '.agents/skills/shared/reference.md').write_text('new reference')
            self.assertTrue(any('Missing Claude compatibility' in e for e in check_skills(root)))
            (root / '.claude/settings.json').write_text('{}')
            self.assertTrue(any('plugin not enabled' in e for e in check_skills(root)))


if __name__ == '__main__':
    unittest.main()
