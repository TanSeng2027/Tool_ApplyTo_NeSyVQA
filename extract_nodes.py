# -*- coding: utf-8 -*-
r"""
BƯỚC 1 - extract_nodes.py: trích TẤT CẢ nút (khái niệm) tiếng Anh từ cskg_triples_uri.tsv, lưu vào file.
Ra: nodes.tsv  (tu_anh <TAB> bac)   - sắp theo bậc (số cạnh) giảm dần, để nếu dịch dở dang thì phần quan trọng đã xong trước
Chạy: python extract_nodes.py --triples cskg_triples_uri.tsv --out nodes.tsv
"""
import argparse, time
from collections import Counter


def label(uri, lang='en'):
    q = uri.split('/')
    if len(q) >= 4 and q[1] == 'c' and q[2] == lang:
        return q[3].replace('_', ' ').strip().lower()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--triples', required=True)
    ap.add_argument('--out', default='nodes.tsv')
    ap.add_argument('--lang', default='en')
    a = ap.parse_args()
    deg = Counter(); n = 0; t = time.time()
    with open(a.triples, encoding='utf-8', errors='replace') as f:
        for line in f:
            n += 1
            p = line.rstrip('\r\n').split('\t')
            if len(p) < 3:
                continue
            for u in (p[0], p[2]):
                w = label(u, a.lang)
                if w:
                    deg[w] += 1
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('tu_anh\tbac\n')
        for w, d in deg.most_common():
            f.write('%s\t%d\n' % (w, d))
    print('[xong] %d dòng, %d nút khác nhau (%.1fs) -> %s' % (n, len(deg), time.time() - t, a.out))


if __name__ == '__main__':
    main()
