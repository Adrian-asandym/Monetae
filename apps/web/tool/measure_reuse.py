"""Count literal retained lines; pass ONLY the authorized Cashew/budget path.

This proxy does not claim to detect authorship: matching Flutter boilerplate
also counts. It separates complete retained lines from rewritten/new lines,
excluding blanks, provenance comments, imports and short delimiters from reuse.
"""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path)
args = parser.parse_args()
target = Path(__file__).resolve().parents[1] / 'lib'
transaction_files = [
    'transactionEntry', 'transactionEntryAmount', 'incomeAmountArrow',
    'transactionEntryNote', 'transactionEntryTag', 'transactionLabel',
]
pairs = {
    'theme/monetae_theme.dart': ['colors.dart'],
    'widgets/transaction_card.dart': [
        'widgets/transactionEntry/' + name + '.dart' for name in transaction_files
    ],
    'widgets/category_pie_chart.dart': ['widgets/pieChart.dart'],
    'widgets/custom_delayed_curve.dart': ['struct/customDelayedCurve.dart'],
    'widgets/fade_in.dart': ['widgets/fadeIn.dart'],
}
print('file,total,literal_retained,rewritten_or_new')
for new, old_files in pairs.items():
    originals = {
        line.strip()
        for old in old_files
        for line in (args.source / 'lib' / old).read_text().splitlines()
    }
    lines = (target / new).read_text().splitlines()
    retained = sum(
        len(line.strip()) >= 12
        and line.strip() in originals
        and not line.strip().startswith(('import ', '//', '@'))
        for line in lines
    )
    code_lines = sum(bool(line.strip()) and not line.strip().startswith('//') for line in lines)
    print(f'{new},{len(lines)},{retained},{code_lines - retained}')
