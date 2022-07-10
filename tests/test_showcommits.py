import io
import os
import sys

from foliant_test.preprocessor import PreprocessorTestFramework
from foliant_test.preprocessor import unpack_file_dict
from unittest import TestCase


def rel_name(path: str):
    return os.path.join(os.path.dirname(__file__), path)


def count_output_warnings(source) -> int:
    return source.getvalue().lower().count('warning')


class TestShowCommits(TestCase):
    def setUp(self):
        self.ptf = PreprocessorTestFramework('showcommits')
        self.ptf.quiet = False
        self.capturedOutput = io.StringIO()
        sys.stdout = self.capturedOutput

    def test_simple(self):
        self.ptf.options = {
            'targets': ['pre']
        }
        self.ptf.context['target'] = 'pre'
        self.ptf.test_preprocessor(
            input_mapping=unpack_file_dict(
                {'test.md': rel_name('test_repo/test.md')}
            ),
            expected_mapping=unpack_file_dict(
                {'test.md': rel_name('expected/test.md')}
            ),
        )

        self.assertEqual(1, count_output_warnings(self.capturedOutput))
