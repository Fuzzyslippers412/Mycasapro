"""
MyCasa Pro - Semantic Search Engine
Provides vector-based semantic search for SecondBrain knowledge base.
Uses sentence transformers for embedding generation and FAISS for similarity search.
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path
import pickle
import logging
from datetime import datetime
import hashlib

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    print("[WARNING] sentence-transformers not available. Semantic search disabled.")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("[WARNING] faiss-cpu not available. Using sklearn fallback.")

logger = logging.getLogger("mycasa.semantic_search")

class SemanticSearchEngine:
    """
    Semantic search engine for SecondBrain notes and documents.
    Combines keyword search with semantic similarity for better results.
    """
    
    def __init__(self, 
                 tenant_id: str,
                 model_name: str = "all-MiniLM-L6-v2",
                 vector_dim: int = 384):
        self.tenant_id = tenant_id
        self.model_name = model_name
        self.vector_dim = vector_dim
        
        # Storage paths
        self.storage_dir = Path(f"storage/tenants/{tenant_id}/semantic_search")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Vector database
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.doc_ids: List[str] = []  # Document identifiers
        
        # Model
        self.model = None
        if EMBEDDING_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Loaded embedding model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load embedding model {model_name}: {e}")
                EMBEDDING_AVAILABLE = False
        
        # Load existing data if available
        self.load_index()
    
    def _generate_doc_id(self, content: str, metadata: Dict[str, Any]) -> str:
        """Generate unique document ID based on content and metadata"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{metadata.get('type', 'doc')}_{content_hash}_{timestamp}"
    
    def add_document(self, 
                     content: str, 
                     doc_id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a document to the semantic search index.
        
        Args:
            content: Document content to index
            doc_id: Optional document ID (auto-generated if not provided)
            metadata: Optional metadata dictionary
            
        Returns:
            Document ID
        """
        if not EMBEDDING_AVAILABLE:
            raise RuntimeError("Embedding model not available. Install sentence-transformers.")
        
        if metadata is None:
            metadata = {}
        
        # Generate document ID if not provided
        if doc_id is None:
            doc_id = self._generate_doc_id(content, metadata)
        
        # Create document entry
        doc_entry = {
            "id": doc_id,
            "content": content,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate embedding
        embedding = self.model.encode([content])[0]  # Shape: (vector_dim,)
        
        # Add to collections
        self.documents.append(doc_entry)
        self.doc_ids.append(doc_id)
        
        # Update embeddings matrix
        if self.embeddings is None:
            self.embeddings = np.array([embedding])
        else:
            self.embeddings = np.vstack([self.embeddings, embedding])
        
        logger.info(f"Added document to semantic index: {doc_id}")
        return doc_id
    
    def batch_add_documents(self, 
                           documents: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
        """
        Add multiple documents efficiently.
        
        Args:
            documents: List of (content, metadata) tuples
            
        Returns:
            List of generated document IDs
        """
        if not EMBEDDINGS_AVAILABLE:
            raise RuntimeError("Embedding model not available. Install sentence-transformers.")
        
        if not documents:
            return []
        
        # Extract contents and metadata
        contents = [doc[0] for doc in documents]
        metadatas = [doc[1] for doc in documents]
        
        # Generate embeddings for all contents at once
        embeddings_batch = self.model.encode(contents)
        
        doc_ids = []
        for i, (content, metadata) in enumerate(zip(contents, metadatas)):
            # Generate document ID
            doc_id = self._generate_doc_id(content, metadata)
            
            # Create document entry
            doc_entry = {
                "id": doc_id,
                "content": content,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to collections
            self.documents.append(doc_entry)
            self.doc_ids.append(doc_id)
            
            # Add embedding
            embedding = embeddings_batch[i]
            if self.embeddings is None:
                self.embeddings = np.array([embedding])
            else:
                self.embeddings = np.vstack([self.embeddings, embedding])
            
            doc_ids.append(doc_id)
        
        logger.info(f"Added {len(documents)} documents to semantic index")
        return doc_ids
    
    def search(self, 
               query: str, 
               top_k: int = 10,
               filters: Optional[Dict[str, Any]] = None,
               threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Perform semantic search on indexed documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            List of matching documents with similarity scores
        """
        if not EMBEDDING_AVAILABLE or self.embeddings is None or len(self.embeddings) == 0:
            logger.warning("No embeddings available for search")
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query])[0]  # Shape: (vector_dim,)
        query_embedding = query_embedding.reshape(1, -1)  # Reshape for similarity calculation
        
        # Calculate similarities
        if FAISS_AVAILABLE:
            # Use FAISS for faster similarity search
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(self.embeddings.astype('float32'))
            faiss.normalize_L2(query_embedding.astype('float32'))
            
            # Create index if needed
            index = faiss.IndexFlatIP(self.vector_dim)
            index.add(self.embeddings.astype('float32'))
            
            # Search
            scores, indices = index.search(query_embedding.astype('float32'), top_k)
            similarities = scores[0]
            doc_indices = indices[0]
        else:
            # Use sklearn cosine similarity
            similarities = cosine_similarity(query_embedding, self.embeddings)[0]
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]
            doc_indices = top_indices
            similarities = similarities[top_indices]
        
        # Prepare results
        results = []
        for i, idx in enumerate(doc_indices):
            if idx < len(self.documents) and similarities[i] >= threshold:
                doc = self.documents[idx]
                
                # Apply filters if provided
                if filters:
                    match = True
                    for key, value in filters.items():
                        if key not in doc["metadata"] or doc["metadata"][key] != value:
                            match = False
                            break
                    if not match:
                        continue
                
                results.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "similarity": float(similarities[i]),
                    "timestamp": doc["timestamp"]
                })
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        logger.info(f"Semantic search returned {len(results)} results for query: '{query[:50]}...'")
        return results[:top_k]
    
    def hybrid_search(self, 
                     query: str, 
                     keyword_results: List[Dict[str, Any]], 
                     top_k: int = 10,
                     keyword_weight: float = 0.3,
                     semantic_weight: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining keyword and semantic results.
        
        Args:
            query: Search query
            keyword_results: Results from keyword search
            top_k: Number of results to return
            keyword_weight: Weight for keyword results (0.0 to 1.0)
            semantic_weight: Weight for semantic results (0.0 to 1.0)
            
        Returns:
            Combined ranked results
        """
        # Get semantic results
        semantic_results = self.search(query, top_k=top_k)
        
        # Combine and rank results
        all_results = {}
        
        # Add keyword results with weighted scores
        for i, result in enumerate(keyword_results):
            doc_id = result.get("id", f"keyword_{i}")
            all_results[doc_id] = {
                **result,
                "combined_score": result.get("score", 1.0) * keyword_weight,
                "keyword_score": result.get("score", 1.0),
                "semantic_score": 0.0
            }
        
        # Add or update with semantic results
        for result in semantic_results:
            doc_id = result["id"]
            if doc_id in all_results:
                # Update existing result with semantic score
                all_results[doc_id]["semantic_score"] = result["similarity"]
                all_results[doc_id]["combined_score"] = (
                    all_results[doc_id]["keyword_score"] * keyword_weight +
                    result["similarity"] * semantic_weight
                )
            else:
                # New semantic-only result
                all_results[doc_id] = {
                    **result,
                    "combined_score": result["similarity"] * semantic_weight,
                    "keyword_score": 0.0,
                    "semantic_score": result["similarity"]
                }
        
        # Sort by combined score
        ranked_results = sorted(
            all_results.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        return ranked_results[:top_k]
    
    def update_document(self, 
                       doc_id: str, 
                       content: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing document in the index."""
        try:
            doc_idx = None
            for i, doc in enumerate(self.documents):
                if doc["id"] == doc_id:
                    doc_idx = i
                    break
            
            if doc_idx is None:
                return False
            
            # Update content if provided
            if content is not None:
                self.documents[doc_idx]["content"] = content
                self.documents[doc_idx]["timestamp"] = datetime.now().isoformat()
                
                # Regenerate embedding
                new_embedding = self.model.encode([content])[0]
                self.embeddings[doc_idx] = new_embedding
            
            # Update metadata if provided
            if metadata is not None:
                self.documents[doc_idx]["metadata"].update(metadata)
            
            logger.info(f"Updated document in semantic index: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """Remove a document from the index."""
        try:
            doc_idx = None
            for i, doc in enumerate(self.documents):
                if doc["id"] == doc_id:
                    doc_idx = i
                    break
            
            if doc_idx is None:
                return False
            
            # Remove from all collections
            self.documents.pop(doc_idx)
            self.doc_ids.pop(doc_idx)
            self.embeddings = np.delete(self.embeddings, doc_idx, axis=0)
            
            logger.info(f"Removed document from semantic index: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    def save_index(self):
        """Save the semantic search index to disk."""
        try:
            # Save embeddings
            embeddings_path = self.storage_dir / "embeddings.npy"
            if self.embeddings is not None:
                np.save(embeddings_path, self.embeddings)
            
            # Save documents and metadata
            docs_path = self.storage_dir / "documents.pkl"
            with open(docs_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'doc_ids': self.doc_ids
                }, f)
            
            logger.info(f"Saved semantic search index for tenant {self.tenant_id}")
        except Exception as e:
            logger.error(f"Failed to save semantic search index: {e}")
    
    def load_index(self):
        """Load the semantic search index from disk."""
        try:
            # Load embeddings
            embeddings_path = self.storage_dir / "embeddings.npy"
            if embeddings_path.exists():
                self.embeddings = np.load(embeddings_path)
            
            # Load documents and metadata
            docs_path = self.storage_dir / "documents.pkl"
            if docs_path.exists():
                with open(docs_path, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data.get('documents', [])
                    self.doc_ids = data.get('doc_ids', [])
            
            logger.info(f"Loaded semantic search index for tenant {self.tenant_id} "
                       f"({len(self.documents)} documents)")
        except Exception as e:
            logger.warning(f"Failed to load semantic search index: {e}")
            # Initialize empty structures
            self.documents = []
            self.doc_ids = []
            self.embeddings = None
    
    def clear_index(self):
        """Clear all documents from the index."""
        self.documents = []
        self.doc_ids = []
        self.embeddings = None
        
        # Remove saved files
        for file_path in self.storage_dir.glob("*"):
            file_path.unlink()
        
        logger.info("Cleared semantic search index")


# Global cache for search engines per tenant
_search_engines = {}

def get_semantic_search_engine(tenant_id: str) -> SemanticSearchEngine:
    """Get or create a semantic search engine for a tenant."""
    if tenant_id not in _search_engines:
        _search_engines[tenant_id] = SemanticSearchEngine(tenant_id)
    return _search_engines[tenant_id]


def reset_search_engine(tenant_id: str):
    """Reset the search engine for a tenant."""
    if tenant_id in _search_engines:
        del _search_engines[tenant_id]