#!/usr/bin/env python3
"""Matrix compatibility entry: standby is observed, legacy effects are refused.

The full generated W-C3 suite owns heartbeat preservation, upgrade and detector
coverage. Reuse its guarded scratch fixture for this existing matrix entry.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent/'tests'))
from test_liveness import Liveness

if __name__=='__main__':
    suite=unittest.TestSuite(Liveness(name) for name in (
        'test_t4_process_exact_identity_interactive_and_idle_standby',
        'test_t6_alias_and_legacy_action_migration'))
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
