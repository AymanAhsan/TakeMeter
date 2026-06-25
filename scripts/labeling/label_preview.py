import csv
from pathlib import Path
rows = list(csv.DictReader(open(Path(__file__).parents[2] / "data" / "dataset.csv", encoding='utf-8')))
unlabeled = [r for r in rows if not r.get('label')]
print(len(unlabeled), 'unlabeled rows\n')
for r in unlabeled[:30]:
    t = r['type']
    text = r['text'][:160]
    print(f"[{t}] {repr(text)}")
    print()
