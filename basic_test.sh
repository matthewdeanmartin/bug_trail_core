# usage: code_tags [-h] [--format {text,html,json,keep-a-changelog}] module
#
#TODOs in source code as a first class construct (v0.1.0)
#
#positional arguments:
#  module                Python module to inspect (e.g., 'my_project.main')
#
#options:
#  -h, --help            show this help message and exit
#  --format {text,html,json,keep-a-changelog}
#                        Output format for the report.
set -e
bug_trail_core
bug_trail_core --version
bug_trail_core --show-config pyproject.toml

