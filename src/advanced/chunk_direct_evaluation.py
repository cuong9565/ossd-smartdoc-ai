import time
import pandas as pd
import streamlit as st
import numpy as np
import re
from typing import List, Dict, Any, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PDFPlumberLoader, Docx2txtLoader
from ..core.metadata import assign_chunk_index_metadata, add_document_metadata
import tempfile
import os

# NLP libraries for intrinsic evaluation
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    st.warning("⚠️ NLTK chưa được cài đặt. Vui lòng chạy: pip install nltk")

# Download NLTK data if needed
if NLTK_AVAILABLE:
    try:
        nltk.data.find('tokenizers/punkt_tab')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        try:
            nltk.download('punkt_tab', quiet=True)
            nltk.download('punkt', quiet=True)  # Fallback for older versions
            nltk.download('stopwords', quiet=True)
        except:
            pass


def evaluate_chunks_directly(
    uploaded_files: List[Any],
    chunk_configs: List[Dict[str, int]]
) -> Dict[str, Any]:
    """
    Đánh giá chất lượng chunks trực tiếp bằng intrinsic metrics
    
    Args:
        uploaded_files: Danh sách file đã upload
        chunk_configs: Danh sách các cấu hình chunking
    
    Returns:
        Dict chứa kết quả đánh giá chi tiết
    """
    
    results = {}
    
    # Load và chuẩn bị documents
    all_docs = []
    full_text = ""
    
    for uploaded_file in uploaded_files:
        suffix = ".pdf" if uploaded_file.type == 'application/pdf' else '.docx'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = tmp.name
        
        try:
            _, docs = load_file(temp_path, suffix)
            all_docs.extend(docs)
            full_text += " ".join([doc.page_content for doc in docs])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    # Đánh giá từng cấu hình
    for i, config in enumerate(chunk_configs):
        config_name = f"Config_{i+1} (size={config['chunk_size']}, overlap={config['chunk_overlap']})"
        
        st.info(f"Đang đánh giá chất lượng {config_name}...")
        
        # Chunk với cấu hình hiện tại
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config['chunk_size'],
            chunk_overlap=config['chunk_overlap']
        )
        chunks = splitter.split_documents(all_docs)
        chunks = assign_chunk_index_metadata(chunks)
        chunks = add_document_metadata(chunks, src_name="evaluation", file_type="pdf")
        
        # Đánh giá chất lượng chunks
        quality_metrics = evaluate_chunk_quality_direct(chunks, full_text)
        
        # Tính toán các metrics bổ sung
        additional_metrics = calculate_additional_metrics(chunks, full_text, config)
        
        # Tính toán các metrics
        results[config_name] = {
            'chunk_size': config['chunk_size'],
            'chunk_overlap': config['chunk_overlap'],
            'num_chunks': len(chunks),
            'quality_metrics': quality_metrics,
            'additional_metrics': additional_metrics,
            'chunks': chunks
        }
    
    return results


def load_file(temp_path: str, suffix: str) -> tuple:
    """Load file và trả về documents"""
    start_time = time.time()
    if suffix == ".pdf":
        loader = PDFPlumberLoader(temp_path)
    else:
        loader = Docx2txtLoader(temp_path)
    docs = loader.load()
    elapsed = round(time.time() - start_time, 2)
    return elapsed, docs


