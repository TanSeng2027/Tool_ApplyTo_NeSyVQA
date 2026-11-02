"""
Làm giàu scene graph bằng triplet CSKG.

Đầu vào : 3 file từ vựng (class / attr / rels .pkl) + cskg_triples_uri.tsv + 1 scene graph
Đầu ra  : <out>.json (nodes, edges) và <out>.png (hình scene graph đã làm giàu)

Chạy thử:  python enrich_sg.py
Dùng riêng: sửa SCENE_GRAPH ở cuối file, hoặc gọi enrich(scene_graph) từ code khác.
"""
import json
import pickle
from collections import defaultdict

import pandas as pd

# ---------------- CẤU HÌNH (sửa đường dẫn cho khớp máy bạn) ----------------
DIR_PKL = r"D:\6.Tool"
TRIPLES = r"D:\6.Tool\cskg_triples_uri.tsv"
CLASS_PKL = DIR_PKL + r"\train_val_gt_class.pkl"
ATTR_PKL = DIR_PKL + r"\train_val_gt_attr.pkl"
RELS_PKL = DIR_PKL + r"\train_val_gt_rels.pkl"

# Chỉ giữ các quan hệ CSKG mang kiến thức thường thức, bỏ RelatedTo (nhiễu)
KEEP_REL = {"/r/IsA", "/r/PartOf", "/r/HasA", "/r/UsedFor", "/r/AtLocation",
            "/r/CapableOf", "/r/MadeOf", "/r/HasProperty"}

# Quan hệ CSKG -> predicate trong từ vựng (chỉ ánh xạ nếu predicate có trong rels.pkl)
REL_TO_VOCAB = {"/r/PartOf": "of", "/r/HasA": "with", "/r/AtLocation": "in"}

TOP_K = 3          # số cạnh tối đa thêm cho mỗi object
VOCAB_ONLY = True  # True: chỉ giữ node CSKG nằm trong từ vựng object (giống notebook)
# ---------------------------------------------------------------------------


def load_vocab(path):
    return [w for w in pickle.load(open(path, "rb")) if w != "__background__"]


def to_uri(label):
    return "/c/en/" + label.strip().lower().replace(" ", "_")


def from_uri(uri):
    return uri.split("/")[3].replace("_", " ") if uri.startswith("/c/en/") else None


def build_index(classes, chunk=500_000):
    """Đọc 5,7 triệu triplet theo chunk, chỉ giữ cạnh liên quan tới từ vựng object."""
    vocab_uri = {to_uri(c) for c in classes}
    keep = []
    for ch in pd.read_csv(TRIPLES, sep="\t", header=None, names=["h", "r", "t"],
                          dtype=str, chunksize=chunk):
        ch = ch[ch["r"].isin(KEEP_REL) & (ch["h"] != ch["t"])]
        ch = ch[ch["h"].isin(vocab_uri) | ch["t"].isin(vocab_uri)]
        if VOCAB_ONLY:
            ch = ch[ch["h"].isin(vocab_uri) & ch["t"].isin(vocab_uri)]
        keep.append(ch)
    df = pd.concat(keep).drop_duplicates()
    index = defaultdict(list)
    for h, r, t in df.itertuples(index=False):
        index[h].append((r, t))
        index[t].append((r, h, "in"))   # đánh dấu cạnh đi vào
    return index, vocab_uri


def coverage_report(classes, attrs, rels, index, vocab_uri):
    linked = [c for c in classes if to_uri(c) in index]
    print(f"Object: {len(classes)} | có cạnh trong CSKG: {len(linked)} "
          f"({100 * len(linked) / len(classes):.1f}%)")
    print(f"Attribute: {len(attrs)} | Predicate: {len(rels)}")


