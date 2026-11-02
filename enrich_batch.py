# -*- coding: utf-8 -*-
r"""
enrich_batch.py - Làm giàu scene graph bằng CSKG cho NHIỀU ảnh một lượt (đọc file CSKG 1 lần).
Nối kết quả SGG (sgg_slim\custom_prediction.json + custom_data_info.json, từ Kaggle) vào enrich_sg.py của bạn.

Chạy:  python enrich_batch.py --dir sgg_slim --out enriched_batch [--topk 10] [--rel-topn 15] [--png] [--limit 3]
Ra  :  enriched_batch\<so>_<ten_anh>.json (mỗi ảnh)   enriched_batch\_tong_hop.json   enriched_batch\_thong_ke.tsv
       (--png: vẽ thêm hình, chậm hơn)
"""
import argparse, json, os, time
import enrich_sg as E


def triples_for_image(p, cls, prd, topk, rel_topn):
    labels = [cls[i] for i in p['bbox_labels'][:topk]]
    triples, seen = [], set()
    for (s, o), r, sc in sorted(zip(p['rel_pairs'], p['rel_labels'], p['rel_scores']), key=lambda x: -x[2]):
        if s < topk and o < topk and labels[s] != labels[o]:
            t = (labels[s], prd[r], labels[o])
            if t not in seen:
                seen.add(t); triples.append(t)
        if len(triples) >= rel_topn:
            break
    return labels, triples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='sgg_slim', help='thư mục chứa custom_prediction.json và custom_data_info.json')
    ap.add_argument('--out', default='enriched_batch')
    ap.add_argument('--topk', type=int, default=10)
    ap.add_argument('--rel-topn', type=int, default=15)
    ap.add_argument('--png', action='store_true', help='vẽ thêm hình mỗi ảnh (chậm hơn)')
    ap.add_argument('--limit', type=int, default=0, help='chỉ chạy N ảnh đầu để thử (0 = tất cả)')
    a = ap.parse_args()

    pred = json.load(open(os.path.join(a.dir, 'custom_prediction.json'), encoding='utf-8'))
    info = json.load(open(os.path.join(a.dir, 'custom_data_info.json'), encoding='utf-8'))
    cls, prd = info['ind_to_classes'], info['ind_to_predicates']
    files = info['idx_to_files']
    print('[anh] %d ảnh' % len(pred))

    try:
        classes, attrs, rels = E.load_vocab(E.CLASS_PKL), E.load_vocab(E.ATTR_PKL), E.load_vocab(E.RELS_PKL)
    except FileNotFoundError as ex:
        print('Không có file từ vựng .pkl (%s) -> dùng từ vựng VG150 của SGG' % ex.filename)
        classes = [c for c in cls if c != '__background__']; rels = [r for r in prd if r != '__background__']
    t = time.time(); print('Đang đọc CSKG (vài phút, chỉ 1 lần)...')
    index, _ = E.build_index(classes)
    print('[cskg] xong sau %.0fs' % (time.time() - t))

    os.makedirs(a.out, exist_ok=True); allg = {}; stats = []
    keys = sorted(pred, key=int)
    if a.limit:
        keys = keys[:a.limit]
    for k in keys:
        idx = int(k)
        name = os.path.splitext(os.path.basename(files[idx]))[0] if idx < len(files) else k
        labels, triples = triples_for_image(pred[k], cls, prd, a.topk, a.rel_topn)
        g = E.enrich(triples, index, set(rels))
        g['image'] = os.path.basename(files[idx]) if idx < len(files) else k
        allg[k] = g
        json.dump(g, open(os.path.join(a.out, '%s.json' % name), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        if a.png:
            E.draw(g, os.path.join(a.out, '%s.png' % name))
        n_cs = sum(1 for e in g['edges'] if e['src'] == 'cskg')
        stats.append((name, len(set(labels)), len(triples), len(g['edges']) - n_cs, n_cs))
    json.dump(allg, open(os.path.join(a.out, '_tong_hop.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    with open(os.path.join(a.out, '_thong_ke.tsv'), 'w', encoding='utf-8') as f:
        f.write('anh\tso_nhan_vat_the\tso_bo_ba_SGG\tso_canh_SGG\tso_canh_CSKG_them_vao\n')
        for s in stats:
            f.write('%s\t%d\t%d\t%d\t%d\n' % s)
    import statistics
    print('[xong] %d ảnh | trung bình mỗi ảnh: %.1f bộ ba SGG, %.1f cạnh CSKG thêm | ảnh KHÔNG được thêm cạnh nào: %d'
          % (len(stats), statistics.mean(s[2] for s in stats), statistics.mean(s[4] for s in stats), sum(1 for s in stats if s[4] == 0)))
    print('[ghi]', a.out)


if __name__ == '__main__':
    main()