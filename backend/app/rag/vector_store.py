"""
PHASE 1.5: RAG (Retrieval-Augmented Generation)
Vector database integration for similar crash search with Siemens embeddings
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import openai

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Vector database for crash embeddings"""
    
    def __init__(self):
        self.db_type = settings.VECTOR_DB_TYPE
        self.client = None
        self.collection = None
        
        # Initialize embedding client for Siemens
        self.embedding_provider = getattr(settings, 'EMBEDDING_PROVIDER', 'openai')
        self.embedding_client = None
        
        if self.embedding_provider == "siemens":
            # Configure OpenAI client for Siemens embeddings
            self.embedding_client = openai.OpenAI(
                api_key=settings.SIEMENS_API_KEY,
                base_url=settings.EMBEDDING_BASE_URL
            )
            logger.info(f"Initialized Siemens embedding client with model: {settings.EMBEDDING_MODEL}")
        
        if self.db_type == "chroma":
            self._init_chroma()
        elif self.db_type == "pinecone":
            self._init_pinecone()
        else:
            logger.warning(f"Unknown vector DB type: {self.db_type}")
    
    def _init_chroma(self):
        """Initialize ChromaDB"""
        try:
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PATH,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="crash_dumps",
                metadata={"description": "Crash dump embeddings for similarity search"}
            )
            
            collection_count = self.collection.count() if self.collection else 0
            logger.info(f"ChromaDB initialized: {collection_count} embeddings")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _init_pinecone(self):
        """Initialize Pinecone - Phase 1.5"""
        # TODO: Implement Pinecone integration
        raise NotImplementedError("Pinecone integration coming soon")
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding using configured provider
        Returns None to use Chroma's default embedding
        """
        try:
            if self.embedding_provider == "siemens" and self.embedding_client:
                response = self.embedding_client.embeddings.create(
                    model=settings.EMBEDDING_MODEL,
                    input=text
                )
                embedding = response.data[0].embedding
                logger.debug(f"Generated Siemens embedding with {len(embedding)} dimensions")
                return embedding
            else:
                # Use Chroma's default embedding
                return None
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}, using Chroma default")
            return None
    
    def add_crash_embedding(
        self,
        crash_id: str,
        crash_data: Dict[str, Any],
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Add crash embedding to vector store
        
        Args:
            crash_id: UUID of crash analysis
            crash_data: Crash metadata
            embedding: Pre-computed embedding (if None, will generate)
            
        Returns:
            Embedding ID
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return ""
        
        try:
            # Generate text representation for embedding
            text = self._crash_to_text(crash_data)
            
            # Generate embedding if using Siemens
            if embedding is None and self.embedding_provider == "siemens":
                embedding = self._generate_embedding(text)
            
            # Metadata for filtering
            metadata = {
                "crash_id": crash_id,
                "exception_code": crash_data.get("exception_code", ""),
                "module": crash_data.get("faulting_module", ""),
                "platform": crash_data.get("platform", ""),
                "timestamp": datetime.utcnow().isoformat(),
                "has_solution": bool(crash_data.get("solutions"))
            }
            
            # Add to collection
            if self.db_type == "chroma":
                # Chroma will auto-generate embedding if not provided
                if embedding:
                    self.collection.add(
                        ids=[crash_id],
                        embeddings=[embedding],
                        documents=[text],
                        metadatas=[metadata]
                    )
                else:
                    self.collection.add(
                        ids=[crash_id],
                        documents=[text],
                        metadatas=[metadata]
                    )
            
            logger.info(f"Added embedding for crash {crash_id}")
            return crash_id
            
        except Exception as e:
            logger.error(f"Failed to add crash embedding: {e}")
            raise
    
    def find_similar_crashes(
        self,
        crash_data: Dict[str, Any],
        limit: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find similar crashes using vector similarity
        
        Args:
            crash_data: Crash to search for
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of similar crashes with metadata
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return []
        
        try:
            # Generate query text
            query_text = self._crash_to_text(crash_data)
            
            # Generate query embedding if using Siemens
            query_embedding = None
            if self.embedding_provider == "siemens":
                query_embedding = self._generate_embedding(query_text)
            
            if self.db_type == "chroma":
                # Use embedding if available, otherwise use text
                if query_embedding:
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=limit,
                        include=["metadatas", "distances", "documents"]
                    )
                else:
                    results = self.collection.query(
                        query_texts=[query_text],
                        n_results=limit,
                        include=["metadatas", "distances", "documents"]
                    )
                
                # Format results
                similar_crashes = []
                for i, crash_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    similarity = 1 - distance  # Convert distance to similarity
                    
                    if similarity >= min_similarity:
                        similar_crashes.append({
                            "crash_id": crash_id,
                            "similarity": similarity,
                            "metadata": results["metadatas"][0][i],
                            "snippet": results["documents"][0][i][:200]
                        })
                
                logger.info(f"Found {len(similar_crashes)} similar crashes")
                return similar_crashes
            
            return []
            
        except Exception as e:
            logger.error(f"Similar crash search failed: {e}")
            return []
    
    def _crash_to_text(self, crash_data: Dict[str, Any]) -> str:
        """
        Convert crash data to text for embedding
        Focus on key identifying features
        """
        parts = []
        
        # Exception information
        if crash_data.get("exception_code"):
            parts.append(f"Exception: {crash_data['exception_code']}")
        
        if crash_data.get("exception_message"):
            parts.append(f"Message: {crash_data['exception_message']}")
        
        # Module information
        if crash_data.get("faulting_module"):
            parts.append(f"Module: {crash_data['faulting_module']}")
        
        # Stack trace (top frames are most important)
        stack = crash_data.get("stack_trace", [])
        if stack:
            parts.append("Stack:")
            for frame in stack[:10]:  # Top 10 frames
                module = frame.get("module", "")
                function = frame.get("function", "")
                if module and function:
                    parts.append(f"  {module}!{function}")
        
        # Platform
        if crash_data.get("platform"):
            parts.append(f"Platform: {crash_data['platform']}")
        
        # Root cause (if analyzed)
        if crash_data.get("root_cause"):
            parts.append(f"Root cause: {crash_data['root_cause']}")
        
        return "\n".join(parts)
    
    def delete_crash(self, crash_id: str):
        """Delete crash from vector store"""
        try:
            if self.db_type == "chroma":
                self.collection.delete(ids=[crash_id])
            
            logger.info(f"Deleted embedding for crash {crash_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete crash embedding: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if self.db_type == "chroma":
            return {
                "total_crashes": self.collection.count(),
                "db_type": self.db_type,
                "collection_name": self.collection.name,
                "embedding_provider": self.embedding_provider,
                "embedding_model": settings.EMBEDDING_MODEL
            }
        
        return {}
    
    def find_similar_crashes_with_reranking(
        self,
        crash_data: Dict[str, Any],
        initial_limit: int = None,
        final_limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar crashes with reranking for improved accuracy
        
        Args:
            crash_data: Crash to search for
            initial_limit: Number of initial candidates (default from config)
            final_limit: Number of final results (default from config)
            
        Returns:
            List of reranked similar crashes
        """
        if not settings.ENABLE_RERANKING:
            # Reranking disabled, use standard search
            return self.find_similar_crashes(crash_data, limit=final_limit or 5)
        
        # Use config defaults if not specified
        initial_limit = initial_limit or settings.RERANKING_INITIAL_LIMIT
        final_limit = final_limit or settings.RERANKING_FINAL_LIMIT
        
        try:
            # Step 1: Get initial candidates with lower similarity threshold
            logger.info(f"Fetching {initial_limit} initial candidates for reranking")
            candidates = self.find_similar_crashes(
                crash_data,
                limit=initial_limit,
                min_similarity=0.5  # Lower threshold for initial retrieval
            )
            
            if not candidates:
                logger.info("No candidates found for reranking")
                return []
            
            if len(candidates) <= final_limit:
                # Not enough candidates to rerank
                logger.info(f"Only {len(candidates)} candidates, skipping reranking")
                return candidates
            
            # Step 2: Rerank using Siemens reranker
            logger.info(f"Reranking {len(candidates)} candidates")
            query_text = self._crash_to_text(crash_data)
            
            # Prepare documents for reranking
            doc_texts = [c["snippet"] for c in candidates]
            
            # Call reranker API (using Siemens)
            if self.embedding_client:
                try:
                    # Note: Actual reranking API might differ, this is a placeholder
                    # Siemens might use a different endpoint for reranking
                    reranked_scores = self._rerank_documents(query_text, doc_texts)
                    
                    # Combine candidates with reranked scores
                    for i, candidate in enumerate(candidates):
                        candidate["reranked_score"] = reranked_scores[i]
                    
                    # Sort by reranked score
                    candidates.sort(key=lambda x: x.get("reranked_score", 0), reverse=True)
                    
                    logger.info(f"Reranking complete, returning top {final_limit}")
                    return candidates[:final_limit]
                    
                except Exception as rerank_error:
                    logger.warning(f"Reranking failed: {rerank_error}, using original order")
                    return candidates[:final_limit]
            
            # Fallback to original order if no reranker client
            return candidates[:final_limit]
            
        except Exception as e:
            logger.error(f"Reranking search failed: {e}")
            # Fallback to standard search
            return self.find_similar_crashes(crash_data, limit=final_limit)
    
    def _rerank_documents(self, query: str, documents: List[str]) -> List[float]:
        """
        Rerank documents using Siemens reranker model
        
        Args:
            query: Query text
            documents: List of document texts
            
        Returns:
            List of reranking scores (0-1)
        """
        try:
            # Note: This is a placeholder implementation
            # The actual Siemens reranking API might use a different endpoint
            # You may need to adjust this based on Siemens documentation
            
            # For now, we'll use a simple scoring based on embeddings
            query_embedding = self._generate_embedding(query)
            doc_embeddings = [self._generate_embedding(doc) for doc in documents]
            
            if query_embedding and all(doc_embeddings):
                # Calculate cosine similarity
                import numpy as np
                
                query_vec = np.array(query_embedding)
                scores = []
                
                for doc_emb in doc_embeddings:
                    doc_vec = np.array(doc_emb)
                    # Cosine similarity
                    similarity = np.dot(query_vec, doc_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
                    )
                    scores.append(float(similarity))
                
                return scores
            
            # Fallback: return original order
            return [1.0 - (i * 0.01) for i in range(len(documents))]
            
        except Exception as e:
            logger.error(f"Reranking calculation failed: {e}")
            # Return uniform scores
            return [0.5] * len(documents)


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create vector store instance"""
    global _vector_store
    
    if _vector_store is None:
        _vector_store = VectorStore()
    
    return _vector_store
