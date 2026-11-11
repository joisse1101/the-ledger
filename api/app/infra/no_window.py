"""The one definition of the flag that stops a process this backend starts from opening a console
window. Pass it as `creationflags=NO_WINDOW` on every `subprocess` call."""

import subprocess

# Zero off Windows, where the constant does not exist and there is no console window to hide.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
