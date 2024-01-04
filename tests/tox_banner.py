import platform

import bug_trail_core

print(f"{platform.python_implementation()} {platform.python_version()}; bug_trail_core {bug_trail_core.__version__}")
