# -*- coding: utf-8 -*-
r"""
gt_split.py - Cắt nodes.tsv thành nhiều file .xlsx để dịch bằng Google Translate (Dịch tài liệu).
Mỗi file: cột A = số thứ tự (số, không bị dịch), cột B = từ tiếng Anh. KHÔNG có dòng tiêu đề.
Cần: pip install openpyxl
Chạy: python gt_split.py --nodes nodes.tsv --outdir gt_chunks --rows 50000
Rồi: lên translate.google.com -> tab 'Tài liệu' -> chọn English -> Vietnamese -> tải từng file lên -> tải bản dịch về thư mục gt_dich
"""
import argparse, os, csv
from openpyxl import Workbook


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nodes', default='nodes.tsv')
    ap.add_argument('--outdir', default='gt_chunks')
    ap.add_argument('--rows', type=int, default=50000, help='số từ mỗi file (nhỏ hơn thì file nhẹ, dễ thử)')
    ap.add_argument('--limit', type=int, default=0, help='chỉ cắt N từ đầu (0 = hết), dùng để thử')
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    words = []
    with open(a.nodes, encoding='utf-8') as f:
        next(f)
        for l in f:
            w = l.rstrip('\r\n').split('\t')[0]
            if w:
                words.append(w)
    if a.limit:
        words = words[:a.limit]
    n = 0
    for i in range(0, len(words), a.rows):
        wb = Workbook(); ws = wb.active
        for j, w in enumerate(words[i:i + a.rows]):
            ws.append([i + j + 1, w])          # id toàn cục (1..N)
        n += 1
        p = os.path.join(a.outdir, 'chunk_%04d.xlsx' % n)
        wb.save(p)
        print('[ghi]', p, '(%d từ, %.1f KB)' % (min(a.rows, len(words) - i), os.path.getsize(p) / 1024))
    print('[xong] %d từ -> %d file trong %s' % (len(words), n, a.outdir))


if __name__ == '__main__':
    main()
