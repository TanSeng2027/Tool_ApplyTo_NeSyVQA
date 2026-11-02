# -*- coding: utf-8 -*-
r"""
gt_peek.py - Xem nhanh chất lượng translated_nodes.tsv: thống kê + mẫu ngẫu nhiên theo vùng bậc và theo trạng thái.
Chạy: python gt_peek.py --file translated_nodes.tsv --n 25
"""
import argparse, csv, random, re
from collections import Counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', default='translated_nodes.tsv')
    ap.add_argument('--n', type=int, default=25)
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    rows = list(csv.reader(open(a.file, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]
    rows = [r for r in rows if len(r) >= 5]
    N = len(rows); rnd = random.Random(a.seed)
    same = sum(1 for r in rows if r[1].lower() == r[0].lower())
    empty = sum(1 for r in rows if not r[1])
    digit = sum(1 for r in rows if re.search(r'\d', r[1]))
    longer = sum(1 for r in rows if len(r[1].split()) > 3)
    print('Tổng %d từ | rỗng %d | giữ nguyên tiếng Anh %d (%.1f%%) | có chữ số %d | bản dịch > 3 từ %d' % (N, empty, same, 100 * same / N, digit, longer))
    print('Trạng thái:', dict(Counter(r[3] for r in rows)))
    bands = [('TOP 2.000 (bậc cao nhất, ảnh hưởng nhiều cạnh nhất)', 0, 2000), ('GIỮA (hạng 100.000 - 110.000)', 100000, 110000), ('ĐUÔI (hạng 900.000 trở đi)', 900000, N)]
    for name, lo, hi in bands:
        seg = rows[lo:hi]
        if not seg:
            continue
        print('\n== %s ==' % name)
        for r in rnd.sample(seg, min(a.n, len(seg))):
            print('  %-24s -> %-28s [%s] bậc=%s' % (r[0], r[1], r[3], r[4]))
    print('\n== Mẫu từ bị đánh kiem_tra ==')
    kt = [r for r in rows if r[3] == 'kiem_tra']
    for r in rnd.sample(kt, min(a.n, len(kt))):
        print('  %-24s -> %-28s bậc=%s' % (r[0], r[1], r[4]))


if __name__ == '__main__':
    main()
