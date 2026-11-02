# -*- coding: utf-8 -*-
r"""
translate_graph.py - Đổi scene graph đã làm giàu (enrich_batch.py) sang TIẾNG VIỆT + sinh văn bản mô tả cho mô hình VQA.

Vào : enriched_batch\_tong_hop.json   (từ enrich_batch.py)
      translated_nodes.tsv            (bản dịch mọi nút CSKG, từ bước Google Translate)
      class_mapping_vi.json           (bảng dịch riêng của bạn, ƯU TIÊN hơn translated_nodes)
      rels_mapping_vi.json            (tuỳ chọn; dịch quan hệ VG như on, wearing...)
      sua_dich.json                   (tuỳ chọn; sửa tay, ưu tiên cao nhất)
Ra  : vi_graphs\vi_graphs.json        (đồ thị tiếng Việt từng ảnh: nút, cạnh, cả nhãn Anh gốc)
      vi_graphs\vi_graphs.jsonl       (mỗi dòng 1 ảnh, 3 trường văn bản dưới đây - tiện đưa vào mô hình)
      vi_graphs\thieu_ban_dich.tsv    (nhãn chưa có bản dịch / giữ nguyên tiếng Anh, để bạn bổ sung)

Ba trường văn bản (dùng cho thí nghiệm so sánh):
  mo_ta_sgg          chỉ quan hệ từ SGG                    (điều kiện b: scene graph thường)
  tri_thuc           chỉ các cạnh tri thức thêm từ CSKG
  mo_ta_lam_giau     mo_ta_sgg + tri_thuc                  (điều kiện c: scene graph đã làm giàu)
Chạy: python translate_graph.py --graphs enriched_batch\_tong_hop.json --nodes translated_nodes.tsv --classes class_mapping_vi.json
"""
import argparse, csv, json, os
from build_vi_kg import DEFAULT_REL_VI, load_map
from apply_translation import EXTRA_REL_VI

# 50 quan hệ VG150 -> tiếng Việt (bị rels_mapping_vi.json ghi đè nếu có)
VG_PRED_VI = {
    'above': 'ở phía trên', 'across': 'băng qua', 'against': 'dựa vào', 'along': 'dọc theo', 'and': 'và', 'at': 'ở',
    'attached to': 'gắn vào', 'behind': 'ở phía sau', 'belonging to': 'thuộc về', 'between': 'ở giữa', 'carrying': 'mang',
    'covered in': 'được phủ bởi', 'covering': 'che phủ', 'eating': 'đang ăn', 'flying in': 'bay trong', 'for': 'dành cho',
    'from': 'từ', 'growing on': 'mọc trên', 'hanging from': 'treo từ', 'has': 'có', 'holding': 'cầm', 'in': 'trong',
    'in front of': 'ở phía trước', 'laying on': 'nằm trên', 'looking at': 'nhìn', 'lying on': 'nằm trên', 'made of': 'làm từ',
    'mounted on': 'gắn trên', 'near': 'gần', 'of': 'của', 'on': 'trên', 'on back of': 'ở phía sau lưng', 'over': 'phía trên',
    'painted on': 'được vẽ trên', 'parked on': 'đỗ trên', 'part of': 'là một phần của', 'playing': 'đang chơi', 'riding': 'đang cưỡi',
    'says': 'ghi', 'sitting on': 'ngồi trên', 'standing on': 'đứng trên', 'to': 'tới', 'under': 'ở dưới', 'using': 'sử dụng',
    'walking in': 'đi trong', 'walking on': 'đi trên', 'watching': 'đang xem', 'wearing': 'mặc', 'wears': 'mặc', 'with': 'có',
}


