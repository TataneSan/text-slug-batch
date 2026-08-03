import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_slug_batch.cli import main, slugify  # noqa: E402


def _write(dirpath, name, content):
    path = os.path.join(dirpath, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _run(argv, stdin_text=""):
    out = io.StringIO()
    err = io.StringIO()
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin_text)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
    finally:
        sys.stdin = old_stdin
    return code, out.getvalue(), err.getvalue()


class SlugifyUnitTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_accents(self):
        self.assertEqual(slugify("Crème brûlée à Paris"), "creme-brulee-a-paris")

    def test_punctuation(self):
        self.assertEqual(slugify("Hello, World! Foo? Bar."), "hello-world-foo-bar")

    def test_separator_custom(self):
        self.assertEqual(slugify("Hello World", separator="_"), "hello_world")

    def test_keep_case(self):
        self.assertEqual(slugify("Hello World", keep_case=True), "Hello-World")

    def test_max_length(self):
        self.assertEqual(slugify("this is a very long title", max_length=10), "this-is-a")

    def test_max_length_no_trailing_sep(self):
        result = slugify("hello-world-foo", max_length=7)
        self.assertFalse(result.endswith("-"))
        self.assertLessEqual(len(result), 7)

    def test_collapse_separators(self):
        self.assertEqual(slugify("foo   ---   bar"), "foo-bar")

    def test_empty_input(self):
        self.assertEqual(slugify(""), "")
        self.assertEqual(slugify("!!!"), "")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_stdin_basic(self):
        code, out, _ = _run(["-"], stdin_text="Hello World\nFoo Bar\n")
        self.assertEqual(code, 0)
        self.assertEqual(out, "hello-world\nfoo-bar\n")

    def test_file_input(self):
        path = _write(self.dir, "titles.txt", "My Post Title\nAnother One\n")
        code, out, _ = _run([path])
        self.assertEqual(code, 0)
        self.assertEqual(out, "my-post-title\nanother-one\n")

    def test_pairs_mode(self):
        code, out, _ = _run(["-", "--pairs"], stdin_text="Hello World\n")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "Hello World => hello-world")

    def test_dedup_suffix(self):
        code, out, _ = _run(["-"], stdin_text="Hello\nHello\nHello\n")
        lines = out.strip().split("\n")
        self.assertEqual(lines[0], "hello")
        self.assertEqual(lines[1], "hello-2")
        self.assertEqual(lines[2], "hello-3")

    def test_no_dedup(self):
        code, out, _ = _run(["-", "--no-dedup"], stdin_text="Hello\nHello\n")
        lines = out.strip().split("\n")
        self.assertEqual(lines, ["hello", "hello"])

    def test_skip_empty(self):
        code, out, _ = _run(["-", "--skip-empty"], stdin_text="!!!\nHello\n")
        self.assertEqual(out, "hello\n")

    def test_separator_underscore(self):
        code, out, _ = _run(["-", "-s", "_"], stdin_text="Hello World\n")
        self.assertEqual(out, "hello_world\n")

    def test_json_report(self):
        import json as _json
        code, out, _ = _run(["-", "--json"], stdin_text="Hello World\nfixed-slug\n")
        self.assertEqual(code, 0)
        report = _json.loads(out)
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["changed"], 1)
        slugs = [m["slug"] for m in report["mappings"]]
        self.assertIn("hello-world", slugs)
        self.assertIn("fixed-slug", slugs)

    def test_json_duplicate_count(self):
        import json as _json
        code, out, _ = _run(["-", "--json"], stdin_text="Hello\nHello\n")
        report = _json.loads(out)
        self.assertEqual(report["duplicates"], 1)

    def test_check_gate_pass(self):
        code, _, _ = _run(["-", "--check"], stdin_text="hello-world\nfoo\n")
        self.assertEqual(code, 0)

    def test_check_gate_fail(self):
        code, _, _ = _run(["-", "--check"], stdin_text="Hello World\n")
        self.assertEqual(code, 2)

    def test_require_change_pass(self):
        code, _, _ = _run(["-", "--require-change"], stdin_text="Hello World\n")
        self.assertEqual(code, 0)

    def test_require_change_fail(self):
        code, _, _ = _run(["-", "--require-change"], stdin_text="hello\n")
        self.assertEqual(code, 2)

    def test_require_unchanged_pass(self):
        code, _, _ = _run(["-", "--require-unchanged"], stdin_text="hello-world\n")
        self.assertEqual(code, 0)

    def test_require_unchanged_fail(self):
        code, _, _ = _run(["-", "--require-unchanged"], stdin_text="Hello World\n")
        self.assertEqual(code, 2)

    def test_require_unique_pass(self):
        code, _, _ = _run(["-", "--require-unique"], stdin_text="hello\nworld\n")
        self.assertEqual(code, 0)

    def test_require_unique_fail(self):
        code, _, _ = _run(["-", "--require-unique"], stdin_text="Hello\nHello\n")
        self.assertEqual(code, 2)

    def test_missing_file_exits_1(self):
        code, _, err = _run(["/nonexistent/file.txt"])
        self.assertEqual(code, 1)
        self.assertIn("error reading input", err)

    def test_max_length_gate(self):
        code, out, _ = _run(["-", "--max-length", "5"], stdin_text="Hello World\n")
        self.assertEqual(code, 0)
        self.assertLessEqual(len(out.strip()), 5)


if __name__ == "__main__":
    unittest.main()
