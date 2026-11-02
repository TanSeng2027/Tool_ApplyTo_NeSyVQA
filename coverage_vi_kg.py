# -*- coding: utf-8 -*-
r"""
coverage_vi_kg.py - Đo ĐỘ PHỦ của cây tri thức tiếng Việt trên các lớp vật thể mà detector (SGG) nhận ra.

Vào : cskg_triples_vi_commonsense.tsv (có cột dau_en, quan_he_en, duoi_en), custom_data_info.json (150 lớp VG)
      (tuỳ chọn) --vocab file.txt : mỗi dòng 1 từ tiếng Anh khác (ví dụ nhãn của bộ dữ liệu tiếng Việt)
Ra  : coverage_lop.tsv  (mỗi lớp: số cạnh, số hàng xóm khác nhau, số loại quan hệ, quan hệ nào)
      in thống kê: bao nhiêu lớp có 0 / <5 / >=20 cạnh, danh sách lớp không có cạnh nào
Chạy: python coverage_vi_kg.py --kg cskg_triples_vi_commonsense.tsv --info sgg_out\custom_data_info.json
"""
import argparse, csv, json, statistics
from collections import defaultdict, Counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kg', default='cskg_triples_vi_commonsense.tsv')
    ap.add_argument('--info', help='custom_data_info.json (ind_to_classes)')
    ap.add_argument('--vocab', help='file từ vựng tiếng Anh bổ sung, mỗi dòng 1 từ')
    ap.add_argument('--out', default='coverage_lop.tsv')
    a = ap.parse_args()

    classes = []
    if a.info:
        classes += [c.lower() for c in json.load(open(a.info, encoding='utf-8'))['ind_to_classes'] if c != '__background__']
    if a.vocab:
        classes += [l.strip().lower() for l in open(a.vocab, encoding='utf-8') if l.strip()]
    classes = sorted(set(classes))
    if not classes:
        raise SystemExit('Cần --info và/hoặc --vocab.')
    cs = set(classes)
    edges = Counter(); nbrs = defaultdict(set); rels = defaultdict(Counter); vi = {}
    with open(a.kg, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            h, t = r['dau_en'], r['duoi_en']
            for me, other, me_vi in ((h, t, r['dau_vi']), (t, h, r['duoi_vi'])):
                if me in cs:
                    edges[me] += 1; nbrs[me].add(other); rels[me][r['quan_he_en']] += 1; vi[me] = me_vi
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('lop_en\tlop_vi\tso_canh\tso_hang_xom\tso_loai_quan_he\tquan_he\n')
        for c in sorted(classes, key=lambda c: -edges[c]):
            f.write('%s\t%s\t%d\t%d\t%d\t%s\n' % (c, vi.get(c, ''), edges[c], len(nbrs[c]), len(rels[c]), ','.join('%s:%d' % kv for kv in rels[c].most_common(6))))
    n = len(classes); deg = [edges[c] for c in classes]
    print('[do] %d lớp tiếng Anh cần phủ' % n)
    print('  có >= 1 cạnh : %d (%.1f%%)' % (sum(d >= 1 for d in deg), 100 * sum(d >= 1 for d in deg) / n))
    print('  có >= 5 cạnh : %d (%.1f%%)' % (sum(d >= 5 for d in deg), 100 * sum(d >= 5 for d in deg) / n))
    print('  có >= 20 cạnh: %d (%.1f%%)' % (sum(d >= 20 for d in deg), 100 * sum(d >= 20 for d in deg) / n))
    print('  số cạnh mỗi lớp: trung vị %d, nhỏ nhất %d, lớn nhất %d' % (statistics.median(deg), min(deg), max(deg)))
    zero = [c for c in classes if edges[c] == 0]
    print('  KHÔNG có cạnh nào (%d): %s' % (len(zero), ', '.join(zero[:40]) + (' ...' if len(zero) > 40 else '')))
    low = [c for c in classes if 0 < edges[c] < 5]
    print('  rất ít cạnh (1-4) (%d): %s' % (len(low), ', '.join(low[:40]) + (' ...' if len(low) > 40 else '')))
    print('[ghi]', a.out)


if __name__ == '__main__':
    main()