def load_nodes(path):
    d = {}
    with open(path, encoding='utf-8') as f:
        next(f)
        for l in f:
            p = l.rstrip('\r\n').split('\t')
            if len(p) >= 4 and p[1]:
                d[p[0]] = (p[1], p[3])
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--graphs', required=True)
    ap.add_argument('--nodes', default='translated_nodes.tsv')
    ap.add_argument('--classes', default='class_mapping_vi.json')
    ap.add_argument('--rels', default='rels_mapping_vi.json')
    ap.add_argument('--overrides', default='sua_dich.json')
    ap.add_argument('--out', default='vi_graphs')
    a = ap.parse_args()

    graphs = json.load(open(a.graphs, encoding='utf-8'))
    nodes_tr = load_nodes(a.nodes) if os.path.isfile(a.nodes) else {}
    cmap = {k.lower(): v for k, v in load_map(a.classes).items()} if os.path.isfile(a.classes) else {}
    ovr = {k.lower(): v for k, v in load_map(a.overrides).items()} if os.path.isfile(a.overrides) else {}
    pred_vi = dict(VG_PRED_VI)
    if os.path.isfile(a.rels):
        pred_vi.update({k.lower(): v for k, v in load_map(a.rels).items()})
    cskg_vi = dict(DEFAULT_REL_VI); cskg_vi.update(EXTRA_REL_VI)
    print('[bang] %d nút Google, %d bảng riêng, %d sửa tay, %d quan hệ VG' % (len(nodes_tr), len(cmap), len(ovr), len(pred_vi)))

    missing = {}
    def tr(w):
        k = w.lower()
        if k in ovr: return ovr[k]
        if k in cmap: return cmap[k]
        if k in nodes_tr:
            v, st = nodes_tr[k]
            if st == 'kiem_tra' and v.lower() == k:
                missing.setdefault(w, 'giu_nguyen_tieng_Anh')
            return v
        missing.setdefault(w, 'khong_co_ban_dich')
        return w

    def rel_vi(e):
        r = e['rel']
        return pred_vi.get(r.lower(), r) if e['src'] == 'sg' else cskg_vi.get(r, pred_vi.get(r.lower(), r))

    out = {}; lines = []
    for k in sorted(graphs, key=int):
        g = graphs[k]
        nodes = [{'en': n['label'], 'vi': tr(n['label']), 'src': n['src']} for n in g['nodes']]
        edges = []
        for e in g['edges']:
            edges.append({'head': tr(e['head']), 'rel': rel_vi(e), 'tail': tr(e['tail']), 'src': e['src'],
                          'head_en': e['head'], 'rel_en': e['rel'], 'tail_en': e['tail']})
        def sent(es):
            seen, res = set(), []
            for e in es:
                s = '%s %s %s' % (e['head'], e['rel'], e['tail'])
                if e['head'] != e['tail'] and s not in seen:
                    seen.add(s); res.append(s)
            return '. '.join(res) + ('.' if res else '')
        sg = [e for e in edges if e['src'] == 'sg']
        sg_sent = {'%s %s %s' % (e['head'], e['rel'], e['tail']) for e in sg}
        ks = [e for e in edges if e['src'] != 'sg' and '%s %s %s' % (e['head'], e['rel'], e['tail']) not in sg_sent]   # bỏ câu đã có ở SGG
        rec = {'image': g.get('image', k), 'nodes': nodes, 'edges': edges,
               'mo_ta_sgg': sent(sg), 'tri_thuc': sent(ks), 'mo_ta_lam_giau': sent(sg + ks)}
        out[k] = rec; lines.append(rec)
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(os.path.join(a.out, 'vi_graphs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, 'vi_graphs.jsonl'), 'w', encoding='utf-8') as f:
        for r in lines:
            f.write(json.dumps({'image': r['image'], 'mo_ta_sgg': r['mo_ta_sgg'], 'tri_thuc': r['tri_thuc'], 'mo_ta_lam_giau': r['mo_ta_lam_giau']}, ensure_ascii=False) + '\n')
    with open(os.path.join(a.out, 'thieu_ban_dich.tsv'), 'w', encoding='utf-8') as f:
        f.write('nhan_anh\tvan_de\n')
        for w, v in sorted(missing.items()):
            f.write('%s\t%s\n' % (w, v))
    print('[xong] %d ảnh | nhãn có vấn đề: %d (xem thieu_ban_dich.tsv)' % (len(out), len(missing)))
    if lines:
        r = lines[0]
        print('--- ví dụ ảnh %s ---' % r['image']); print('SGG      :', r['mo_ta_sgg'][:300]); print('Tri thức :', r['tri_thuc'][:300])
    print('[ghi]', a.out)


if __name__ == '__main__':
    main()
