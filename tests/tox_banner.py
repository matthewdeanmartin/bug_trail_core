import platform

import bug_trail_core

print(
    "{} {}; bug_trail_core {}".format(
        platform.python_implementation(),
        platform.python_version(),
        bug_trail_core.__version__,
    )
)
