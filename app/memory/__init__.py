# memory package - layered memory system
from app.memory.base import BaseMemory
from app.memory.working_memory import WorkingMemory
from app.memory.session_memory import SessionMemory
from app.memory.project_memory import ProjectMemory
from app.memory.knowledge_memory import KnowledgeMemory
from app.memory.manager import ContextManager

# M4: hierarchical memory (L1 episodic / L2 semantic / L3 procedural)
from app.memory.embedder import HashingEmbedder, cosine_similarity
from app.memory.episodic_memory import EpisodicMemory
from app.memory.semantic_memory import SemanticMemory
from app.memory.procedural_memory import ProceduralMemory
from app.memory.consolidation import MemoryConsolidation
from app.memory.hierarchical import HierarchicalMemory

__all__ = [
    "BaseMemory",
    "WorkingMemory",
    "SessionMemory",
    "ProjectMemory",
    "KnowledgeMemory",
    "ContextManager",
    "HashingEmbedder",
    "cosine_similarity",
    "EpisodicMemory",
    "SemanticMemory",
    "ProceduralMemory",
    "MemoryConsolidation",
    "HierarchicalMemory",
]