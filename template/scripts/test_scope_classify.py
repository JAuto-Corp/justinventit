"""Exercise the actual scope classifier against disposable Git history and an authored config."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

_HERE = Path(__file__).resolve()
CLI = next((c for c in (_HERE.with_name("scope-classify.py"), _HERE.parent.parent / "scope-classify.py") if c.is_file()), _HERE.with_name("scope-classify.py"))
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_TERMINAL_PROMPT="0")

CONFIG = {
    "schema_version": 1,
    "file_count_threshold": 4,
    "standard_triggers": [
        {"name": "migration-added", "pattern": "^supabase/migrations/.*\\.sql$", "status": "added"},
        {"name": "api-route-added", "pattern": "^src/app/api/.*/route\\.ts$", "status": "added"},
        {"name": "page-touched", "pattern": "^src/app/.*/page\\.tsx$"},
        {"name": "infra-touched", "pattern": "^\\.github/(workflows|actions)/"},
    ],
    "executable_class": {"pattern": "^(scripts/|\\.claude/hooks/|\\.github/(workflows|actions)/|[^/]*Dockerfile)", "exclude_pattern": "\\.md$"},
    "tooling": {
        "config_path": "scripts/scope-classes.json",
        "denylist": "^(src/|supabase/|\\.github/|\\.claude/hooks/|package\\.json$|.*Dockerfile$)",
        "consumer_roots": ["src", "tests", ".github", ".claude", "scripts", ":(glob,top)package.json", ":(glob,top)Makefile", ":(glob,top)**/Dockerfile*"],
        "product_import_patterns": ["^\\s*(from|import)\\s+(src|app)\\b"],
        "inventory": [{"helper": "scripts/helper.py", "test": "scripts/tests/helper.test.py"}],
    },
}


class ScopeClassifyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "T")
        self.config = Path(self.tmp.name) / "scope-classes.json"
        self.config.write_text(json.dumps(CONFIG), encoding="utf-8")
        self.write("README.md", "seed")
        self.write("src/lib/util.ts", "export const a = 1;\n")
        self.write("scripts/helper.py", "print('helper v1')\n")
        self.write("scripts/tests/helper.test.py", "import unittest\n")
        self.write("scripts/scope-classes.json", json.dumps(CONFIG))
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], env=ENV, stderr=subprocess.STDOUT).decode().strip()

    def write(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "change", "--allow-empty")
        return self.git("rev-parse", "HEAD")

    def run_cli(self, *args, cwd=None):
        cmd = [sys.executable, str(CLI), "--config", str(self.config), "--repo", str(self.repo), *args]
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or self.tmp.name), env=ENV, timeout=60)

    def classify(self, *extra):
        head = self.commit()
        r = self.run_cli(*extra, "%s..%s" % (self.base, head))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.splitlines()[0]

    def test_no_changes_is_quick(self):
        self.assertEqual(self.classify(), "class=Quick reason=no-changes")

    def test_single_source_edit_is_quick_by_heuristic(self):
        self.write("src/lib/util.ts", "export const a = 2;\n")
        self.assertEqual(self.classify(), "class=Quick reason=quick-by-heuristic")

    def test_added_migration_and_route_trigger_standard_plus(self):
        self.write("supabase/migrations/001.sql", "select 1;")
        self.write("src/app/api/x/route.ts", "export {}")
        line = self.classify()
        self.assertTrue(line.startswith("class=Standard+ reason="), line)
        self.assertIn("migration-added", line)
        self.assertIn("api-route-added", line)

    def test_added_only_triggers_ignore_modifications(self):
        self.write("supabase/migrations/001.sql", "select 1;")
        self.base = self.commit()
        self.write("supabase/migrations/001.sql", "select 2;")
        self.assertEqual(self.classify(), "class=Quick reason=quick-by-heuristic")

    def test_file_count_threshold(self):
        for i in range(4):
            self.write("src/lib/f%d.ts" % i, "x")
        self.assertEqual(self.classify(), "class=Standard+ reason=files-4")

    def test_executable_file_outside_inventory_is_standard_plus_with_refusal_trace(self):
        self.write("scripts/other.sh", "#!/bin/sh\n")
        line = self.classify()
        self.assertTrue(line.startswith("class=Standard+ reason=executable-class,tooling-refused:not-in-inventory:scripts/other.sh"), line)

    def test_markdown_under_executable_dir_is_prose(self):
        self.write("scripts/README.md", "docs")
        self.assertEqual(self.classify(), "class=Quick reason=quick-by-heuristic")

    def test_inventoried_helper_with_its_test_is_tooling(self):
        self.write("scripts/helper.py", "print('helper v2')\n")
        self.write("scripts/tests/helper.test.py", "import unittest\n# v2\n")
        self.assertEqual(self.classify(), "class=Quick(tooling) reason=inventory:2/2,consumers:none,product-import:none,test-in-change")

    def test_helper_without_test_change_is_refused_unless_red_recorded(self):
        self.write("scripts/helper.py", "print('helper v3')\n")
        line = self.classify()
        self.assertIn("tooling-refused:test-not-in-change:scripts/helper.py", line)
        self.assertTrue(line.startswith("class=Standard+"), line)
        self.base = self.git("rev-parse", "HEAD~1")
        r = self.run_cli("--red-recorded", "ledger:red#42", "%s..%s" % (self.base, self.git("rev-parse", "HEAD")))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("class=Quick(tooling) reason=inventory:1/1,consumers:none,product-import:none,red-recorded:scripts/helper.py(ledger:red#42)", r.stdout)

    def test_mixed_change_with_product_path_is_standard_plus(self):
        self.write("scripts/helper.py", "print('helper v2')\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        self.write("src/lib/util.ts", "export const a = 3;\n")
        line = self.classify()
        self.assertTrue(line.startswith("class=Standard+ reason=executable-class,tooling-refused:denylist:src/lib/util.ts"), line)

    def test_consumer_outside_inventory_refuses_tooling(self):
        self.write(".claude/hooks/session-start.sh", "#!/bin/sh\npython3 scripts/helper.py\n")
        self.base = self.commit()
        self.write("scripts/helper.py", "print('helper v2')\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        line = self.classify()
        self.assertIn("tooling-refused:consumer:scripts/helper.py<-.claude/hooks/session-start.sh", line)

    def test_product_import_refuses_tooling(self):
        self.write("scripts/helper.py", "from src.lib import util\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        line = self.classify()
        self.assertIn("tooling-refused:product-import:scripts/helper.py:src.lib.util->src/lib/util.ts", line)

    def test_new_pair_added_with_config_edit_is_tooling(self):
        self.write("scripts/newtool.py", "print('new')\n")
        self.write("scripts/tests/newtool.test.py", "import unittest\n")
        cfg = json.loads(self.config.read_text())
        cfg["tooling"]["inventory"].append({"helper": "scripts/newtool.py", "test": "scripts/tests/newtool.test.py"})
        self.write("scripts/scope-classes.json", json.dumps(cfg))
        self.config.write_text(json.dumps(cfg), encoding="utf-8")  # the loaded config is the HEAD config, as in real use
        line = self.classify()
        self.assertEqual(line, "class=Quick(tooling) reason=inventory:new-pair(scripts/newtool.py),consumers:none,product-import:none,test-in-change")

    def test_unregistered_pair_is_not_tooling(self):
        self.write("scripts/guess.py", "print('x')\n")
        self.write("scripts/tests/guess.test.py", "import unittest\n")
        line = self.classify()
        self.assertIn("tooling-refused:not-in-inventory:scripts/guess.py,scripts/tests/guess.test.py", line)

    def test_any_deletion_is_never_tooling(self):
        (self.repo / "scripts/helper.py").unlink()
        (self.repo / "scripts/tests/helper.test.py").unlink()
        cfg = json.loads(self.config.read_text())
        cfg["tooling"]["inventory"] = []
        self.write("scripts/scope-classes.json", json.dumps(cfg))
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        head = self.commit()
        r = self.run_cli("--red-recorded", "ledger:red#7", "%s..%s" % (self.base, head))
        self.assertIn("tooling-refused:deletion-not-tooling:scripts/helper.py,scripts/tests/helper.test.py", r.stdout)
        self.assertTrue(r.stdout.startswith("class=Standard+"), r.stdout)

    def test_config_change_beyond_inventory_is_standard_plus(self):
        self.write("scripts/scope-classes.json", json.dumps(dict(CONFIG, file_count_threshold=9)))
        line = self.classify()
        self.assertIn("tooling-refused:config-changed:beyond-inventory", line)
        self.assertTrue(line.startswith("class=Standard+"), line)

    def test_paths_from_file_needs_no_git_but_cannot_establish_tooling(self):
        listing = Path(self.tmp.name) / "paths.txt"
        listing.write_text("A\tsupabase/migrations/002.sql\nM\tsrc/lib/util.ts\nR100\told.txt\tnew.txt\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(CLI), "--config", str(self.config), "--paths-from", str(listing), "--json"],
                           capture_output=True, text=True, cwd="/", env=ENV, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        first, rest = r.stdout.split("\n", 1)
        self.assertEqual(first, "class=Standard+ reason=migration-added,files-4")
        data = json.loads(rest)
        self.assertEqual(data["paths"], ["new.txt", "old.txt", "src/lib/util.ts", "supabase/migrations/002.sql"])
        listing.write_text("M\tscripts/helper.py\nM\tscripts/tests/helper.test.py\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(CLI), "--config", str(self.config), "--paths-from", str(listing)],
                           capture_output=True, text=True, cwd="/", env=ENV, timeout=60)
        self.assertEqual(r.stdout.strip(), "class=Standard+ reason=executable-class,tooling-refused:unverifiable:no-repository-head (consumer, import and symlink checks need --repo and --head)")
        self.write("scripts/helper.py", "print('v2')\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        head = self.commit()
        r = self.run_cli("--paths-from", str(listing), "--head", head)
        self.assertEqual(r.stdout.strip(), "class=Quick(tooling) reason=inventory:2/2,consumers:none,product-import:none,test-in-change")

    def test_multiline_product_import_is_caught(self):
        self.write("scripts/helper.py", "#!/usr/bin/env python3\nimport os\nfrom src.lib import util\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        self.assertIn("tooling-refused:product-import:scripts/helper.py:src.lib.util->src/lib/util.ts", self.classify())

    def test_transitive_consumer_through_inventoried_wrapper_is_refused(self):
        cfg = json.loads(self.config.read_text())
        cfg["tooling"]["inventory"].append({"helper": "scripts/wrapper.py", "test": "scripts/tests/wrapper.test.py"})
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        self.write("scripts/scope-classes.json", json.dumps(cfg))
        self.write("scripts/wrapper.py", "import subprocess\nsubprocess.run(['python3', 'scripts/helper.py'])\n")
        self.write("scripts/tests/wrapper.test.py", "# t\n")
        self.write(".github/workflows/ci.yml", "run: python3 scripts/wrapper.py\n")
        self.base = self.commit()
        self.write("scripts/helper.py", "print('v2')\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        line = self.classify()
        self.assertIn("tooling-refused:consumer:scripts/wrapper.py<-.github/workflows/ci.yml", line)  # the transitive hop is named

    def test_module_spelling_and_makefile_dockerfile_consumers_are_refused(self):
        for consumer, text in (("src/lib/use.py", "import scripts.helper\n"), ("Makefile", "run:\n\tpython -m scripts.helper\n"), ("Dockerfile", "RUN python3 scripts/helper.py\n"), ("tests/test_runtime.py", "from scripts import helper\n")):
            self.setUp()
            self.write(consumer, text)
            self.base = self.commit()
            self.write("scripts/helper.py", "print('v2')\n")
            self.write("scripts/tests/helper.test.py", "# v2\n")
            line = self.classify()
            self.assertIn("tooling-refused:consumer:", line, consumer)
            self.assertIn(consumer, line, consumer)

    def test_symlinks_anywhere_refuse_tooling(self):
        (self.repo / "scripts/helper.py").unlink()
        os.symlink("../src/lib/util.ts", self.repo / "scripts/helper.py")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        self.assertIn("tooling-refused:symlink:scripts/helper.py", self.classify())
        self.setUp()
        os.symlink("../../scripts/helper.py", self.repo / ".claude/hooks/run.sh") if (self.repo / ".claude/hooks").mkdir(parents=True) is None else None
        self.base = self.commit()
        self.write("scripts/helper.py", "print('v2')\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        self.assertIn("tooling-refused:symlink-consumer:.claude/hooks/run.sh->../../scripts/helper.py", self.classify())

    def test_deleted_helper_alone_is_refused(self):
        (self.repo / "scripts/helper.py").unlink()
        self.assertIn("tooling-refused:deletion-not-tooling:scripts/helper.py", self.classify())

    def test_symlink_consumer_through_inventoried_wrapper_is_refused(self):
        cfg = json.loads(self.config.read_text())
        cfg["tooling"]["inventory"].append({"helper": "scripts/wrapper.py", "test": "scripts/tests/wrapper.test.py"})
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        self.write("scripts/scope-classes.json", json.dumps(cfg))
        self.write("scripts/wrapper.py", "import subprocess\nsubprocess.run(['python3', 'scripts/helper.py'])\n")
        self.write("scripts/tests/wrapper.test.py", "# t\n")
        (self.repo / ".claude/hooks").mkdir(parents=True)
        os.symlink("../../scripts/wrapper.py", self.repo / ".claude/hooks/run.sh")
        self.base = self.commit()
        self.write("scripts/helper.py", "print('v2')\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        self.assertIn("tooling-refused:symlink-consumer:.claude/hooks/run.sh->../../scripts/wrapper.py", self.classify())

    def test_test_only_deletion_is_refused_and_test_only_edit_is_tooling(self):
        (self.repo / "scripts/tests/helper.test.py").unlink()
        self.assertIn("tooling-refused:deletion-not-tooling:scripts/tests/helper.test.py", self.classify())
        self.setUp()
        self.write("scripts/tests/helper.test.py", "# test-only edit\n")
        self.assertEqual(self.classify(), "class=Quick(tooling) reason=inventory:1/1,consumers:none,product-import:none,test-only:scripts/tests/helper.test.py")

    def test_null_nested_config_sections_cannot_evaluate(self):
        for key, val in (("consumer_roots", None), ("product_import_patterns", None), ("config_path", []), ("inventory", None)):
            cfg = json.loads(json.dumps(CONFIG))
            cfg["tooling"][key] = val
            self.config.write_text(json.dumps(cfg), encoding="utf-8")
            r = self.run_cli("%s..HEAD" % self.base)
            self.assertEqual((r.returncode, r.stdout.startswith("CANNOT-EVALUATE")), (2, True), key)
        self.config.write_text(json.dumps(CONFIG), encoding="utf-8")

    def test_compose_consumer_and_esm_product_import_with_rendered_defaults(self):
        try:
            import jinja2
        except ImportError:
            self.skipTest("jinja2 unavailable")
        src = CLI.with_name("scope-classes.json.jinja")
        if not src.is_file():
            self.skipTest("no jinja source beside the CLI (generated project)")
        cfg = json.loads(jinja2.Environment(keep_trailing_newline=True).from_string(src.read_text()).render(stack="nextjs", database="supabase", use_tds=False))
        cfg["tooling"]["inventory"] = [{"helper": "scripts/h.mjs", "test": "scripts/tests/h.test.mjs"}]
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        self.write("scripts/scope-classes.json", json.dumps(cfg))
        self.write("scripts/h.mjs", "export const x = 1;\n")
        self.write("scripts/tests/h.test.mjs", "import { x } from '../h.mjs';\n")
        self.write("compose.yaml", "services:\n  a:\n    command: node scripts/h.mjs\n")
        self.base = self.commit()
        self.write("scripts/h.mjs", "export const x = 2;\n")
        self.write("scripts/tests/h.test.mjs", "import { x } from '../h.mjs'; // v2\n")
        self.assertIn("tooling-refused:consumer:scripts/h.mjs<-compose.yaml", self.classify())
        (self.repo / "compose.yaml").unlink()
        self.base = self.commit()
        self.write("scripts/h.mjs", "import { product } from '../src/product.mjs';\nexport const x = 3;\n")
        self.write("scripts/tests/h.test.mjs", "// v3\n")
        self.assertIn("tooling-refused:product-import:scripts/h.mjs:", self.classify())

    def test_root_level_app_package_consumer_is_found_with_rendered_defaults(self):
        try:
            import jinja2
        except ImportError:
            self.skipTest("jinja2 unavailable")
        src = CLI.with_name("scope-classes.json.jinja")
        if not src.is_file():
            self.skipTest("no jinja source beside the CLI (generated project)")
        cfg = json.loads(jinja2.Environment(keep_trailing_newline=True).from_string(src.read_text()).render(stack="django", database="sqlite", use_tds=False))
        cfg["tooling"]["inventory"] = [{"helper": "scripts/helper.py", "test": "scripts/tests/helper.test.py"}]
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        self.write("scripts/scope-classes.json", json.dumps(cfg))
        self.write("orders/views.py", "import scripts.helper\n")
        self.write("docs/README.md", "see scripts/helper.py for details\n")
        self.base = self.commit()
        self.write("scripts/helper.py", "print('v2')\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        self.assertIn("tooling-refused:consumer:scripts/helper.py<-orders/views.py", self.classify())
        (self.repo / "orders/views.py").unlink()
        self.base = self.commit()
        self.write("scripts/helper.py", "print('v3')\n")
        self.write("scripts/tests/helper.test.py", "# v3\n")
        self.assertEqual(self.classify(), "class=Quick(tooling) reason=inventory:2/2,consumers:none,product-import:none,test-in-change")

    def test_invalid_historical_config_is_refused_not_crashed(self):
        bad = json.loads(json.dumps(CONFIG))
        bad["tooling"]["inventory"] = None
        self.write("scripts/scope-classes.json", json.dumps(bad))
        self.base = self.commit()
        self.write("scripts/scope-classes.json", json.dumps(CONFIG))
        line = self.classify()
        self.assertTrue(line.startswith("class=Standard+"), line)
        self.assertIn("tooling-refused:config-changed:invalid:", line)

    def test_imports_resolved_against_the_repository_tree(self):
        self.write("orders/__init__.py", "")
        self.write("orders/models.py", "class Order: pass\n")
        self.write("src/lib/thing.mjs", "export const t = 1;\n")
        self.base = self.commit()
        cases = (
            ("from orders.models import Order\n", "product-import:scripts/helper.py:orders.models->orders/models.py"),
            ("import orders\n", "product-import:scripts/helper.py:orders->orders/__init__.py"),
            ("from ..src.lib import thing\n", "product-import:scripts/helper.py:..src.lib.thing->src/lib/thing.mjs"),
            ("from orders import models\n", "product-import:scripts/helper.py:orders.models->orders/models.py"),

            ("import os, json\nfrom scripts import helper\n", None),
            ("import requests\n", None),
        )
        for content, expect in cases:
            self.write("scripts/helper.py", content)
            self.write("scripts/tests/helper.test.py", "# %d\n" % len(content))
            line = self.classify()
            if expect:
                self.assertIn("tooling-refused:" + expect, line, content)
            else:
                self.assertTrue(line.startswith("class=Quick(tooling)"), (content, line))
            self.base = self.git("rev-parse", "HEAD")
        cfg = json.loads(self.config.read_text())
        cfg["tooling"]["inventory"].append({"helper": "scripts/h.mjs", "test": "scripts/tests/h.test.mjs"})
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        self.write("scripts/scope-classes.json", json.dumps(cfg))
        self.write("scripts/h.mjs", "export const x = 1;\n")
        self.write("scripts/tests/h.test.mjs", "import { x } from '../h.mjs';\n")
        self.base = self.commit()
        self.write("scripts/h.mjs", "import { t } from '../src/lib/thing.mjs';\n")
        self.write("scripts/tests/h.test.mjs", "// v2\n")
        self.assertIn("tooling-refused:product-import:scripts/h.mjs:../src/lib/thing.mjs->src/lib/thing.mjs", self.classify())
        self.write("scripts/h.mjs", "import { t } from 'src/lib/thing';\n")
        self.write("scripts/tests/h.test.mjs", "// v3\n")
        self.assertIn("tooling-refused:product-import:scripts/h.mjs:src/lib/thing->src/lib/thing.mjs", self.classify())

    def test_root_module_and_multi_name_imports_and_consumers(self):
        cfg = json.loads(self.config.read_text())
        cfg["tooling"]["consumer_roots"] = [".", ":(exclude,glob)**/*.md"]   # root-level app packages, as the rendered defaults do
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        self.write("scripts/scope-classes.json", json.dumps(cfg))
        self.write("settings.py", "FLAG = 1\n")
        self.write("orders/__init__.py", "")
        self.write("scripts/other.py", "x = 1\n")
        self.base = self.commit()
        for content, expect in (("import settings\n", "settings->settings.py"), ("from settings import FLAG\n", "settings->settings.py"), ("import os, orders\n", "orders->orders/__init__.py"), ("from os import (\n    path,\n    sep,\n)\n", None)):
            self.write("scripts/helper.py", content)
            self.write("scripts/tests/helper.test.py", "# %d\n" % len(content))
            line = self.classify()
            if expect:
                self.assertIn("tooling-refused:product-import:scripts/helper.py:" + expect, line, content)
            else:
                self.assertTrue(line.startswith("class=Quick(tooling)"), (content, line))
            self.base = self.git("rev-parse", "HEAD")
        for consumer_text in ("from scripts import other, helper\n", "from scripts import (\n    other,\n    helper,\n)\n", "import scripts\nscripts.helper\n"):
            self.write("orders/views.py", consumer_text)
            self.base = self.commit()
            self.write("scripts/helper.py", "print(%d)\n" % len(consumer_text))
            self.write("scripts/tests/helper.test.py", "# %d\n" % len(consumer_text))
            self.assertIn("tooling-refused:consumer:scripts/helper.py<-orders/views.py", self.classify(), consumer_text)
        self.write("orders/views.py", "from scripts import other\n")
        self.base = self.commit()
        self.write("scripts/helper.py", "print('unrelated')\n")
        self.write("scripts/tests/helper.test.py", "# u\n")
        line = self.classify()
        self.assertIn("tooling-refused:consumer:scripts/helper.py<-orders/views.py", line)  # v1: a package-level textual reference refuses without confirmation

    def test_ambiguous_consumer_outside_the_package_is_refused(self):
        cfg = json.loads(self.config.read_text())
        cfg["tooling"]["consumer_roots"] = [".", ":(exclude,glob)**/*.md"]
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        self.write("scripts/scope-classes.json", json.dumps(cfg))
        self.write("scripts/settings.py", "TOOL = 'helper'\n")
        self.write("src/consumer.py", "from scripts import settings\nimport importlib\nmodule = importlib.import_module(f'scripts.{settings.TOOL}')\n")
        self.base = self.commit()
        self.write("scripts/helper.py", "print('v2')\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        self.assertIn("tooling-refused:consumer:scripts/helper.py<-src/consumer.py", self.classify())

    def test_sibling_relative_import_consumer_and_bare_sibling_import(self):
        self.write("scripts/runtime.py", "from . import helper\nhelper.run()\n")
        self.write("Makefile", "run:\n\tpython3 -m scripts.runtime\n")
        self.base = self.commit()
        self.write("scripts/helper.py", "print('v2')\n")
        self.write("scripts/tests/helper.test.py", "# v2\n")
        self.assertIn("tooling-refused:consumer:scripts/helper.py<-scripts/runtime.py", self.classify())
        self.write("scripts/runtime.py", "import scripts as s\ns.helper\n")
        self.base = self.commit()
        self.write("scripts/helper.py", "print('v3')\n")
        self.write("scripts/tests/helper.test.py", "# v3\n")
        self.assertIn("tooling-refused:consumer:scripts/helper.py<-scripts/runtime.py", self.classify())
        (self.repo / "scripts/runtime.py").write_text("X = 1\n", encoding="utf-8")
        self.base = self.commit()
        self.write("scripts/helper.py", "import runtime\nprint(runtime.X)\n")
        self.write("scripts/tests/helper.test.py", "# v4\n")
        self.assertIn("tooling-refused:product-import:scripts/helper.py:runtime->scripts/runtime.py", self.classify())

    def test_dynamic_and_unresolved_relative_imports_are_ambiguous_hence_standard_plus(self):
        for i, content in enumerate(("import importlib\nm = importlib.import_module('orders')\n", "mod = __import__('orders')\n", "from . import nothing_here\n")):
            self.write("scripts/helper.py", content)
            self.write("scripts/tests/helper.test.py", "# case %d\n" % i)
            line = self.classify()
            self.assertIn("tooling-refused:product-import:scripts/helper.py:<ambiguous>->dynamic-or-unresolved-relative-import", line, content)
            self.base = self.git("rev-parse", "HEAD")

    def test_failed_tooling_without_executable_trigger_is_still_standard_plus(self):
        cfg = json.loads(self.config.read_text())
        cfg["executable_class"]["pattern"] = "^\\.github/"
        cfg["tooling"]["inventory"] = [{"helper": "tools/h.py", "test": "tools/h.test.py"}]
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        self.write("tools/h.py", "1")
        self.write("tools/h.test.py", "2")
        self.base = self.commit()
        self.write("tools/h.py", "3")
        self.assertEqual(self.classify(), "class=Standard+ reason=tooling-refused:test-not-in-change:tools/h.py")

    def test_unicode_inventory_paths_are_not_false_consumers(self):
        cfg = json.loads(self.config.read_text())
        cfg["tooling"]["inventory"] = [{"helper": "scripts/tööls/helper.py", "test": "scripts/tööls/tests/helper.test.py"}]
        self.config.write_text(json.dumps(cfg), encoding="utf-8")
        self.write("scripts/tööls/helper.py", "print(1)\n")
        self.write("scripts/tööls/tests/helper.test.py", "import scripts.tööls.helper\n")
        self.base = self.commit()
        self.write("scripts/tööls/helper.py", "print(2)\n")
        self.write("scripts/tööls/tests/helper.test.py", "import scripts.tööls.helper  # v2\n")
        self.assertEqual(self.classify(), "class=Quick(tooling) reason=inventory:2/2,consumers:none,product-import:none,test-in-change")

    def test_malformed_configs_cannot_evaluate(self):
        for bad in ({"schema_version": 1}, dict(CONFIG, tooling=None), dict(CONFIG, file_count_threshold=None), dict(CONFIG, file_count_threshold=4.9), dict(CONFIG, executable_class={})):
            self.config.write_text(json.dumps(bad), encoding="utf-8")
            r = self.run_cli("%s..HEAD" % self.base)
            self.assertEqual(r.returncode, 2, json.dumps(bad))
            self.assertTrue(r.stdout.startswith("CANNOT-EVALUATE"), r.stdout)
        self.config.write_text(json.dumps(CONFIG), encoding="utf-8")

    def test_trace_is_one_line_even_with_odd_references(self):
        self.write("scripts/helper.py", "print('v2')\n")
        head = self.commit()
        r = self.run_cli("--red-recorded", "ledger\nline2", "%s..%s" % (self.base, head))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(len(r.stdout.strip().splitlines()), 1)
        self.assertIn("red-recorded:scripts/helper.py(ledger\\nline2)", r.stdout)

    def test_rendered_default_patterns_when_jinja2_available(self):
        try:
            import jinja2
        except ImportError:
            self.skipTest("jinja2 unavailable")
        src = next((c for c in (CLI.with_name("scope-classes.json.jinja"),) if c.is_file()), None)
        if src is None:
            self.skipTest("no jinja source beside the CLI (generated project)")
        env = jinja2.Environment(keep_trailing_newline=True)
        for stack, db, path, expect in (("nextjs", "supabase", "apps/web/src/app/page.tsx", "page-touched"), ("rails", "postgres", "db/migrate/1_x.rb", "migration-added"), ("django", "sqlite", "orders/migrations/0001_initial.py", "migration-added")):
            cfg = Path(self.tmp.name) / ("%s.json" % stack)
            cfg.write_text(env.from_string(src.read_text()).render(stack=stack, database=db, use_tds=False), encoding="utf-8")
            listing = Path(self.tmp.name) / "l.txt"
            listing.write_text("A\t%s\n" % path, encoding="utf-8")
            r = subprocess.run([sys.executable, str(CLI), "--config", str(cfg), "--paths-from", str(listing)], capture_output=True, text=True, cwd="/", env=ENV, timeout=60)
            self.assertIn(expect, r.stdout, (stack, path, r.stdout))

    def test_unreadable_config_bad_pattern_and_bad_range_cannot_evaluate(self):
        r = self.run_cli("%s..HEAD" % self.base)
        self.assertEqual(r.returncode, 0)
        self.config.write_text("{not json", encoding="utf-8")
        r = self.run_cli("%s..HEAD" % self.base)
        self.assertEqual((r.returncode, r.stdout.startswith("CANNOT-EVALUATE")), (2, True))
        bad = dict(CONFIG, standard_triggers=[{"name": "x", "pattern": "("}])
        self.config.write_text(json.dumps(bad), encoding="utf-8")
        r = self.run_cli("%s..HEAD" % self.base)
        self.assertEqual(r.returncode, 2)
        self.assertIn("bad pattern", r.stdout)
        self.config.write_text(json.dumps(CONFIG), encoding="utf-8")
        r = self.run_cli("nope..HEAD")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unresolved revision", r.stdout)

    def test_rendered_sibling_config_is_valid_when_present(self):
        rendered = CLI.with_name("scope-classes.json")
        if not rendered.is_file():
            self.skipTest("no rendered scope-classes.json beside the CLI (JV repo layout)")
        listing = Path(self.tmp.name) / "p.txt"
        listing.write_text("M\tREADME.md\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(CLI), "--config", str(rendered), "--paths-from", str(listing)],
                           capture_output=True, text=True, cwd="/", env=ENV, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "class=Quick reason=quick-by-heuristic")
        self.assertEqual(json.loads(rendered.read_text())["tooling"]["inventory"], [], "rendered config must ship inert")
        listing.write_text("M\tscripts/evidence-delta.py\nM\tscripts/test_evidence_delta.py\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(CLI), "--config", str(rendered), "--paths-from", str(listing)],
                           capture_output=True, text=True, cwd="/", env=ENV, timeout=60)   # a rendered project need not be a git repo
        self.assertTrue(r.stdout.startswith("class=Standard+ reason=executable-class,tooling-refused:"), "tooling must not fire with an empty inventory: " + r.stdout)


if __name__ == "__main__":
    unittest.main()
