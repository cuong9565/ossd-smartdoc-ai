# Function: Gán index của mỗi trang cho từng chunk
# Param: documents là 1 danh sách các chunk trong documents
# Ví dụ:
#   + Một page_num có nhiều chunk [chunk1, chunk2, chunk3]
#   + Đánh dấu chunk1 có index 1, chunk2 có index 2,...
# Return về document đã thêm thông tin 'chunk_index' cho mỗi chunk.metadata
# #
def assign_chunk_index_metadata(documents: list) -> list:
    # Biên page_counters đếm một trang đã xuất hiện bao nhiêu lần
    page_counters: dict = {}

    # Duyệt qua từng chunk trong documents
    for chunk in documents:
        page_number = chunk.metadata.get('page', 0) # Lấy số trang của chunk đó
        page_counters[page_number] = page_counters.get(page_number, 0) + 1 # Đánh dấu page_number có số lượng tăng thêm 1
        chunk.metadata['chunk_index'] = page_counters[page_number] # Đánh dấu index cho chunk đó
    return documents