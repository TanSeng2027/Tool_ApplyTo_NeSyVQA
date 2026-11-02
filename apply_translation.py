# -*- coding: utf-8 -*-
r"""
BƯỚC 3 - apply_translation.py: ghép bản dịch nút vào file triplet gốc -> cskg_triples_vi.tsv (cột giống vi_kg.tsv, dùng được cho eval_vi_kg.py).
Chạy: python apply_translation.py --triples cskg_triples_uri.tsv --nodes translated_nodes.tsv --out cskg_triples_vi.tsv [--only-khop] [--rels-file rels_mapping_vi.json]
"""
import argparse, json, time
from collections import Counter
from build_vi_kg import DEFAULT_REL_VI, load_map, node_label


EXTRA_REL_VI = {
    'FormOf': 'là dạng của', 'HasContext': 'thuộc lĩnh vực', 'EtymologicallyRelatedTo': 'có chung nguồn gốc với',
    'EtymologicallyDerivedFrom': 'có nguồn gốc từ', 'DistinctFrom': 'khác với', 'MannerOf': 'là một cách của',
    'Entails': 'kéo theo', 'InstanceOf': 'là một ví dụ của', 'DefinedAs': 'được định nghĩa là', 'SymbolOf': 'là biểu tượng của',
    'HasFirstSubevent': 'bắt đầu bằng', 'HasLastSubevent': 'kết thúc bằng', 'CausesDesire': 'gây ra mong muốn',
    'NotDesires': 'không muốn', 'NotCapableOf': 'không thể', 'NotHasProperty': 'không có tính chất', 'NotUsedFor': 'không dùng để',
    'ObstructedBy': 'bị cản bởi', 'CreatedBy': 'được tạo bởi', 'Desires': 'muốn',
}
COMMONSENSE = ['IsA', 'PartOf', 'HasA', 'UsedFor', 'AtLocation', 'CapableOf', 'MadeOf', 'HasProperty', 'LocatedNear', 'Causes',
               'CausesDesire', 'Desires', 'HasSubevent', 'HasPrerequisite', 'HasFirstSubevent', 'HasLastSubevent',
               'MotivatedByGoal', 'ReceivesAction', 'CreatedBy', 'DefinedAs', 'SymbolOf', 'InstanceOf']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--triples', required=True)
    ap.add_argument('--nodes', default='translated_nodes.tsv')
    ap.add_argument('--out', default='cskg_triples_vi.tsv')
    ap.add_argument('--only-khop', action='store_true', help='chỉ dùng bản dịch dịch-ngược-khớp')
    ap.add_argument('--drop-kiem-tra', action='store_true', help='bỏ các từ trạng thái kiem_tra (Google giữ nguyên tiếng Anh hoặc rỗng)')
    ap.add_argument('--keep-rels', default='all', help='"all" | "commonsense" (bỏ RelatedTo/Synonym/FormOf/DerivedFrom/Antonym/HasContext...) | danh sách cách nhau dấu phẩy')
    ap.add_argument('--overrides', help='file JSON sửa tay (en -> vi), ưu tiên cao nhất')
    ap.add_argument('--rels-file', help='rels_mapping_vi.json')
    a = ap.parse_args()

    tr = {}
    with open(a.nodes, encoding='utf-8') as f:
        next(f)
        for l in f:
            p = l.rstrip('\r\n').split('\t')
            if len(p) >= 4 and p[1] and (not a.only_khop or p[3] == 'khop') and not (a.drop_kiem_tra and p[3] == 'kiem_tra'):
                tr[p[0]] = p[1]
    if a.overrides:
        tr.update({k.lower(): v for k, v in load_map(a.overrides).items()})
    rmap = dict(DEFAULT_REL_VI); rmap.update(EXTRA_REL_VI)
    if a.rels_file:
        rmap.update({k.replace('/r/', ''): v for k, v in load_map(a.rels_file).items()})
    k = a.keep_rels.strip()
    keep = None if k.lower() == 'all' else set(COMMONSENSE) if k.lower() == 'commonsense' else set(x.strip() for x in k.split(','))
    print('[nap] %d bản dịch nút | quan hệ giữ: %s' % (len(tr), 'tất cả' if keep is None else ', '.join(sorted(keep))))

    seen = set(); n = kept = dup = loops = 0; byrel = Counter(); t = time.time()
    with open(a.triples, encoding='utf-8', errors='replace') as f, open(a.out, 'w', encoding='utf-8') as o:
        o.write('dau_vi\tquan_he_vi\tduoi_vi\tdau_en\tquan_he_en\tduoi_en\n')
        for line in f:
            n += 1
            p = line.rstrip('\r\n').split('\t')
            if len(p) < 3 or not p[1].startswith('/r/'):
                continue
            h, tl = node_label(p[0]), node_label(p[2])
            if not h or not tl or h == tl or h not in tr or tl not in tr:
                continue
            r = p[1][3:]
            if keep is not None and r not in keep:
                continue
            if tr[h] == tr[tl]:
                loops += 1; continue                  # hai từ Anh khác nhau cùng ra một từ Việt -> cạnh tự nối, bỏ
            row = (tr[h], rmap.get(r, r), tr[tl])
            k = hash(row)
            if k in seen:
                dup += 1; continue
            seen.add(k); kept += 1; byrel[r] += 1
            o.write('%s\t%s\t%s\t%s\t%s\t%s\n' % (row[0], row[1], row[2], h, r, tl))
    print('[xong] %d dòng -> giữ %d cạnh tiếng Việt (bỏ %d trùng, %d cạnh tự nối) trong %.0fs' % (n, kept, dup, loops, time.time() - t))
    print('[theo quan hệ]', dict(byrel.most_common(12)))
    print('[ghi]', a.out)


if __name__ == '__main__':
    main()