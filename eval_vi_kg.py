# -*- coding: utf-8 -*-
r"""
eval_vi_kg.py - Đánh giá chất lượng cây tri thức tiếng Việt bằng người (độ chính xác theo quan hệ + độ đồng thuận kappa).

B1. Lấy mẫu cạnh để chấm (phân tầng theo quan hệ, cố định seed để tái lập):
    python eval_vi_kg.py sample --kg vi_kg.tsv --per-rel 40 --out danh_gia_mau.tsv
    -> mỗi người chấm điền cột danh_gia_A / danh_gia_B bằng:  d (đúng) | s (sai) | k (không chắc)
       Tiêu chí gợi ý: câu "<đầu> <quan hệ> <đuôi>" có đúng theo hiểu biết thông thường VÀ tự nhiên trong tiếng Việt không?
B2. Tính kết quả:
    python eval_vi_kg.py score --file danh_gia_mau.tsv
    -> độ chính xác theo quan hệ (A, B, và khi cả hai cùng 'd'), tỉ lệ đồng thuận, Cohen's kappa
"""
import argparse, csv, random, sys
from collections import defaultdict, Counter


def sample(a):
    rows = list(csv.DictReader(open(a.kg, encoding='utf-8'), delimiter='\t'))
    by = defaultdict(list)
    only = set(x.strip() for x in a.only.split(',')) if a.only else None
    for r in rows:
        if only is None or r['quan_he_en'] in only:
            by[r['quan_he_en']].append(r)
    if not by:
        sys.exit('Không có cạnh nào khớp --only. Quan hệ có trong file: ' + ', '.join(sorted({r['quan_he_en'] for r in rows})))
    rnd = random.Random(a.seed); out = []
    for rel, rs in sorted(by.items()):
        rnd.shuffle(rs); out += rs[:a.per_rel]
    rnd.shuffle(out)
    cols = ['id', 'cau_vi', 'dau_vi', 'quan_he_vi', 'duoi_vi', 'dau_en', 'quan_he_en', 'duoi_en', 'danh_gia_A', 'danh_gia_B']
    with open(a.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t'); w.writerow(cols)
        for i, r in enumerate(out, 1):
            w.writerow([i, '%s %s %s' % (r['dau_vi'], r['quan_he_vi'], r['duoi_vi']), r['dau_vi'], r['quan_he_vi'], r['duoi_vi'],
                        r['dau_en'], r['quan_he_en'], r['duoi_en'], '', ''])
    print('[mẫu] %d cạnh (%s) -> %s' % (len(out), ', '.join('%s:%d' % (k, min(len(v), a.per_rel)) for k, v in sorted(by.items())), a.out))


def kappa(x, y):
    n = len(x)
    if n == 0:
        return float('nan')
    po = sum(1 for i, j in zip(x, y) if i == j) / n
    cx, cy = Counter(x), Counter(y)
    pe = sum((cx[k] / n) * (cy[k] / n) for k in set(cx) | set(cy))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def score(a):
    rows = list(csv.DictReader(open(a.file, encoding='utf-8'), delimiter='\t'))
    ok = {'d', 's', 'k'}
    rated = [r for r in rows if r['danh_gia_A'].strip().lower() in ok and r['danh_gia_B'].strip().lower() in ok]
    print('[chấm] %d/%d cạnh đã có đủ 2 nhãn hợp lệ (d/s/k)' % (len(rated), len(rows)))
    if not rated:
        sys.exit('Chưa có cạnh nào được chấm đủ.')
    A = [r['danh_gia_A'].strip().lower() for r in rated]; B = [r['danh_gia_B'].strip().lower() for r in rated]
    print('[đồng thuận] %.1f%% | Cohen kappa = %.3f' % (100 * sum(1 for i, j in zip(A, B) if i == j) / len(A), kappa(A, B)))
    by = defaultdict(list)
    for r, x, y in zip(rated, A, B):
        by[r['quan_he_en']].append((x, y))
    print('\n%-14s %5s  %8s %8s %10s' % ('quan hệ', 'n', 'đúng(A)', 'đúng(B)', 'cả hai đúng'))
    tot = [0, 0, 0, 0]
    for rel, v in sorted(by.items()):
        n = len(v); pa = sum(x == 'd' for x, _ in v); pb = sum(y == 'd' for _, y in v); pab = sum(x == 'd' and y == 'd' for x, y in v)
        print('%-14s %5d  %7.1f%% %7.1f%% %9.1f%%' % (rel, n, 100 * pa / n, 100 * pb / n, 100 * pab / n))
        for i, c in enumerate((n, pa, pb, pab)):
            tot[i] += c
    print('%-14s %5d  %7.1f%% %7.1f%% %9.1f%%' % ('TỔNG', tot[0], 100 * tot[1] / tot[0], 100 * tot[2] / tot[0], 100 * tot[3] / tot[0]))


def errors(a):
    rows = list(csv.DictReader(open(a.file, encoding='utf-8'), delimiter='\t'))
    bad = Counter(); tot = Counter(); ex = defaultdict(list)
    for r in rows:
        x, y = r['danh_gia_A'].strip().lower(), r['danh_gia_B'].strip().lower()
        if x not in ('d', 's', 'k') and y not in ('d', 's', 'k'):
            continue
        is_bad = (x == 's') + (y == 's') >= 1
        for side in ('dau', 'duoi'):
            key = (r[side + '_en'], r[side + '_vi'])
            tot[key] += 1
            if is_bad:
                bad[key] += 1
                if len(ex[key]) < 2:
                    ex[key].append(r['cau_vi'])
    print('Từ xuất hiện nhiều nhất trong cạnh bị chấm SAI (ưu tiên sửa bản dịch các từ này):\n')
    print('%-16s %-22s %6s %6s  ví dụ' % ('từ Anh', 'bản dịch hiện tại', 'sai', 'tổng'))
    for (en, vi), c in bad.most_common(a.top):
        print('%-16s %-22s %6d %6d  %s' % (en, vi, c, tot[(en, vi)], ' | '.join(ex[(en, vi)])))
    print('\nSửa các từ này trong 1 file JSON, ví dụ sua_dich.json: {"figure": "hình nhân", ...} rồi chạy build_vi_kg.py với --override sua_dich.json')


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('sample'); s.add_argument('--kg', default='vi_kg.tsv'); s.add_argument('--per-rel', type=int, default=40)
    s.add_argument('--seed', type=int, default=42); s.add_argument('--only', help='chỉ lấy mẫu các quan hệ này, ví dụ IsA,PartOf,HasA,UsedFor'); s.add_argument('--out', default='danh_gia_mau.tsv')
    c = sp.add_parser('score'); c.add_argument('--file', default='danh_gia_mau.tsv')
    q = sp.add_parser('errors'); q.add_argument('--file', default='danh_gia_mau.tsv'); q.add_argument('--top', type=int, default=30)
    a = ap.parse_args()
    {'sample': sample, 'score': score, 'errors': errors}[a.cmd](a)


if __name__ == '__main__':
    main()