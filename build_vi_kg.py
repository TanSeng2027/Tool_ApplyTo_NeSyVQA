# -*- coding: utf-8 -*-
r"""
build_vi_kg.py - Dịch CSKG sang đồ thị tri thức tiếng Việt.

Đọc : cskg_triples_uri.tsv (node1 <TAB> /r/Rel <TAB> node2), class_mapping_vi.json, rels_mapping_vi.json
Giữ : cạnh mà CẢ HAI nút đều có bản dịch trong class_mapping_vi.json, quan hệ thuộc danh sách cho phép.
Ra  : vi_kg.tsv   (đầu, quan hệ, đuôi - tiếng Việt, kèm cột tiếng Anh)
      vi_kg.json  (nodes, edges, thống kê)
Chạy: python build_vi_kg.py --triples cskg_triples_uri.tsv --classes class_mapping_vi.json --rels rels_mapping_vi.json
"""
import argparse, json, os, sys, time
from collections import Counter, defaultdict

# Tên quan hệ CSKG -> tiếng Việt (bị ghi đè nếu rels_mapping_vi.json có cùng khóa)
DEFAULT_REL_VI = {
    'IsA': 'là một loại', 'PartOf': 'là một phần của', 'HasA': 'có', 'UsedFor': 'dùng để',
    'AtLocation': 'thường ở', 'CapableOf': 'có thể', 'MadeOf': 'làm từ', 'HasProperty': 'có tính chất',
    'LocatedNear': 'ở gần', 'Causes': 'gây ra', 'Desires': 'muốn', 'ReceivesAction': 'có thể bị',
    'HasSubevent': 'gồm bước', 'HasPrerequisite': 'cần có', 'MotivatedByGoal': 'vì mục tiêu',
    'RelatedTo': 'liên quan đến', 'Synonym': 'đồng nghĩa với', 'Antonym': 'trái nghĩa với',
    'SimilarTo': 'giống', 'DerivedFrom': 'bắt nguồn từ', 'CreatedBy': 'được tạo bởi',
}
DEFAULT_KEEP = ['IsA', 'PartOf', 'HasA', 'UsedFor', 'AtLocation', 'CapableOf', 'MadeOf', 'HasProperty']


def load_map(path):
    """Chấp nhận: {"man": "người đàn ông"}, {"man": ["người đàn ông", ...]}, {"man": {"vi": "..."}}, hoặc list các cặp."""
    raw = json.load(open(path, encoding='utf-8'))
    out = {}

    def pick(v):
        if isinstance(v, str):
            return v.strip()
        if isinstance(v, (list, tuple)) and v:
            return pick(v[0])
        if isinstance(v, dict):
            for k in ('vi', 'vn', 'vietnamese', 'tieng_viet', 'label_vi', 'name_vi', 'translation'):
                if k in v:
                    return pick(v[k])
            for x in v.values():
                if isinstance(x, (str, list)):
                    return pick(x)
        return None

    if isinstance(raw, dict):
        for k, v in raw.items():
            t = pick(v)
            if t:
                out[str(k).strip()] = t
    elif isinstance(raw, list):
        for it in raw:
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                out[str(it[0]).strip()] = str(it[1]).strip()
            elif isinstance(it, dict):
                ks = list(it.keys())
                en = it.get('en') or it.get('name') or it.get(ks[0])
                t = pick(it.get('vi') or it.get(ks[-1]))
                if en and t:
                    out[str(en).strip()] = t
    return out


