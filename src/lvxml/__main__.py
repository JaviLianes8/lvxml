"""Allow ``python -m lvxml`` as an alternative to the ``lvxml`` command."""

from __future__ import annotations

import sys

from ._cli import main

sys.exit(main())