def evaluate_chunk_quality_direct(chunks: List[Any], full_text: str) -> Dict[str, float]:
    """
    Đánh giá chất lượng chunks bằng các intrinsic metrics
    """
    
    chunk_texts = [chunk.page_content for chunk in chunks]
    
    # 1. Basic chunk metrics
    chunk_lengths = [len(text) for text in chunk_texts]
    basic_metrics = {
        'avg_chunk_length': np.mean(chunk_lengths),
        'std_chunk_length': np.std(chunk_lengths),
        'min_chunk_length': np.min(chunk_lengths),
        'max_chunk_length': np.max(chunk_lengths),
        'chunk_length_variance': np.var(chunk_lengths),
        'chunk_length_range': np.max(chunk_lengths) - np.min(chunk_lengths)
    }
    
    # 2. Sentence-level metrics
    sentence_metrics = calculate_sentence_metrics(chunk_texts)
    
    # 3. Semantic coherence metrics
    coherence_metrics = calculate_coherence_metrics(chunk_texts)
    
    # 4. Boundary quality metrics
    boundary_metrics = calculate_boundary_quality(chunk_texts, full_text)
    
    # 5. Content coverage metrics
    coverage_metrics = calculate_content_coverage(chunk_texts, full_text)
    
    # 6. Structural metrics
    structural_metrics = calculate_structural_metrics(chunk_texts)
    
    # Combine all metrics
    all_metrics = {}
    all_metrics.update(basic_metrics)
    all_metrics.update(sentence_metrics)
    all_metrics.update(coherence_metrics)
    all_metrics.update(boundary_metrics)
    all_metrics.update(coverage_metrics)
    all_metrics.update(structural_metrics)
    
    return all_metrics


def calculate_sentence_metrics(chunk_texts: List[str]) -> Dict[str, float]:
    """
    Tính toán các metrics liên quan đến câu trong chunks
    """
    
    if not NLTK_AVAILABLE:
        return {
            'avg_sentences_per_chunk': 0,
            'sentence_completeness': 0,
            'sentence_boundary_violations': 0
        }
    
    total_sentences = 0
    incomplete_sentences = 0
    sentence_boundary_violations = 0
    
    for text in chunk_texts:
        sentences = sent_tokenize(text)
        total_sentences += len(sentences)
        
        # Check for incomplete sentences (very short sentences)
        for sentence in sentences:
            if len(sentence.strip()) < 10:  # Very short sentences might be incomplete
                incomplete_sentences += 1
        
        # Check sentence boundary violations (sentences cut in the middle)
        if text.strip() and not text.strip().endswith(('.', '!', '?', '"', "'")):
            if len(text.strip()) > 50:  # Only count longer texts as violations
                sentence_boundary_violations += 1
    
    avg_sentences = total_sentences / len(chunk_texts) if chunk_texts else 0
    completeness = 1 - (incomplete_sentences / total_sentences) if total_sentences > 0 else 0
    
    return {
        'avg_sentences_per_chunk': avg_sentences,
        'sentence_completeness': completeness,
        'sentence_boundary_violations': sentence_boundary_violations,
        'total_sentences': total_sentences
    }


def calculate_coherence_metrics(chunk_texts: List[str]) -> Dict[str, float]:
    """
    Tính toán các metrics đo lường sự liên kết ngữ nghĩa
    """
    
    coherence_scores = []
    overlap_scores = []
    
    for i, text in enumerate(chunk_texts):
        # 1. Word overlap with adjacent chunks (local coherence)
        words_current = set(re.findall(r'\b\w+\b', text.lower()))
        
        if i > 0:
            words_prev = set(re.findall(r'\b\w+\b', chunk_texts[i-1].lower()))
            overlap = len(words_current & words_prev) / len(words_current | words_prev) if len(words_current | words_prev) > 0 else 0
            overlap_scores.append(overlap)
        
        # 2. Internal coherence (word repetition within chunk)
        if len(words_current) > 0:
            word_freq = {}
            for word in words_current:
                word_freq[word] = text.lower().count(word)
            
            # Coherence based on word repetition
            if len(word_freq) > 0:
                avg_freq = np.mean(list(word_freq.values()))
                coherence_scores.append(min(avg_freq / len(words_current), 1.0))
    
    return {
        'avg_local_coherence': np.mean(overlap_scores) if overlap_scores else 0,
        'avg_internal_coherence': np.mean(coherence_scores) if coherence_scores else 0,
        'coherence_stability': 1 - np.std(overlap_scores) if overlap_scores else 0
    }