def enrich(scene_graph, index, rels_vocab, top_k=TOP_K):
    """
    scene_graph: list (subj, pred, obj), ví dụ [("man", "riding", "horse")]
    Trả về dict {nodes, edges}. Node/cạnh từ ảnh có src='sg', từ CSKG có src='cskg'.
    """
    nodes, edges = {}, []

    def add_node(label, src):
        if label not in nodes:
            nodes[label] = {"label": label, "src": src}

    for s, p, o in scene_graph:
        add_node(s, "sg"); add_node(o, "sg")
        edges.append({"head": s, "rel": p, "tail": o, "src": "sg", "rel_vocab": p})

    seen = {(e["head"], e["rel"], e["tail"]) for e in edges}
    objs = [n for n in list(nodes)]
    for obj in objs:
        cands = []
        for item in index.get(to_uri(obj), []):
            if len(item) == 3:                     # cạnh đi vào: (r, other, 'in')
                r, other, _ = item
                head, tail = from_uri(other), obj
            else:                                  # cạnh đi ra
                r, other = item
                head, tail = obj, from_uri(other)
            other_label = from_uri(other)
            if other_label is None:
                continue
            # ưu tiên cạnh nối với object đang có trong ảnh (đúng ngữ cảnh)
            in_scene = other_label in nodes
            cands.append((in_scene, r, head, tail))
        cands.sort(key=lambda x: (not x[0],))      # in_scene lên đầu
        # mỗi loại quan hệ chỉ lấy 1 cạnh, tối đa top_k
        used_rel, added = set(), 0
        for in_scene, r, head, tail in cands:
            if added >= top_k:
                break
            if r in used_rel or (head, r, tail) in seen or head == tail:
                continue
            used_rel.add(r); added += 1; seen.add((head, r, tail))
            add_node(head, "cskg"); add_node(tail, "cskg")
            v = REL_TO_VOCAB.get(r)
            edges.append({"head": head, "rel": r.replace("/r/", ""), "tail": tail,
                          "src": "cskg", "rel_vocab": v if v in rels_vocab else None})
    return {"nodes": list(nodes.values()), "edges": edges}


def draw(graph, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    G = nx.DiGraph()
    for n in graph["nodes"]:
        G.add_node(n["label"], src=n["src"])
    for e in graph["edges"]:
        G.add_edge(e["head"], e["tail"], rel=e["rel"], src=e["src"])
    pos = nx.spring_layout(G, seed=3, k=1.2)
    fig, ax = plt.subplots(figsize=(11, 8))
    sg_nodes = [n for n, d in G.nodes(data=True) if d["src"] == "sg"]
    cs_nodes = [n for n, d in G.nodes(data=True) if d["src"] == "cskg"]
    nx.draw_networkx_nodes(G, pos, nodelist=sg_nodes, node_color="black", node_shape="s",
                           node_size=2600, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=cs_nodes, node_color="#9ecae1", node_shape="o",
                           node_size=2600, ax=ax)
    nx.draw_networkx_labels(G, pos, labels={n: n for n in sg_nodes}, font_color="white",
                            font_size=9, ax=ax)
    nx.draw_networkx_labels(G, pos, labels={n: n for n in cs_nodes}, font_size=9, ax=ax)
    sg_e = [(u, v) for u, v, d in G.edges(data=True) if d["src"] == "sg"]
    cs_e = [(u, v) for u, v, d in G.edges(data=True) if d["src"] == "cskg"]
    nx.draw_networkx_edges(G, pos, edgelist=sg_e, ax=ax, node_size=2600, arrowsize=18,
                           connectionstyle="arc3,rad=0.1")
    nx.draw_networkx_edges(G, pos, edgelist=cs_e, ax=ax, node_size=2600, style="dashed",
                           edge_color="gray", arrowsize=18, connectionstyle="arc3,rad=0.1")
    nx.draw_networkx_edge_labels(G, pos, ax=ax, font_size=8,
                                 edge_labels={(u, v): d["rel"] for u, v, d in G.edges(data=True)})
    ax.set_title("Đen/liền = scene graph (từ ảnh)   |   Xanh/đứt = kiến thức CSKG")
    ax.axis("off")
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    classes, attrs, rels = load_vocab(CLASS_PKL), load_vocab(ATTR_PKL), load_vocab(RELS_PKL)
    print("Đang đọc CSKG (vài phút)...")
    index, vocab_uri = build_index(classes)
    coverage_report(classes, attrs, rels, index, vocab_uri)

    # Scene graph mẫu: thay bằng kết quả mô hình SGG hoặc ground truth của bạn.
    SCENE_GRAPH = [("man", "riding", "horse"), ("man", "wearing", "hat"),
                   ("horse", "on", "grass")]
    SCENE_GRAPH = [t for t in SCENE_GRAPH if t[0] in classes and t[2] in classes
                   and t[1] in rels]          # chỉ giữ nhãn nằm trong từ vựng

    g = enrich(SCENE_GRAPH, index, set(rels))
    json.dump(g, open("enriched_sg.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    draw(g, "enriched_sg.png")
    for e in g["edges"]:
        print(f'[{e["src"]:4}] {e["head"]} --{e["rel"]}--> {e["tail"]}')
    print("Đã lưu enriched_sg.json và enriched_sg.png")
