"""
Seed script to populate ChromaDB with synthetic crash data.
This provides historical crash data for RAG (Retrieval Augmented Generation).
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.vector_store import get_vector_store

# Setup simple logging for script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Synthetic crash data representing common crash patterns
SEED_CRASHES = [
    {
        "crash_id": "seed_001",
        "exception_code": "0xC0000005",
        "exception_name": "ACCESS_VIOLATION",
        "faulting_module": "ntdll.dll",
        "faulting_function": "RtlpWaitOnCriticalSection",
        "stack_trace": [
            {"module": "ntdll.dll", "function": "RtlpWaitOnCriticalSection"},
            {"module": "kernel32.dll", "function": "BaseThreadInitThunk"}
        ],
        "root_cause": "Null pointer dereference in critical section handling",
        "solution": "Add null pointer check before accessing critical section object. Ensure proper initialization of CRITICAL_SECTION structure.",
        "tags": ["null_pointer", "critical_section", "access_violation"]
    },
    {
        "crash_id": "seed_002",
        "exception_code": "0xC0000005",
        "exception_name": "ACCESS_VIOLATION",
        "faulting_module": "myapp.exe",
        "faulting_function": "ProcessBuffer",
        "stack_trace": [
            {"module": "myapp.exe", "function": "ProcessBuffer"},
            {"module": "myapp.exe", "function": "HandleData"},
            {"module": "kernel32.dll", "function": "BaseThreadInitThunk"}
        ],
        "root_cause": "Buffer overflow due to insufficient bounds checking",
        "solution": "Implement proper bounds checking before buffer operations. Use safe string functions like strncpy_s instead of strcpy.",
        "tags": ["buffer_overflow", "bounds_check", "access_violation"]
    },
    {
        "crash_id": "seed_003",
        "exception_code": "0xC00000FD",
        "exception_name": "STACK_OVERFLOW",
        "faulting_module": "myapp.exe",
        "faulting_function": "RecursiveFunction",
        "stack_trace": [{"module": "myapp.exe", "function": "RecursiveFunction"} for _ in range(50)],
        "root_cause": "Infinite recursion without termination condition",
        "solution": "Add proper base case for recursion. Consider using iteration instead of recursion for deep call chains.",
        "tags": ["stack_overflow", "recursion", "infinite_loop"]
    },
    {
        "crash_id": "seed_004",
        "exception_code": "0xC0000374",
        "exception_name": "HEAP_CORRUPTION",
        "faulting_module": "ucrtbase.dll",
        "faulting_function": "free",
        "stack_trace": [
            {"module": "ucrtbase.dll", "function": "free"},
            {"module": "myapp.exe", "function": "Cleanup"},
            {"module": "kernel32.dll", "function": "BaseThreadInitThunk"}
        ],
        "root_cause": "Double free detected - memory freed twice",
        "solution": "Set pointers to NULL after freeing. Use smart pointers (std::unique_ptr, std::shared_ptr) to avoid manual memory management.",
        "tags": ["heap_corruption", "double_free", "memory_management"]
    },
    {
        "crash_id": "seed_005",
        "exception_code": "0xC0000005",
        "exception_name": "ACCESS_VIOLATION",
        "faulting_module": "myapp.exe",
        "faulting_function": "UseAfterFree",
        "stack_trace": [
            {"module": "myapp.exe", "function": "UseAfterFree"},
            {"module": "myapp.exe", "function": "Process"},
            {"module": "kernel32.dll", "function": "BaseThreadInitThunk"}
        ],
        "root_cause": "Use-after-free: accessing memory after it was freed",
        "solution": "Ensure objects are not used after deletion. Use RAII patterns and smart pointers to manage lifetime automatically.",
        "tags": ["use_after_free", "access_violation", "memory_lifetime"]
    }
]


async def seed_database():
    """Populate ChromaDB with seed crash data."""
    logger.info("Starting ChromaDB seeding process...")
    
    try:
        vector_store = get_vector_store()
        logger.info(f"Connected to vector store: {vector_store.__class__.__name__}")
        
        # Check current count
        try:
            if vector_store.collection:
                current_count = vector_store.collection.count()
                logger.info(f"Current vector DB count: {current_count}")
            else:
                current_count = 0
                logger.warning("Collection not initialized")
        except Exception as e:
            logger.warning(f"Could not get current count: {e}")
            current_count = 0
        
        # Add each crash
        added_count = 0
        for crash_data in SEED_CRASHES:
            crash_id = crash_data.get('crash_id', 'unknown')
            try:
                # Remove crash_id from data dict for embedding
                data_copy = {k: v for k, v in crash_data.items() if k != 'crash_id'}
                vector_store.add_crash_embedding(crash_id, data_copy)
                logger.info(f"Added crash {crash_id}: {crash_data['exception_name']} - {crash_data['root_cause'][:50]}...")
                added_count += 1
            except Exception as e:
                logger.error(f"Failed to add crash {crash_id}: {e}")
        
        # Verify final count
        try:
            if vector_store.collection:
                final_count = vector_store.collection.count()
                logger.info(f"Seeding complete! Added {added_count} crashes. Total in DB: {final_count}")
            else:
                logger.info(f"Seeding complete! Added {added_count} crashes.")
        except Exception as e:
            logger.warning(f"Could not get final count: {e}")
            logger.info(f"Seeding complete! Added {added_count} crashes.")
        
        # Test similarity search
        logger.info("\nTesting similarity search...")
        test_crash = {
            "exception_code": "0xC0000005",
            "faulting_module": "myapp.exe",
            "stack_trace": [
                {"module": "myapp.exe", "function": "ProcessBuffer"},
                {"module": "kernel32.dll", "function": "BaseThreadInitThunk"}
            ]
        }
        
        similar = vector_store.find_similar_crashes(test_crash, limit=3)
        logger.info(f"Found {len(similar)} similar crashes:")
        for i, crash in enumerate(similar, 1):
            logger.info(f"  {i}. {crash['crash_id']} (similarity: {crash['similarity']:.3f}) - {crash['root_cause'][:60]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(seed_database())
    sys.exit(0 if success else 1)