def calculate_boundary_quality(chunk_texts: List[str], full_text: str) -> Dict[str, float]:
    """
    Tính toán chất lượng của chunk boundaries
    """
    
    boundary_violations = 0
    natural_breaks = 0
    total_boundaries = len(chunk_texts) - 1
    
    # Find natural break points in original text
    natural_break_positions = []
    for match in re.finditer(r'[.!?]\s+\n|\n\n|\.\s+[A-Z]', full_text):
        natural_break_positions.append(match.start())
    
    # Check if chunk boundaries align with natural breaks
    reconstructed_text = "".join(chunk_texts)
    current_pos = 0
    
    for i in range(len(chunk_texts) - 1):
        current_pos += len(chunk_texts[i])
        
        # Check if boundary is near a natural break
        is_natural_break = any(abs(current_pos - pos) < 50 for pos in natural_break_positions)
        if is_natural_break:
            natural_breaks += 1
        else:
            boundary_violations += 1
    
    boundary_quality = natural_breaks / total_boundaries if total_boundaries > 0 else 0
    
    return {
        'boundary_quality': boundary_quality,
        'natural_breaks': natural_breaks,
        'boundary_violations': boundary_violations,
        'boundary_alignment_rate': boundary_quality
    }


def calculate_content_coverage(chunk_texts: List[str], full_text: str) -> Dict[str, float]:
    """
    Tính toán độ bao phủ nội dung
    """
    
    chunked_text = "".join(chunk_texts)
    
    # Character-level coverage
    char_coverage = len(chunked_text) / len(full_text) if len(full_text) > 0 else 0
    
    # Word-level coverage
    original_words = set(re.findall(r'\b\w+\b', full_text.lower()))
    chunked_words = set(re.findall(r'\b\w+\b', chunked_text.lower()))
    
    word_coverage = len(chunked_words & original_words) / len(original_words) if len(original_words) > 0 else 0
    
    # Unique content ratio (to detect duplication)
    total_chunk_chars = sum(len(text) for text in chunk_texts)
    unique_chars = len(set(chunked_text))
    duplication_ratio = 1 - (unique_chars / total_chunk_chars) if total_chunk_chars > 0 else 0
    
    return {
        'char_coverage': char_coverage,
        'word_coverage': word_coverage,
        'duplication_ratio': duplication_ratio,
        'content_preservation': word_coverage
    }


def calculate_structural_metrics(chunk_texts: List[str]) -> Dict[str, float]:
    """
    Tính toán các cấu trúc metrics
    """
    
    # Paragraph structure
    paragraph_counts = []
    for text in chunk_texts:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_counts.append(len(paragraphs))
    
    avg_paragraphs = np.mean(paragraph_counts) if paragraph_counts else 0
    
    # Punctuation balance
    total_punctuation = 0
    for text in chunk_texts:
        total_punctuation += len(re.findall(r'[.!?,:;]', text))
    
    avg_punctuation = total_punctuation / len(chunk_texts) if chunk_texts else 0
    
    # Length distribution quality (chunks should have similar lengths)
    lengths = [len(text) for text in chunk_texts]
    length_balance = 1 - (np.std(lengths) / np.mean(lengths)) if np.mean(lengths) > 0 else 0
    
    return {
        'avg_paragraphs_per_chunk': avg_paragraphs,
        'avg_punctuation_per_chunk': avg_punctuation,
        'length_balance': length_balance,
        'structural_consistency': length_balance
    }


def calculate_additional_metrics(chunks: List[Any], full_text: str, config: Dict[str, int]) -> Dict[str, float]:
    """
    Tính toán các metrics bổ sung
    """
    
    chunk_texts = [chunk.page_content for chunk in chunks]
    
    # Efficiency metrics
    total_chars = sum(len(text) for text in chunk_texts)
    processing_efficiency = len(chunk_texts) / (total_chars / 1000) if total_chars > 0 else 0  # chunks per 1k chars
    
    # Overlap efficiency
    overlap_ratio = config['chunk_overlap'] / config['chunk_size'] if config['chunk_size'] > 0 else 0
    
    # Information density
    total_words = sum(len(re.findall(r'\b\w+\b', text)) for text in chunk_texts)
    information_density = total_words / total_chars if total_chars > 0 else 0
    
    return {
        'processing_efficiency': processing_efficiency,
        'overlap_ratio': overlap_ratio,
        'information_density': information_density,
        'chunks_per_kb': processing_efficiency
    }


