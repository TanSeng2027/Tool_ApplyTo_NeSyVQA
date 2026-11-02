# -*- coding: utf-8 -*-
r"""
gt_merge.py - Ghép các file .xlsx đã dịch bằng Google Translate về translated_nodes.tsv (cùng định dạng với translate_nodes.py).
Ghép theo cột A (id), nên tên file và thứ tự file không quan trọng; kiểm tra lệch hàng.
Chạy: python gt_merge.py --nodes nodes.tsv --vi-dir gt_dich --out translated_nodes.tsv [--back-dir gt_dich_nguoc]
  --back-dir: thư mục chứa bản dịch NGƯỢC (đưa các file tiếng Việt lên dịch Vietnamese -> English) để gán khop/kiem_tra
"""
import argparse, glob, os, sys
from openpyxl import load_workbook
import translate_candidates as T


def read_dir(d):
    out = {}; bad = 0
    for p in sorted(glob.glob(os.path.join(d, '*.xlsx'))):
        ws = load_workbook(p, read_only=True).active
        for row in ws.iter_rows(values_only=True):
            if not row or row[0] is None:
                continue
            try:
                i = int(row[0])
            except (TypeError, ValueError):
                bad += 1; continue
            out[i] = (str(row[1]).strip() if len(row) > 1 and row[1] is not None else '')
    return out, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nodes', default='nodes.tsv')
    ap.add_argument('--vi-dir', default='gt_dich')
    ap.add_argument('--back-dir')
    ap.add_argument('--out', default='translated_nodes.tsv')
    a = ap.parse_args()

    words = []; deg = []
    with open(a.nodes, encoding='utf-8') as f:
        next(f)
        for l in f:
            p = l.rstrip('\r\n').split('\t')
            if p[0]:
                words.append(p[0]); deg.append(p[1] if len(p) > 1 else '0')
    vi, bad1 = read_dir(a.vi_dir)
    back, bad2 = (read_dir(a.back_dir) if a.back_dir else ({}, 0))
    if bad1 or bad2:
        print('[cảnh báo] %d dòng có cột A không phải số (bị Google đổi?)' % (bad1 + bad2))
    miss = sum(1 for i in range(1, len(words) + 1) if i in vi and not vi[i])
    n = st = 0; stat = {}
    with open(a.out, 'w', encoding='utf-8') as o:
        o.write('tu_anh\tban_dich_vi\tdich_nguoc_en\ttrang_thai\tbac\n')
        for i, w in enumerate(words, 1):
            if i not in vi:
                continue
            v = T.clean_vi(vi[i]); b = back.get(i, '')
            if not v or v.lower() == w.lower():
                s = 'kiem_tra'                     # rỗng hoặc Google để nguyên tiếng Anh (tên riêng/viết tắt?)
            elif a.back_dir:
                s = 'khop' if i in back and (T.norm(b) == T.norm(w) or T.norm(b).rstrip('s') == T.norm(w).rstrip('s')) else 'kiem_tra'
            else:
                s = 'chua_kiem'
            stat[s] = stat.get(s, 0) + 1; n += 1
            o.write('%s\t%s\t%s\t%s\t%s\n' % (w, v.replace('\t', ' '), b.replace('\t', ' '), s, deg[i - 1]))
    print('[ghép] %d/%d từ có bản dịch | trạng thái: %s' % (n, len(words), stat))
    if n < len(words):
        print('[cảnh báo] thiếu %d từ (chưa dịch file nào đó?)' % (len(words) - n))
    print('[ghi]', a.out)


if __name__ == '__main__':
    main()
