"""`cx edit` — open ~/.cxrc.toml in $EDITOR."""
from __future__ import annotations

import os
import shlex

from .. import output
from ..config import Config


def run(config: Config) -> int:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    argv = shlex.split(editor) + [str(config.path)]
    output.exec_in(os.getcwd(), argv)
    return 0