def node_label(uri):
    """'/c/en/hot_dog/n/wn' -> 'hot dog' (chỉ nút tiếng Anh); khác -> None"""
    p = uri.split('/')
    if len(p) >= 4 and p[1] == 'c' and p[2] == 'en':
        return p[3].replace('_', ' ').strip().lower()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--triples', required=True)
    ap.add_argument('--classes', required=True, help='class_mapping_vi.json (tiếng Anh -> tiếng Việt)')
    ap.add_argument('--rels', help='rels_mapping_vi.json (tuỳ chọn, ghi đè tên quan hệ)')
    ap.add_argument('--keep', default=','.join(DEFAULT_KEEP), help='quan hệ CSKG giữ lại; "all" = tất cả')
    ap.add_argument('--out', default='vi_kg')
    ap.add_argument('--max-per-node-rel', type=int, default=0,
                    help='mỗi (nút, quan hệ) giữ tối đa K cạnh, ưu tiên nút đích cụ thể (ít kết nối); 0 = không giới hạn')
    ap.add_argument('--export-candidates', type=int, default=0,
                    help='xuất N khái niệm tiếng Anh chưa có bản dịch nhưng nối nhiều với từ đã dịch (để dịch thêm)')
    a = ap.parse_args()

    cmap = {k.lower(): v for k, v in load_map(a.classes).items()}
    rmap = dict(DEFAULT_REL_VI)
    if a.rels:
        for k, v in load_map(a.rels).items():
            rmap[k.replace('/r/', '').strip()] = v
    keep = None if a.keep.strip().lower() == 'all' else set(x.strip() for x in a.keep.split(','))

    print('[map] %d nút có bản dịch. Mẫu:' % len(cmap))
    for k in list(cmap)[:5]:
        print('   %-18s -> %s' % (k, cmap[k]))
    print('[map] quan hệ dùng: ' + ', '.join('%s=%s' % (k, rmap.get(k, '?')) for k in sorted(keep or rmap)))
    if not cmap:
        sys.exit('Không đọc được bản dịch nào từ --classes. Gửi mình vài dòng đầu của file để chỉnh.')

    t = time.time(); n = 0; edges = {}; skipped_rel = Counter()
    with open(a.triples, encoding='utf-8', errors='replace') as f:
        for line in f:
            n += 1
            p = line.rstrip('\r\n').split('\t')
            if len(p) < 3 or not p[1].startswith('/r/'):
                continue
            r = p[1][3:]
            if keep is not None and r not in keep:
                continue
            h, tl = node_label(p[0]), node_label(p[2])
            if not h or not tl or h == tl or h not in cmap or tl not in cmap:
                continue
            if r not in rmap:
                skipped_rel[r] += 1
                continue
            edges[(h, r, tl)] = 1
    print('[cskg] đọc %d dòng trong %.1fs, giữ %d cạnh' % (n, time.time() - t, len(edges)))
    if skipped_rel:
        print('[cskg] bỏ vì chưa có tên tiếng Việt cho quan hệ:', dict(skipped_rel))

    # gộp cạnh trùng sau khi dịch (nhiều từ tiếng Anh -> cùng một từ tiếng Việt)
    merged = defaultdict(list)
    for (h, r, tl) in sorted(edges):
        merged[(cmap[h], r, cmap[tl])].append((h, tl))
    print('[gop] %d cạnh tiếng Anh -> %d cạnh tiếng Việt sau khi gộp trùng' % (len(edges), len(merged)))

    # giới hạn nút trung tâm: mỗi (đầu, quan hệ) và mỗi (quan hệ, đuôi) giữ tối đa K cạnh, ưu tiên nút ít kết nối
    if a.max_per_node_rel > 0:
        deg0 = Counter()
        for (h, r, tl) in merged:
            deg0[h] += 1; deg0[tl] += 1
        K = a.max_per_node_rel
        for side in (0, 1):
            groups = defaultdict(list)
            for (h, r, tl) in merged:
                groups[((h, r) if side == 0 else (r, tl))].append((h, r, tl))
            drop = set()
            for g, es in groups.items():
                if len(es) > K:
                    es.sort(key=lambda e: (deg0[e[2]] if side == 0 else deg0[e[0]], e))
                    drop.update(es[K:])
            for e in drop:
                merged.pop(e, None)
        print('[gioi han] max %d cạnh/(nút, quan hệ) -> còn %d cạnh' % (K, len(merged)))

    en_of = {}
    for (h, r, tl), srcs in merged.items():
        en_of[(h, r, tl)] = srcs[0]
    nodes = sorted({x for h, _, tl in merged for x in (h, tl)})
    deg = Counter()
    for h, _, tl in merged:
        deg[h] += 1; deg[tl] += 1
    vi2en = defaultdict(set)
    for en, vi in cmap.items():
        vi2en[vi].add(en)
    rows = []
    rev = {v: k for k, v in rmap.items()}
    # rel_en lấy lại từ khoá gốc
    rel_en_of = {}
    for (h, r, tl) in edges:
        rel_en_of[(cmap[h], r, cmap[tl])] = r
    for (h, r, tl) in sorted(merged):
        he, te = en_of[(h, r, tl)]
        rows.append((h, rmap[r], tl, he, r, te))
    with open(a.out + '.tsv', 'w', encoding='utf-8') as f:
        f.write('dau_vi\tquan_he_vi\tduoi_vi\tdau_en\tquan_he_en\tduoi_en\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    json.dump({
        'nodes': [{'vi': x, 'en': sorted(vi2en.get(x, [])), 'degree': deg[x]} for x in nodes],
        'edges': [{'head': r[0], 'rel': r[1], 'tail': r[2], 'head_en': r[3], 'rel_en': r[4], 'tail_en': r[5]} for r in rows],
        'stats': {'n_nodes': len(nodes), 'n_edges': len(rows), 'by_relation': dict(Counter(r[4] for r in rows)),
                  'nodes_without_edges': sum(1 for k in cmap if cmap[k] not in deg)}},
        open(a.out + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(a.out + '_nghi_ngo.tsv', 'w', encoding='utf-8') as f:
        f.write('nut_vi\tbac\tso_tu_anh_cung_ban_dich\tcac_tu_anh\n')
        for x in sorted(nodes, key=lambda x: -deg[x]):
            ens = sorted(vi2en.get(x, []))
            if deg[x] >= 50 or len(ens) > 1:
                f.write('%s\t%d\t%d\t%s\n' % (x, deg[x], len(ens), ', '.join(ens)))
    print('[ghi]', a.out + '_nghi_ngo.tsv', '(nút bậc cao hoặc nhiều từ Anh cùng một bản dịch, nên rà tay)')
    st = Counter(r[4] for r in rows)
    print('[ket qua] %d nút, %d cạnh | theo quan hệ: %s' % (len(nodes), len(rows), dict(st)))
    print('[ket qua] %d/%d nút trong class_mapping chưa có cạnh nào' % (sum(1 for k in cmap if cmap[k] not in deg), len(cmap)))
    for r in rows[:8]:
        print('   %s --%s--> %s' % (r[0], r[1], r[2]))
    print('[ghi]', a.out + '.tsv', '|', a.out + '.json')

    if a.export_candidates > 0:
        cnt = Counter(); ctx = defaultdict(list); t = time.time()
        with open(a.triples, encoding='utf-8', errors='replace') as f:
            for line in f:
                p = line.rstrip('\r\n').split('\t')
                if len(p) < 3 or not p[1].startswith('/r/'):
                    continue
                if keep is not None and p[1][3:] not in keep:
                    continue
                h, tl = node_label(p[0]), node_label(p[2])
                if not h or not tl or h == tl:
                    continue
                if h in cmap and tl not in cmap and tl.replace(' ', '').isalpha():
                    cnt[tl] += 1
                    if len(ctx[tl]) < 4:
                        ctx[tl].append('%s %s %s' % (h, p[1][3:], tl))
                elif tl in cmap and h not in cmap and h.replace(' ', '').isalpha():
                    cnt[h] += 1
                    if len(ctx[h]) < 4:
                        ctx[h].append('%s %s %s' % (h, p[1][3:], tl))
        with open(a.out + '_can_dich.tsv', 'w', encoding='utf-8') as f:
            f.write('tu_anh\tso_ket_noi_voi_tu_da_dich\tngu_canh\n')
            for w, c in cnt.most_common(a.export_candidates):
                f.write('%s\t%d\t%s\n' % (w, c, ' ; '.join(ctx[w])))
        print('[ghi]', a.out + '_can_dich.tsv', '(%d ứng viên, xuất %d, %.1fs)' % (len(cnt), min(len(cnt), a.export_candidates), time.time() - t))


if __name__ == '__main__':
    main()