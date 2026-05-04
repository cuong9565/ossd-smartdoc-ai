from .db import getConnection
from langchain_core.documents import Document
import json


def _serialize_documents(documents):
    serialized_documents = []
    for document in documents or []:
        page_content = getattr(document, "page_content", None)
        metadata = getattr(document, "metadata", {}) or {}
        if page_content is None and isinstance(document, dict):
            page_content = document.get("page_content", "")
            metadata = document.get("metadata", {}) or {}
        serialized_documents.append(
            {
                "page_content": page_content or "",
                "metadata": metadata,
            }
        )
    return serialized_documents


def _deserialize_documents(documents_json):
    try:
        documents = json.loads(documents_json) if documents_json else []
    except json.JSONDecodeError:
        return []

    normalized_documents = []
    for document in documents:
        if isinstance(document, dict):
            normalized_documents.append(
                Document(
                    page_content=document.get("page_content", ""),
                    metadata=document.get("metadata", {}) or {},
                )
            )
    return normalized_documents

def save_retriever_state(session_id, mode, retriever_k, chunk_size, chunk_overlap):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute('''INSERT OR REPLACE INTO retriever_state (session_id, mode,retriever_k, chunk_size, chunk_overlap) Values (?, ?, ?,?, ?)''', (session_id, mode, retriever_k, chunk_size, chunk_overlap))

    conn.commit()
    conn.close()
  
def load_retriever_state(session_id):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute('''select * from retriever_state where session_id = ?''', (session_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        return dict(row)
    else: 
        return None
    
def save_messages(session_id, msg_dict):
    conn = getConnection()
    cur = conn.cursor()

    sources_json = json.dumps(msg_dict.get("sources", []))
    keywords_json = json.dumps(msg_dict.get("keywords" , []))

   
    cur.execute(
        '''insert into chat_messages(session_id, role, content, response, timestamp, response_time, mode, sources, keywords)
           values (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            session_id,
            msg_dict.get('role'),
            msg_dict.get('content', ''),
            msg_dict.get('response', ''),
            msg_dict.get('timestamp'),
            msg_dict.get('response_time'),
            msg_dict.get('mode'),
            sources_json,
            keywords_json,
        )
    )

    conn.commit()
    conn.close()

def load_history(session_id):
    conn = getConnection()
    cur = conn.cursor()

    cur.execute(
        '''select role, content, response, timestamp, response_time, mode, sources, keywords
           from chat_messages
           where session_id = ?
           order by id asc''',
        (session_id,)
    )

    rows = cur.fetchall()
    history = []
    for row in rows:
      msg = {
          "role": row['role'],
          'content' : row['content'],
          'response' : row['response'],
          'timestamp': row['timestamp'] if 'timestamp' in row.keys() else None,
          'response_time': row['response_time'] if 'response_time' in row.keys() else None,
          'mode': row['mode'] if 'mode' in row.keys() else None,
          'sources' : json.loads(row['sources'] if row['sources'] else '[]'),
          'keywords' : json.loads(row['keywords'] if row['keywords'] else '[]')
      }
      history.append(msg)
    conn.close()
    return history


def clear_chat_history(session_id: str) -> None:
    conn = getConnection()
    cur = conn.cursor()
    cur.execute("delete from chat_messages where session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def clear_retriever_state(session_id: str) -> None:
    conn = getConnection()
    cur = conn.cursor()
    cur.execute("delete from retriever_state where session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def clear_document_state(session_id: str) -> None:
    conn = getConnection()
    cur = conn.cursor()
    cur.execute("delete from document_state where session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def save_document_state(session_id, file_name, mode, chunk_size, chunk_overlap, retrieval_k, documents):
    conn = getConnection()
    cur = conn.cursor()
    # Multi-file: lưu danh sách tên file dưới dạng JSON string
    if isinstance(file_name, (list, tuple)):
        file_name = json.dumps(list(file_name), ensure_ascii=False)
    documents_json = json.dumps(_serialize_documents(documents), ensure_ascii=False)
    cur.execute(
      """
      INSERT OR REPLACE INTO document_state
      (session_id, file_name, mode, chunk_size, chunk_overlap, retriever_k, documents_json, documents, steps_json, graph_triples_json)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """,
      (
        session_id,
        file_name,
        mode,
        chunk_size,
        chunk_overlap,
        retrieval_k,
        documents_json,
        documents_json,
        json.dumps([], ensure_ascii=False),  # default nếu caller chưa truyền steps
        json.dumps([], ensure_ascii=False),  # default nếu caller chưa truyền graph triples
      ),
    )
    conn.commit()
    conn.close()


def save_document_state_full(session_id, file_name, mode, chunk_size, chunk_overlap, retrieval_k, documents, steps, graph_triples):
    """Lưu đầy đủ document state để refresh chỉ cần load DB là render đúng UI + tiếp tục chat."""
    conn = getConnection()
    cur = conn.cursor()
    # Multi-file: lưu danh sách tên file dưới dạng JSON string
    if isinstance(file_name, (list, tuple)):
        file_name = json.dumps(list(file_name), ensure_ascii=False)
    documents_json = json.dumps(_serialize_documents(documents), ensure_ascii=False)
    steps_json = json.dumps(steps or [], ensure_ascii=False)
    graph_triples_json = json.dumps(graph_triples or [], ensure_ascii=False)
    cur.execute(
      """
      INSERT OR REPLACE INTO document_state
      (session_id, file_name, mode, chunk_size, chunk_overlap, retriever_k, documents_json, documents, steps_json, graph_triples_json)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """,
      (session_id, file_name, mode, chunk_size, chunk_overlap, retrieval_k, documents_json, documents_json, steps_json, graph_triples_json),
    )
    conn.commit()
    conn.close()

def load_document_state(session_id):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM document_state WHERE session_id = ?", (session_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None

    document_row = dict(row)
    # file_name có thể là JSON string (multi-file) hoặc string (single-file)
    try:
        if isinstance(document_row.get("file_name"), str) and document_row["file_name"].strip().startswith("["):
            document_row["file_name"] = json.loads(document_row["file_name"])
    except Exception:
        pass
    documents_json = document_row.get("documents_json") or document_row.get("documents")
    document_row["documents"] = _deserialize_documents(documents_json)
   
    try:
        document_row["steps"] = json.loads(document_row.get("steps_json") or "[]")
    except json.JSONDecodeError:
        document_row["steps"] = []
    try:
        document_row["graph_triples"] = json.loads(document_row.get("graph_triples_json") or "[]")
    except json.JSONDecodeError:
        document_row["graph_triples"] = []
    return document_row