import pickle                                         # dùng để serialize (lưu) object Python xuống file
import time                                           # đo thời gian thực thi
from pathlib import Path                              # thao tác đường dẫn file hiện đại
from typing import Iterable, List, Set, Tuple, Union  # typing cho code rõ ràng
import networkx as nx                                 # thư viện tạo graph
import spacy                                          # thư viện NLP
from pyvis.network import Network                     # Xem tree trực quan

_NLP = None # biến global để cache model spaCy

def _load_spacy_model():
    """
    Load model spaCy (en_core_web_sm).
    """
    global _NLP
    if _NLP is not None:
        return _NLP
    
    _NLP = spacy.load("en_core_web_sm")
    return _NLP

def _phrase_text(token):
    """
    Lấy toàn bộ phrase (cụm từ) liên quan đến token.
    Ví dụ: "the big red car"
    """
    return token.doc[token.left_edge.i : token.right_edge.i + 1].text.strip()

def _entity_text(token):
    """
    Ưu tiên lấy Named Entity (NER) nếu token nằm trong entity.
    Nếu không thì lấy phrase.
    """
    for ent in token.doc.ents:
        if token.i >= ent.start and token.i < ent.end:
            return ent.text
    return _phrase_text(token)


def _extract_triples_from_sentence(sent):
    """
    Extract triples (subject, relation, object) từ 1 câu.
    """
    triples = []

    for token in sent:
        if token.pos_ not in {"VERB", "AUX"} and token.dep_ != "ROOT":
            continue

        subjects = [
            child
            for child in token.lefts
            if child.dep_ in {"nsubj", "nsubjpass", "csubj", "agent", "expl"}
        ]

        objects = [
            child
            for child in token.rights
            if child.dep_ in {"dobj", "obj", "pobj", "dative", "attr", "oprd", "acomp"}
        ]

        for child in token.rights:
            if child.dep_ == "prep":
                objects.extend(
                    [grandchild for grandchild in child.children if grandchild.dep_ == "pobj"]
                )

        if not subjects or not objects:
            continue

        relation = token.lemma_.lower().strip()
        if not relation:
            relation = token.text.lower().strip()

        for subject in subjects:
            subject_text = _entity_text(subject)
            for obj in objects:
                object_text = _entity_text(obj)
                if subject_text and relation and object_text:
                    triples.append((subject_text, relation, object_text))

    return triples


def extract_triples(documents: Iterable[Union[str, object]]):
    """
    Input: danh sách document (string hoặc object có page_content)
    Output:
        - thời gian xử lý
        - danh sách triples (subject, relation, object)
    """
    start_time = time.time()
    nlp = _load_spacy_model()

    triples: List[Tuple[str, str, str]] = []
    seen: Set[Tuple[str, str, str]] = set()

    for document in documents:
        text = document.page_content

        if not text or not text.strip():
            continue

        # Gồm 1 Chunk
        # Mỗi chunk gồm các token chứa
        #   token.text, 
        #   token.pos_,
        #   token.dep_,
        #   token.head.text
        parsed = nlp(text)

        for sent in parsed.sents:
            for triple in _extract_triples_from_sentence(sent):
                normalized = tuple(part.strip() for part in triple)
                if normalized not in seen:
                    seen.add(normalized)
                    triples.append(normalized)

    elapsed = round(time.time() - start_time, 2)
    return elapsed, triples


def build_graph(triples: Iterable[Tuple[str, str, str]]) -> nx.DiGraph:
    """
    Xây dựng directed graph từ triples.
    Node: subject, object
    Edge: subject -> object với relation
    """
    start_time = time.time()
    graph = nx.DiGraph()

    for subject, relation, object_ in triples:
        if graph.has_edge(subject, object_):
            relations = graph[subject][object_].get("relations", [])
            if relation not in relations:
                relations.append(relation)
            graph[subject][object_]["relations"] = relations
            graph[subject][object_]["count"] = graph[subject][object_].get("count", 0) + 1
        else:
            graph.add_edge(subject, object_, relations=[relation], count=1)
    
    elapsed = round(time.time() - start_time, 2)
    _export_graph_html(graph)
    return elapsed, graph


def save_graph(graph: nx.DiGraph, path: str = "graph.pkl") -> Path:
    """
    Lưu graph xuống file bằng pickle.
    """
    start_time = time.time()
    save_path = Path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with save_path.open("wb") as file:
        pickle.dump(graph, file)

    elapsed = round(time.time() - start_time, 2)
    return elapsed, save_path

def _export_graph_html(graph):
    """
    Hiển thị UI để xem cấu trúc GRAPH RAG
    """
    net = Network(
        height="700px",
        width="100%",
        bgcolor="#111111",   # nền tối
        font_color="white",
        directed=True
    )

    # physics cho layout mượt
    net.barnes_hut()

    # 🎯 phân loại node theo vai trò
    subjects = set(u for u, v in graph.edges())
    objects = set(v for u, v in graph.edges())

    for node in graph.nodes():
        if node in subjects and node in objects:
            color = "#f39c12"  # vừa subject vừa object
            size = 25
        elif node in subjects:
            color = "#00bfff"  # subject
            size = 30
        else:
            color = "#2ecc71"  # object
            size = 20

        net.add_node(
            node,
            label=node,
            title=node,
            shape="box",
            color=color,
            size=size
        )

    # 🎯 edge đẹp hơn
    for u, v, data in graph.edges(data=True):
        label = ", ".join(data["relations"])

        net.add_edge(
            u,
            v,
            label=label,
            color="#aaaaaa",
            arrows="to",
            font={"size": 12, "align": "middle"}
        )

    net.add_node(
        "LEGEND_SUBJECT",
        label="Subject",
        color="#00bfff",
        shape="dot",
        x=800, y=300,
        physics=False,
        fixed=True
    )

    net.add_node(
        "LEGEND_OBJECT",
        label="Object",
        color="#2ecc71",
        shape="dot",
        x=800, y=200,
        physics=False,
        fixed=True
    )

    net.add_node(
        "LEGEND_BOTH",
        label="Subject + Object",
        color="#f39c12",
        shape="dot",
        x=800, y=100,
        physics=False,
        fixed=True
    )

    # 🎯 thêm hiệu ứng hover
    net.set_options("""
    var options = {
    "nodes": {
        "borderWidth": 2,
        "shadow": true
    },
    "edges": {
        "smooth": {
        "type": "dynamic"
        }
    },
    "physics": {
        "barnesHut": {
        "gravitationalConstant": -3000,
        "centralGravity": 0.3,
        "springLength": 150
        },
        "minVelocity": 0.75
    },
    "layout": {
        "improvedLayout": true
    }
    }
    """)
    net.write_html("graph.html")