def get_direct_chunk_configurations() -> List[Dict[str, int]]:
    """
    Trả về danh sách các cấu hình chunking theo yêu cầu của user
    """
    chunk_sizes = [500, 1000, 1500, 2000]
    chunk_overlaps = [50, 100, 200]
    
    configs = []
    for size in chunk_sizes:
        for overlap in chunk_overlaps:
            configs.append({
                'chunk_size': size,
                'chunk_overlap': overlap,
                'retrieval_k': 5  # Not used in direct evaluation
            })
    
    return configs


def render_chunk_direct_evaluation_section():
    """
    Render giao diện đánh giá chunks trực tiếp
    """
    
    if not st.session_state.get('uploaded_files') and not st.session_state.get('documents'):
        st.warning("⚠️ Vui lòng upload tài liệu trước khi chạy đánh giá chunking.")
        return
    
    st.divider()
    st.subheader("🔍 Đánh giá Chất lượng Chunks Trực tiếp")
    st.caption("Phân tích chất lượng intrinsic của các chunks mà không cần câu hỏi retrieval")
    
    # Configuration info
    st.markdown("### 📋 Cấu hình đánh giá trực tiếp")
    st.info(f"Sẽ đánh giá **12 cấu hình** với:")
    st.markdown("- **Chunk sizes**: 500, 1000, 1500, 2000 ký tự")
    st.markdown("- **Chunk overlaps**: 50, 100, 200 ký tự") 
    st.markdown("- **Metrics**: Intrinsic chunk quality (coherence, completeness, boundaries)")
    
    # Metrics explanation
    with st.expander("📖 Các metrics được đánh giá"):
        st.markdown("**Basic Metrics:**")
        st.markdown("- Độ dài trung bình, độ lệch chuẩn, phạm vi độ dài")
        
        st.markdown("**Sentence Metrics:**")
        st.markdown("- Số câu trung bình, độ hoàn thiện câu, vi phạm biên câu")
        
        st.markdown("**Coherence Metrics:**")
        st.markdown("- Sự liên kết local, coherence nội tại, độ ổn định")
        
        st.markdown("**Boundary Quality:**")
        st.markdown("- Chất lượng biên, breaks tự nhiên, vi phạm biên")
        
        st.markdown("**Content Coverage:**")
        st.markdown("- Độ bao phủ ký tự/từ, tỷ lệ trùng lặp")
        
        st.markdown("**Structural Metrics:**")
        st.markdown("- Cấu trúc đoạn, cân bằng độ dài, tính nhất quán")
    
    # Run evaluation button
    if st.button("🔍 Chạy đánh giá chunks trực tiếp", type="primary", use_container_width=True):
        uploaded_files = st.session_state.get('uploaded_files', [])
        if not uploaded_files:
            st.error("⚠️ Cần upload file để chạy đánh giá chunking.")
            return
        
        configs = get_direct_chunk_configurations()
        
        with st.spinner(f"Đang đánh giá chất lượng {len(configs)} cấu hình chunking..."):
            try:
                results = evaluate_chunks_directly(
                    uploaded_files,
                    configs
                )
                
                # Store results in session state
                st.session_state.chunk_direct_results = results
                
                st.success("✅ Đánh giá chất lượng chunks hoàn tất!")
                
                # Display results
                display_direct_evaluation_results(results)
                
            except Exception as e:
                st.error(f"❌ Lỗi khi đánh giá: {str(e)}")
                st.exception(e)
    
    # Display previous results if available
    if 'chunk_direct_results' in st.session_state:
        st.divider()
        st.subheader("📈 Kết quả đánh giá chất lượng chunks gần nhất")
        display_direct_evaluation_results(st.session_state.chunk_direct_results)


