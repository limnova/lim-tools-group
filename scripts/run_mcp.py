"""Launch a project STDIO MCP with Claude-style environment expansion."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


VARIABLE = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}')


def expand(value, environment):
    def replace(match):
        name, default = match.groups()
        if name in environment:
            return environment[name]
        if default is not None:
            return default
        raise ValueError(f'Missing environment variable: {name}')
    return VARIABLE.sub(replace, value)


def command_for(server, environment):
    if server.get('type', 'stdio') != 'stdio':
        raise ValueError('Launcher only supports STDIO MCP')
    command = expand(server['command'], environment)
    args = [expand(value, environment) for value in server.get('args', [])]
    child_env = dict(environment)
    child_env.update({key: expand(value, environment) for key, value in server.get('env', {}).items()})
    return [command, *args], child_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--server', required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.config.read_text('utf-8-sig'))
        command, environment = command_for(data['mcpServers'][args.server], os.environ)
        executable = shutil.which(command[0])
        if executable is None:
            print('MCP executable is unavailable; check command/PATH.', file=sys.stderr)
            return 2
        command[0] = executable
        # Inherit streams so stdout contains only the child's MCP protocol.
        child = subprocess.Popen(command, env=environment, cwd=args.config.resolve().parent)
        try:
            return child.wait()
        except KeyboardInterrupt:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            return 130
    except ValueError as error:
        message = str(error)
        print(message if message.startswith('Missing environment variable: ') else 'Invalid MCP configuration.', file=sys.stderr)
        return 2
    except (KeyError, OSError):
        print('Unable to start MCP; check configuration and executable.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
