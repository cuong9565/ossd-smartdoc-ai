def filter_documents(documents, src=None, file_type=None, upload_date=None):
  filtered = []
  for doc in documents:
    if src and doc.metadata.get("source") != src:
      continue
    if file_type and doc.metadata.get("file_type") != file_type:
      continue
    if upload_date and doc.metadata.get("upload_date") != upload_date:
      continue
    filtered.append(doc)
  return filtered