def display_direct_evaluation_results(results: Dict[str, Any]):
    """
    Hiển thị kết quả đánh giá chunks trực tiếp
    """
    
    if not results:
        return
    
    # Create comprehensive comparison table
    comparison_data = []
    for config_name, metrics in results.items():
        quality = metrics['quality_metrics']
        additional = metrics['additional_metrics']
        
        comparison_data.append({
            'Cấu hình': config_name,
            'Chunk Size': metrics['chunk_size'],
            'Overlap': metrics['chunk_overlap'],
            'Số chunks': metrics['num_chunks'],
            'Độ dài TB': round(quality.get('avg_chunk_length', 0), 1),
            'Std Độ dài': round(quality.get('std_chunk_length', 0), 1),
            'Câu/Chunk': round(quality.get('avg_sentences_per_chunk', 0), 1),
            'Hoàn thiện câu': round(quality.get('sentence_completeness', 0) * 100, 1),
            'Coherence': round(quality.get('avg_local_coherence', 0) * 100, 1),
            'Chất lượng biên': round(quality.get('boundary_quality', 0) * 100, 1),
            'Bao phủ nội dung': round(quality.get('content_preservation', 0) * 100, 1),
            'Cân bằng độ dài': round(quality.get('length_balance', 0) * 100, 1)
        })
    
    df = pd.DataFrame(comparison_data)
    
    # Display main comparison table
    st.markdown("### 📊 Bảng so sánh chất lượng chunks")
    st.dataframe(df, use_container_width=True)
    
    # Find best configurations
    st.markdown("### 🏆 Cấu hình tốt nhất theo từng metric")
    
    best_coherence = max(results.items(), key=lambda x: x[1]['quality_metrics'].get('avg_local_coherence', 0))
    best_completeness = max(results.items(), key=lambda x: x[1]['quality_metrics'].get('sentence_completeness', 0))
    best_boundary = max(results.items(), key=lambda x: x[1]['quality_metrics'].get('boundary_quality', 0))
    best_coverage = max(results.items(), key=lambda x: x[1]['quality_metrics'].get('content_preservation', 0))
    best_balance = max(results.items(), key=lambda x: x[1]['quality_metrics'].get('length_balance', 0))
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Coherence cao nhất",
            best_coherence[0].split('(')[0].strip(),
            f"{best_coherence[1]['quality_metrics'].get('avg_local_coherence', 0)*100:.1f}%"
        )
    
    with col2:
        st.metric(
            "Hoàn thiện câu cao nhất",
            best_completeness[0].split('(')[0].strip(),
            f"{best_completeness[1]['quality_metrics'].get('sentence_completeness', 0)*100:.1f}%"
        )
    
    with col3:
        st.metric(
            "Chất lượng biên cao nhất",
            best_boundary[0].split('(')[0].strip(),
            f"{best_boundary[1]['quality_metrics'].get('boundary_quality', 0)*100:.1f}%"
        )
    
    with col4:
        st.metric(
            "Bao phủ nội dung cao nhất",
            best_coverage[0].split('(')[0].strip(),
            f"{best_coverage[1]['quality_metrics'].get('content_preservation', 0)*100:.1f}%"
        )
    
    with col5:
        st.metric(
            "Cân bằng độ dài cao nhất",
            best_balance[0].split('(')[0].strip(),
            f"{best_balance[1]['quality_metrics'].get('length_balance', 0)*100:.1f}%"
        )
    
    # Detailed charts
    st.markdown("### 📈 Biểu đồ so sánh chi tiết")
    
    # Chart 1: Quality Metrics Comparison
    col1, col2 = st.columns(2)
    
    with col1:
        quality_df = pd.DataFrame({
            'Cấu hình': list(results.keys()),
            'Coherence': [round(metrics['quality_metrics'].get('avg_local_coherence', 0) * 100, 1) for metrics in results.values()],
            'Hoàn thiện câu': [round(metrics['quality_metrics'].get('sentence_completeness', 0) * 100, 1) for metrics in results.values()],
            'Chất lượng biên': [round(metrics['quality_metrics'].get('boundary_quality', 0) * 100, 1) for metrics in results.values()]
        })
        st.bar_chart(quality_df.set_index('Cấu hình'), use_container_width=True)
        st.caption("Coherence, Hoàn thiện câu, Chất lượng biên")
    
    with col2:
        coverage_df = pd.DataFrame({
            'Cấu hình': list(results.keys()),
            'Bao phủ nội dung': [round(metrics['quality_metrics'].get('content_preservation', 0) * 100, 1) for metrics in results.values()],
            'Cân bằng độ dài': [round(metrics['quality_metrics'].get('length_balance', 0) * 100, 1) for metrics in results.values()],
            'Tính nhất quán': [round(metrics['quality_metrics'].get('structural_consistency', 0) * 100, 1) for metrics in results.values()]
        })
        st.bar_chart(coverage_df.set_index('Cấu hình'), use_container_width=True)
        st.caption("Bao phủ nội dung và Cân bằng cấu trúc")
    
    # Chart 2: Structural Analysis
    structural_df = pd.DataFrame({
        'Cấu hình': list(results.keys()),
        'Số chunks': [metrics['num_chunks'] for metrics in results.values()],
        'Độ dài TB': [round(metrics['quality_metrics'].get('avg_chunk_length', 0), 1) for metrics in results.values()],
        'Std Độ dài': [round(metrics['quality_metrics'].get('std_chunk_length', 0), 1) for metrics in results.values()],
        'Câu/Chunk': [round(metrics['quality_metrics'].get('avg_sentences_per_chunk', 0), 1) for metrics in results.values()]
    })
    st.bar_chart(structural_df.set_index('Cấu hình'), use_container_width=True)
    st.caption("Phân tích cấu trúc chunks")
    
    # Overall quality score
    st.markdown("### 🎯 Điểm chất lượng tổng thể")
    
    overall_scores = {}
    for config_name, metrics in results.items():
        quality = metrics['quality_metrics']
        
        # Calculate weighted overall score
        weights = {
            'coherence': 0.25,
            'completeness': 0.20,
            'boundary': 0.20,
            'coverage': 0.15,
            'balance': 0.10,
            'structure': 0.10
        }
        
        score = (
            quality.get('avg_local_coherence', 0) * weights['coherence'] +
            quality.get('sentence_completeness', 0) * weights['completeness'] +
            quality.get('boundary_quality', 0) * weights['boundary'] +
            quality.get('content_preservation', 0) * weights['coverage'] +
            quality.get('length_balance', 0) * weights['balance'] +
            quality.get('structural_consistency', 0) * weights['structure']
        )
        
        overall_scores[config_name] = score
    
    # Sort by overall score
    sorted_configs = sorted(overall_scores.items(), key=lambda x: x[1], reverse=True)
    
    st.markdown("#### Bảng xếp hạng chất lượng tổng thể:")
    for i, (config_name, score) in enumerate(sorted_configs[:5], 1):
        st.markdown(f"**{i}.** {config_name} - **{score*100:.2f}%**")
    
    # Best overall
    best_overall = sorted_configs[0]
    st.success(f"🏆 **Cấu hình tốt nhất tổng thể**: {best_overall[0]} với điểm chất lượng {best_overall[1]*100:.2f}%")
    
    # Detailed analysis by chunk size
    st.markdown("### 🔍 Phân tích theo kích thước chunk")
    
    chunk_size_analysis = {}
    for config_name, metrics in results.items():
        size = metrics['chunk_size']
        if size not in chunk_size_analysis:
            chunk_size_analysis[size] = []
        chunk_size_analysis[size].append(metrics['quality_metrics'])
    
    for size in sorted(chunk_size_analysis.keys()):
        metrics_list = chunk_size_analysis[size]
        avg_coherence = np.mean([m.get('avg_local_coherence', 0) for m in metrics_list])
        avg_completeness = np.mean([m.get('sentence_completeness', 0) for m in metrics_list])
        avg_boundary = np.mean([m.get('boundary_quality', 0) for m in metrics_list])
        avg_coverage = np.mean([m.get('content_preservation', 0) for m in metrics_list])
        
        st.markdown(f"**Chunk Size {size}**: "
                   f"Coherence: {avg_coherence*100:.1f}%, "
                   f"Hoàn thiện: {avg_completeness*100:.1f}%, "
                   f"Biên: {avg_boundary*100:.1f}%, "
                   f"Bao phủ: {avg_coverage*100:.1f}%")
