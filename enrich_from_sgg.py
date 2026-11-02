r"""
Nối kết quả SGG (Kaggle) vào enrich_sg.py của bạn.
Chạy:  python enrich_from_sgg.py sgg_out\custom_prediction.json [--topk 10] [--rel-topn 15] [--name img1]
Cần để cùng thư mục với enrich_sg.py và custom_data_info.json (hoặc dùng --info).
"""
import argparse, json, os
import enrich_sg as E

ap = argparse.ArgumentParser()
ap.add_argument("pred")
ap.add_argument("--info")
ap.add_argument("--topk", type=int, default=10)
ap.add_argument("--rel-topn", type=int, default=15)
ap.add_argument("--name", default="enriched_sgg")
ap.add_argument("--image", default="0", help="khóa ảnh trong file (mặc định lấy ảnh đầu)")
a = ap.parse_args()

info = json.load(open(a.info or os.path.join(os.path.dirname(os.path.abspath(a.pred)), "custom_data_info.json"), encoding="utf-8"))
cls, prd = info["ind_to_classes"], info["ind_to_predicates"]
raw = json.load(open(a.pred, encoding="utf-8"))
if "bbox" in raw:
    p = raw
else:
    keys = list(raw.keys())
    print("Các khóa trong file:", keys[:5])
    p = raw[a.image] if a.image in raw else raw[keys[0]]
labels = [cls[i] for i in p["bbox_labels"][:a.topk]]

triples, seen = [], set()
for (s, o), r, sc in sorted(zip(p["rel_pairs"], p["rel_labels"], p["rel_scores"]), key=lambda x: -x[2]):
    if s < a.topk and o < a.topk and labels[s] != labels[o]:
        t = (labels[s], prd[r], labels[o])
        if t not in seen:
            seen.add(t); triples.append(t)
    if len(triples) >= a.rel_topn:
        break

try:
    classes, attrs, rels = E.load_vocab(E.CLASS_PKL), E.load_vocab(E.ATTR_PKL), E.load_vocab(E.RELS_PKL)
except FileNotFoundError as ex:
    print("Không có file từ vựng .pkl (%s) -> dùng từ vựng VG150 của SGG" % ex.filename)
    classes = [c for c in cls if c != "__background__"]
    rels = [r for r in prd if r != "__background__"]
miss = sorted({x for s, _, o in triples for x in (s, o) if x not in classes})
if miss:
    print("Lưu ý: nhãn VG không có trong từ vựng GQA (không tra được CSKG):", miss)
print("Đang đọc CSKG (vài phút)...")
index, vocab_uri = E.build_index(classes)
g = E.enrich(triples, index, set(rels))
json.dump(g, open(a.name + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
E.draw(g, a.name + ".png")
for e in g["edges"]:
    print(f'[{e["src"]:4}] {e["head"]} --{e["rel"]}--> {e["tail"]}')
print("Đã lưu", a.name + ".json", "và", a.name + ".png")