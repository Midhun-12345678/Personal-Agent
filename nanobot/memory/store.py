"""Vector-based memory store using ChromaDB and sentence-transformers."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class UserMemoryStore:
    """Per-user semantic memory store with vector search capabilities.
    
    Uses ChromaDB for persistent vector storage and sentence-transformers
    for embedding generation. Each user gets an isolated collection.
    """

    def __init__(self, user_id: str, workspace: Path):
        """Initialize the memory store for a specific user.
        
        Args:
            user_id: Unique user identifier
            workspace: Base workspace path (chromadb stored at workspace/memory/)
        """
        self.user_id = user_id
        self.workspace = workspace
        self.collection_name = f"memory_{user_id}"
        
        # Lazy initialization
        self._client = None
        self._collection = None
        self._embedder = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of ChromaDB and embeddings model."""
        if self._initialized:
            return
            
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "Semantic memory requires 'chromadb' and 'sentence-transformers'. "
                "Install with: pip install chromadb sentence-transformers"
            ) from e
        
        # Setup ChromaDB persistent storage
        memory_dir = self.workspace / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        self._client = chromadb.PersistentClient(path=str(memory_dir))
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Load embedding model
        self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self._initialized = True
        
        logger.debug(
            "Initialized semantic memory for user '{}' at {}",
            self.user_id, memory_dir
        )

    def _embed(self, text: str) -> list[float]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        self._ensure_initialized()
        embedding = self._embedder.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    async def save(
        self,
        text: str,
        category: str = "general",
        source: str = "conversation"
    ) -> str:
        """Save a memory with embedding.
        
        Args:
            text: Memory text content
            category: Category (profile, goal, preference, task, general)
            source: Source of the memory (conversation, import, etc.)
            
        Returns:
            Memory ID
        """
        self._ensure_initialized()
        
        memory_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        embedding = self._embed(text)
        
        self._collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "user_id": self.user_id,
                "category": category,
                "timestamp": timestamp,
                "source": source,
            }]
        )
        
        logger.debug(
            "Saved memory [{}]: '{}...' (category={})",
            memory_id[:8], text[:50], category
        )
        
        return memory_id

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search for relevant memories.
        
        Args:
            query: Search query
            top_k: Maximum number of results
            
        Returns:
            List of matching memories with text, category, timestamp, score
        """
        self._ensure_initialized()
        
        if self._collection.count() == 0:
            return []
        
        query_embedding = self._embed(query)
        
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"]
        )
        
        memories = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0.0
                # Convert distance to similarity score (cosine distance -> similarity)
                score = 1.0 - distance
                
                memories.append({
                    "text": doc,
                    "category": metadata.get("category", "general"),
                    "timestamp": metadata.get("timestamp", ""),
                    "score": round(score, 4),
                })
        
        logger.debug("Memory search '{}': {} results", query[:30], len(memories))
        return memories

    async def save_profile(self, field: str, value: str) -> str:
        """Save a structured profile fact.
        
        Args:
            field: Profile field name (e.g., "profession", "name")
            value: Field value
            
        Returns:
            Memory ID
        """
        text = f"User's {field} is: {value}"
        return await self.save(text, category="profile", source="profile_update")

    async def get_profile(self) -> list[dict[str, Any]]:
        """Get all profile memories.
        
        Returns:
            List of profile memories
        """
        self._ensure_initialized()
        
        if self._collection.count() == 0:
            return []
        
        results = self._collection.get(
            where={"category": "profile"},
            include=["documents", "metadatas"]
        )
        
        profiles = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}
                profiles.append({
                    "text": doc,
                    "category": "profile",
                    "timestamp": metadata.get("timestamp", ""),
                })
        
        return profiles

    async def delete(self, memory_id: str) -> None:
        """Delete a memory by ID.
        
        Args:
            memory_id: Memory ID to delete
        """
        self._ensure_initialized()
        self._collection.delete(ids=[memory_id])
        logger.debug("Deleted memory [{}]", memory_id[:8])

    async def count(self) -> int:
        """Get total number of memories for this user.
        
        Returns:
            Memory count
        """
        self._ensure_initialized()
        return self._collection.count()

    async def clear(self) -> None:
        """Delete all memories for this user."""
        self._ensure_initialized()
        ids = self._collection.get()["ids"]
        if ids:
            self._collection.delete(ids=ids)
        logger.debug(f"Cleared {len(ids)} memories for user '{self.user_id}'")
