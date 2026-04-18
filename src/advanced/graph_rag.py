import pickle
import time
from pathlib import Path
from typing import Iterable, List, Set, Tuple, Union

import networkx as nx

try:
    import spacy
except ImportError:  # pragma: no cover
    spacy = None

_NLP = None


def _load_spacy_model():
    global _NLP
    if _NLP is not None:
        return _NLP

    if spacy is None:
        raise RuntimeError(
            "spaCy is required for extract_triples. "
            "Install it with `python -m spacy download en_core_web_sm`."
        )

    try:
        _NLP = spacy.load("en_core_web_sm")
    except OSError:
        from spacy.cli import download

        download("en_core_web_sm")
        _NLP = spacy.load("en_core_web_sm")

    return _NLP


def _phrase_text(token):
    return token.doc[token.left_edge.i : token.right_edge.i + 1].text.strip()


def _entity_text(token):
    for ent in token.doc.ents:
        if token.i >= ent.start and token.i < ent.end:
            return ent.text
    return _phrase_text(token)


def _extract_triples_from_sentence(sent):
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
    start_time = time.time()
    nlp = _load_spacy_model()

    triples: List[Tuple[str, str, str]] = []
    seen: Set[Tuple[str, str, str]] = set()

    for document in documents:
        if hasattr(document, "page_content"):
            text = document.page_content
        elif isinstance(document, str):
            text = document
        else:
            text = str(document)

        if not text or not text.strip():
            continue

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
    return elapsed, graph


def save_graph(graph: nx.DiGraph, path: str = "graph.pkl") -> Path:
    start_time = time.time()
    save_path = Path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with save_path.open("wb") as file:
        pickle.dump(graph, file)

    elapsed = round(time.time() - start_time, 2)
    return elapsed, save_path
