#!/usr/bin/env python
# -*- encoding: UTF-8 -*-

"""
Tests accsum on UTF-8 files.
"""

import glob
import shutil
import subprocess
import tempfile

import os.path as p
from collections import namedtuple, OrderedDict

# Alias range as xrange in Python 3:
try:
    xrange
except NameError:
    xrange = range

# Create a Python 2/3 Unicode string literal:
try:
    unicode
except NameError:
    u = str
else:
    u = lambda s: s.decode('UTF-8')


# pathlib doesn't exist in Python 2, so make a small version of it:
class Path(str):
    def __div__(self, other):
        return Path(p.join(self, other))

    def exists(self):
        return p.exists(self)

    def create_file(self, filename, contents):
        with open(self / filename, 'w') as fp:
            fp.write(contents.encode('UTF-8'))
            if not contents.endswith('\n'):
                fp.write(b'\x0A')


# Path to accuracy program
BIN_DIR = Path(p.dirname(p.dirname(p.realpath(__file__)))) / 'bin'
ACCURACY_BIN = BIN_DIR / 'accuracy'
ACCSUM_BIN = BIN_DIR / 'accsum'
assert ACCURACY_BIN.exists(), 'Could not find ' + ACCURACY_BIN
assert ACCSUM_BIN.exists(), 'Could not find ' + ACCSUM_BIN


class FilePair(namedtuple('FilePairBase', 'actual generated')):
    """
    Pair of tests that are written as documents. Then an accuracy report may
    be produced.
    """

    @property
    def prefix(self):
        return str(hash(self.actual))

    def write_to_dir(self, directory):
        directory.create_file(self.actual_filename, self.actual)
        directory.create_file(self.generated_filename, self.generated)

    @property
    def actual_filename(self):
        return '%s_actual' % self.prefix

    @property
    def generated_filename(self):
        return '%s_gen' % self.prefix

    @property
    def report_filename(self):
        return '%s_report' % self.prefix

    def write_accuracy_report(self, directory):
        self.write_to_dir(directory)

        # Return name of the report?
        subprocess.check_call([
            ACCURACY_BIN,
            directory / self.actual_filename,
            directory / self.generated_filename,
            directory / self.report_filename
        ])


class ClassResult(namedtuple('ResultBase', 'count missed right character')):
    pass


class ClassReport(object):
    """
    Wraps an accuracy report.
    """
    def __init__(self, *results):
        self._results = OrderedDict((
            (result.character, result) for result in results
        ))

    def __getitem__(self, key):
        return self._results[key]

    @classmethod
    def from_accuracy_report(cls, report_text):
        lines = report_text.split('\n\n')[-1].rstrip('\n').split('\n')

        # Assert we've got the right header
        count, missed, right = lines.pop(0).split()
        assert count == u('Count')
        assert missed == u('Missed')
        assert right == u('%Right')

        def generate_results():
            for line in lines:
                count, missed, right, char = line.lstrip().split(None, 3)
                char = char.lstrip(u('{')).rstrip(u('}'))
                yield ClassResult(int(count), int(missed), right, char)

        return cls(*list(generate_results()))


class TemporaryDirectory(object):
    """
    Context manager: creates a temporary directory and removes it when
    finished.
    """
    def __enter__(self):
        self._name = Path(tempfile.mkdtemp())
        return self._name

    def __exit__(self, *exc_info):
        shutil.rmtree(self._name)


def accsum(reports):
    """
    Runs accsum, returning a ClassReport (the final section in the report).
    """
    # Save the accuracy report to the temporary file.
    with tempfile.TemporaryFile() as temp_file:
        subprocess.check_call([ACCSUM_BIN] + reports, stdout=temp_file)

        temp_file.flush()
        temp_file.seek(0)

        contents = temp_file.read().decode('UTF-8')

    return ClassReport.from_accuracy_report(contents)


tests = [
    FilePair(actual=u("Hello{{world>"),
             generated=u("Hello{<world>")),
    FilePair(actual=u("Hello<<world>"),
             generated=u("Hello<{world>")),
    # TODO: hospital/beauty salon test
    # TODO: polish test
]

actual = ClassReport.from_accuracy_report(u(
r"""UNLV-ISRI OCR Accuracy Report Version 6.1
-----------------------------------------
    1124   Characters
       8   Errors
   99.29%  Accuracy

       0   Reject Characters
       0   Suspect Markers
       0   False Marks
    0.00%  Characters Marked
   99.29%  Accuracy After Correction

     Ins    Subst      Del   Errors
       0        0        0        0   Marked
       0        6        2        8   Unmarked
       0        6        2        8   Total

   Count   Missed   %Right
     112        0   100.00   ASCII Spacing Characters
      62        0   100.00   ASCII Special Symbols
      42        0   100.00   ASCII Uppercase Letters
     908        6    99.34   ASCII Lowercase Letters
    1124        6    99.47   Total

  Errors   Marked   Correct-Generated
       4        0   {ä}-{a}
       2        0   {}-{<\n>}
       2        0   {ö}-{o}

   Count   Missed   %Right
     112        0   100.00   { }
      20        0   100.00   {"}
       8        0   100.00   {(}
       8        0   100.00   {)}
      16        0   100.00   {,}
       2        0   100.00   {-}
       8        0   100.00   {.}
       8        0   100.00   {C}
       4        0   100.00   {I}
       4        0   100.00   {M}
      10        0   100.00   {O}
      12        0   100.00   {R}
       4        0   100.00   {T}
     104        0   100.00   {a}
      16        0   100.00   {c}
       4        0   100.00   {d}
      82        0   100.00   {e}
      12        0   100.00   {g}
      10        0   100.00   {h}
     116        0   100.00   {i}
      12        0   100.00   {j}
      42        0   100.00   {k}
      54        0   100.00   {l}
      20        0   100.00   {m}
      66        0   100.00   {n}
      48        0   100.00   {o}
      14        0   100.00   {p}
      30        0   100.00   {r}
      94        0   100.00   {s}
      98        0   100.00   {t}
      36        0   100.00   {u}
      14        0   100.00   {v}
       6        0   100.00   {w}
      30        6    80.00   {y}
"""))


if __name__ == '__main__':

    # Create temporary files for each...
    with TemporaryDirectory() as temp_dir:
        # Create each individual accuracy report:
        for test in tests:
            test.write_accuracy_report(temp_dir)

        reports = glob.glob(temp_dir / '*_report')
        assert len(reports) == len(tests)

        final_report = accsum(reports)
        import os; os.system('open ' + temp_dir)
        import pdb; pdb.set_trace()

        raise NotImplementedError

