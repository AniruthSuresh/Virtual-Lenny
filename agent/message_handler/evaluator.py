"""
RAG Quality Evaluator

Calculates quality scores without hardcoded keywords:
1. Retrieval Quality - Based on actual similarity scores from Qdrant
2. Groundedness - Token overlap with retrieved context
3. Coherence - Response completeness and structure
"""

import re
from typing import List, Dict, Any

class RAGEvaluator:
    """Evaluate RAG response quality"""
    
    def __init__(self):
        pass
    
    def calculate_retrieval_score(self, search_results: List[Any]) -> Dict[str, float]:
        """
        Calculate retrieval quality based on similarity scores.
        
        Returns:
            {
                "avg_score": float (0-1),
                "top_score": float (0-1),
                "score_variance": float (0-1),
                "source_diversity": float (0-1)
            }
        """
        if not search_results:
            return {
                "avg_score": 0.0,
                "top_score": 0.0,
                "score_variance": 0.0,
                "source_diversity": 0.0
            }
        
        # Extract scores
        scores = [r.score for r in search_results if hasattr(r, 'score')]
        
        # Calculate metrics
        avg_score = sum(scores) / len(scores) if scores else 0.0
        top_score = max(scores) if scores else 0.0
        
        # Score variance (lower is better - means consistent relevance)
        if len(scores) > 1:
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            # Normalize: low variance (0.0) = good (1.0), high variance (0.1) = bad (0.0)
            score_variance = max(0, 1 - (variance * 10))
        else:
            score_variance = 1.0
        
        # Source diversity (LinkedIn vs YouTube mix)
        sources = [r.payload.get('source', '') for r in search_results]
        unique_sources = len(set(sources))
        source_diversity = min(unique_sources / 2.0, 1.0)  # Max 2 sources
        
        return {
            "avg_score": round(avg_score, 3),
            "top_score": round(top_score, 3),
            "score_variance": round(score_variance, 3),
            "source_diversity": round(source_diversity, 3)
        }
    
    def calculate_groundedness_score(
        self, 
        response: str, 
        context_chunks: List[str]
    ) -> float:
        """
        Calculate groundedness: how much of response comes from context.
        
        Uses n-gram overlap (1-grams, 2-grams, 3-grams).
        """
        if not response or not context_chunks:
            return 0.0
        
        response_lower = response.lower()
        context_lower = " ".join(context_chunks).lower()
        
        # Extract words (4+ chars for meaningful overlap)
        response_words = set(
            word for word in re.findall(r'\b\w+\b', response_lower)
            if len(word) >= 4
        )
        context_words = set(
            word for word in re.findall(r'\b\w+\b', context_lower)
            if len(word) >= 4
        )
        
        if not response_words:
            return 0.0
        
        # 1-gram overlap
        unigram_overlap = len(response_words & context_words) / len(response_words)
        
        # 2-gram overlap (more stringent)
        response_bigrams = self._get_ngrams(response_lower, n=2)
        context_bigrams = self._get_ngrams(context_lower, n=2)
        
        if response_bigrams:
            bigram_overlap = len(response_bigrams & context_bigrams) / len(response_bigrams)
        else:
            bigram_overlap = 0.0
        
        # Weighted combination (unigrams 60%, bigrams 40%)
        groundedness = (0.6 * unigram_overlap) + (0.4 * bigram_overlap)
        
        return round(groundedness, 3)
    
    def _get_ngrams(self, text: str, n: int) -> set:
        """Extract n-grams from text"""
        words = re.findall(r'\b\w+\b', text)
        if len(words) < n:
            return set()
        
        ngrams = set()
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            if len(ngram.replace(" ", "")) >= n * 3:  # Filter short ngrams
                ngrams.add(ngram)
        
        return ngrams
    
    def calculate_coherence_score(self, response: str) -> float:
        """
        Calculate response coherence based on structure.
        
        Checks:
        - Length (not too short, not too long)
        - Sentence structure (has multiple sentences)
        - Completeness (doesn't end abruptly)
        """
        if not response:
            return 0.0
        
        score = 0.0
        
        # Length check (150-800 chars is ideal)
        length = len(response)
        if 150 <= length <= 800:
            score += 0.4
        elif 100 <= length < 150 or 800 < length <= 1000:
            score += 0.2
        
        # Sentence structure (multiple sentences is good)
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) >= 3:
            score += 0.3
        elif len(sentences) >= 2:
            score += 0.2
        
        # Completeness (ends with punctuation)
        if response.rstrip().endswith(('.', '!', '?')):
            score += 0.3
        
        return round(min(score, 1.0), 3)
    
    def calculate_source_attribution_score(
        self,
        response: str,
        search_results: List[Any]
    ) -> float:
        """
        Check if response references concepts from retrieved sources.
        
        Looks for evidence that the response used the context.
        """
        if not response or not search_results:
            return 0.0
        
        response_lower = response.lower()
        
        # Count how many sources contributed content
        sources_used = 0
        
        for result in search_results[:3]:  # Check top 3 chunks
            chunk_content = result.payload.get('content', '').lower()
            
            # Extract key phrases (3+ word sequences)
            chunk_phrases = self._get_ngrams(chunk_content, n=3)
            
            # Check if any phrases appear in response
            for phrase in chunk_phrases:
                if phrase in response_lower:
                    sources_used += 1
                    break  # Count this source once
        
        # Normalize by number of results checked
        attribution_score = sources_used / min(3, len(search_results))
        
        return round(attribution_score, 3)
    
    def calculate_rag_score(
        self,
        retrieval_metrics: Dict[str, float],
        groundedness: float,
        coherence: float,
        source_attribution: float
    ) -> Dict[str, Any]:
        """
        Calculate overall RAG score.
        
        Weighted combination:
        - 40% Retrieval quality
        - 30% Groundedness
        - 20% Coherence
        - 10% Source attribution
        
        Returns:
            {
                "overall": float (0-100),
                "breakdown": {...},
                "grade": str ("A", "B", "C", "D", "F")
            }
        """
        # Use average of retrieval metrics
        retrieval_score = (
            retrieval_metrics["avg_score"] * 0.5 +
            retrieval_metrics["top_score"] * 0.3 +
            retrieval_metrics["score_variance"] * 0.1 +
            retrieval_metrics["source_diversity"] * 0.1
        )
        
        # Weighted combination
        overall = (
            0.40 * retrieval_score +
            0.30 * groundedness +
            0.20 * coherence +
            0.10 * source_attribution
        )
        
        # Convert to 0-100 scale
        overall_pct = overall * 100
        
        # Assign grade
        if overall_pct >= 80:
            grade = "A"
        elif overall_pct >= 70:
            grade = "B"
        elif overall_pct >= 60:
            grade = "C"
        elif overall_pct >= 50:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "overall": round(overall_pct, 1),
            "breakdown": {
                "retrieval": round(retrieval_score * 100, 1),
                "groundedness": round(groundedness * 100, 1),
                "coherence": round(coherence * 100, 1),
                "attribution": round(source_attribution * 100, 1)
            },
            "grade": grade,
            "details": {
                "avg_similarity": retrieval_metrics["avg_score"],
                "top_similarity": retrieval_metrics["top_score"],
                "source_diversity": retrieval_metrics["source_diversity"]
            }
        }