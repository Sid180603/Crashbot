"""
Migration Utility for Siemens AI Integration
Helps migrate from OpenAI/Anthropic to Siemens AI API
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import asyncio
from typing import Dict, Any, List
from app.core.config import settings
from app.core.logging import get_logger
from app.llm.analyzer import LLMAnalyzer
from app.rag.vector_store import get_vector_store
import openai

logger = get_logger(__name__)


class SiemensMigration:
    """Migration utility for Siemens AI"""
    
    def __init__(self):
        self.vector_store = None
        self.old_embedding_model = None
        self.new_embedding_model = None
    
    def test_api_connection(self) -> bool:
        """Test connection to Siemens AI API"""
        logger.info("Testing Siemens AI API connection...")
        
        try:
            if not settings.SIEMENS_API_KEY:
                logger.error("SIEMENS_API_KEY not set in environment")
                return False
            
            if settings.SIEMENS_API_KEY == "SIAK-your-siemens-api-key-here":
                logger.error("SIEMENS_API_KEY is still using placeholder value")
                logger.info("Please update your .env file with actual API key from my.siemens.com")
                return False
            
            # Test LLM endpoint
            client = openai.OpenAI(
                api_key=settings.SIEMENS_API_KEY,
                base_url=settings.LLM_BASE_URL
            )
            
            response = client.chat.completions.create(
                model="mistral-7b-instruct",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10
            )
            
            logger.info(f"✅ LLM API connection successful! Response: {response.choices[0].message.content[:50]}")
            
            # Test embeddings endpoint
            embed_response = client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input="Test embedding"
            )
            
            logger.info(f"✅ Embeddings API connection successful! Dimensions: {len(embed_response.data[0].embedding)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ API connection failed: {e}")
            logger.info("\nTroubleshooting:")
            logger.info("1. Verify API key is correct (get from my.siemens.com)")
            logger.info("2. Check network connectivity to api.siemens.com")
            logger.info("3. Ensure you're on Siemens network or VPN")
            logger.info("4. Verify API key has 'llm' scope")
            return False
    
    def test_crash_analysis(self) -> bool:
        """Test crash analysis with Siemens model"""
        logger.info("\nTesting crash analysis with Siemens AI...")
        
        try:
            # Sample crash data
            crash_data = {
                "exception_code": "0xC0000005",
                "exception_message": "Access Violation",
                "faulting_module": "test.dll",
                "faulting_address": "0x00007FF12345",
                "platform": "Windows",
                "architecture": "x64",
                "stack_trace": [
                    {"module": "test.dll", "function": "main", "offset": "+0x10", "address": "0x00007FF12345"}
                ]
            }
            
            analyzer = LLMAnalyzer()
            result = analyzer.analyze_crash(crash_data)
            
            logger.info(f"✅ Analysis successful!")
            logger.info(f"   Root Cause: {result.get('root_cause', 'N/A')[:100]}")
            logger.info(f"   Confidence: {result.get('confidence_score', 0)}%")
            logger.info(f"   Solutions: {len(result.get('solutions', []))}")
            logger.info(f"   Cost: ${analyzer.cost_usd:.4f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Crash analysis failed: {e}")
            return False
    
    def test_embeddings(self) -> bool:
        """Test embedding generation"""
        logger.info("\nTesting embedding generation...")
        
        try:
            vector_store = get_vector_store()
            
            # Sample crash data
            crash_data = {
                "exception_code": "0xC0000005",
                "exception_message": "Access Violation",
                "faulting_module": "test.dll",
                "platform": "Windows"
            }
            
            # Generate embedding
            embedding = vector_store._generate_embedding(
                vector_store._crash_to_text(crash_data)
            )
            
            if embedding:
                logger.info(f"✅ Embedding generation successful!")
                logger.info(f"   Dimensions: {len(embedding)}")
                logger.info(f"   Provider: {vector_store.embedding_provider}")
                logger.info(f"   Model: {settings.EMBEDDING_MODEL}")
                return True
            else:
                logger.warning("⚠️ No embedding generated (using Chroma default)")
                return True
            
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            return False
    
    def compare_models(self) -> Dict[str, Any]:
        """Compare different Siemens models"""
        logger.info("\nComparing Siemens models...")
        
        models = [
            "mistral-7b-instruct",
            "qwen3-30b-a3b-instruct-2507",
            "devstral-small-2505"
        ]
        
        crash_data = {
            "exception_code": "0xC0000005",
            "exception_message": "Access Violation",
            "faulting_module": "test.dll",
            "platform": "Windows",
            "stack_trace": [
                {"module": "test.dll", "function": "process_data", "offset": "+0x50"}
            ]
        }
        
        results = {}
        
        for model in models:
            try:
                logger.info(f"\nTesting {model}...")
                
                import time
                start = time.time()
                
                analyzer = LLMAnalyzer()
                analyzer.model = model
                result = analyzer.analyze_crash(crash_data)
                
                duration = time.time() - start
                
                results[model] = {
                    "success": True,
                    "duration": duration,
                    "cost": analyzer.cost_usd,
                    "confidence": result.get("confidence_score", 0),
                    "solutions": len(result.get("solutions", []))
                }
                
                logger.info(f"   Duration: {duration:.2f}s")
                logger.info(f"   Confidence: {result.get('confidence_score', 0)}%")
                logger.info(f"   Cost: ${analyzer.cost_usd:.4f}")
                
            except Exception as e:
                logger.error(f"   ❌ Failed: {e}")
                results[model] = {"success": False, "error": str(e)}
        
        # Print comparison
        logger.info("\n" + "="*60)
        logger.info("MODEL COMPARISON SUMMARY")
        logger.info("="*60)
        
        for model, data in results.items():
            if data.get("success"):
                logger.info(f"\n{model}:")
                logger.info(f"  Speed: {data['duration']:.2f}s")
                logger.info(f"  Confidence: {data['confidence']}%")
                logger.info(f"  Solutions: {data['solutions']}")
                logger.info(f"  Cost: ${data['cost']:.4f}")
        
        return results
    
    def check_configuration(self) -> bool:
        """Check if configuration is set up correctly"""
        logger.info("\nChecking configuration...")
        
        checks = []
        
        # Check API key
        if settings.SIEMENS_API_KEY and settings.SIEMENS_API_KEY != "SIAK-your-siemens-api-key-here":
            logger.info("✅ SIEMENS_API_KEY is set")
            checks.append(True)
        else:
            logger.error("❌ SIEMENS_API_KEY not configured")
            checks.append(False)
        
        # Check provider
        if settings.LLM_PROVIDER == "siemens":
            logger.info("✅ LLM_PROVIDER set to 'siemens'")
            checks.append(True)
        else:
            logger.warning(f"⚠️ LLM_PROVIDER is '{settings.LLM_PROVIDER}', expected 'siemens'")
            checks.append(False)
        
        # Check base URL
        if settings.LLM_BASE_URL == "https://api.siemens.com/llm/v1":
            logger.info("✅ LLM_BASE_URL is correct")
            checks.append(True)
        else:
            logger.error(f"❌ LLM_BASE_URL is '{settings.LLM_BASE_URL}'")
            checks.append(False)
        
        # Check model
        siemens_models = [
            "qwen3-30b-a3b-instruct-2507", "devstral-small-2505", 
            "mistral-7b-instruct", "deepseek-r1-0528-qwen3-8b"
        ]
        if settings.LLM_MODEL in siemens_models:
            logger.info(f"✅ LLM_MODEL is '{settings.LLM_MODEL}'")
            checks.append(True)
        else:
            logger.warning(f"⚠️ LLM_MODEL is '{settings.LLM_MODEL}', not a Siemens model")
            checks.append(False)
        
        # Check embedding configuration
        if settings.EMBEDDING_PROVIDER == "siemens":
            logger.info("✅ EMBEDDING_PROVIDER set to 'siemens'")
            checks.append(True)
        else:
            logger.warning(f"⚠️ EMBEDDING_PROVIDER is '{settings.EMBEDDING_PROVIDER}'")
            checks.append(False)
        
        return all(checks)
    
    def run_migration(self):
        """Run full migration process"""
        logger.info("="*60)
        logger.info("SIEMENS AI MIGRATION UTILITY")
        logger.info("="*60)
        
        # Step 1: Check configuration
        logger.info("\n[1/5] Checking configuration...")
        config_ok = self.check_configuration()
        
        if not config_ok:
            logger.error("\n❌ Configuration incomplete. Please update your .env file.")
            logger.info("\nRequired settings:")
            logger.info("  SIEMENS_API_KEY=SIAK-your-key")
            logger.info("  LLM_PROVIDER=siemens")
            logger.info("  LLM_BASE_URL=https://api.siemens.com/llm/v1")
            logger.info("  LLM_MODEL=qwen3-30b-a3b-instruct-2507")
            logger.info("  EMBEDDING_PROVIDER=siemens")
            return False
        
        # Step 2: Test API connection
        logger.info("\n[2/5] Testing API connection...")
        if not self.test_api_connection():
            logger.error("\n❌ API connection failed. Cannot proceed.")
            return False
        
        # Step 3: Test crash analysis
        logger.info("\n[3/5] Testing crash analysis...")
        if not self.test_crash_analysis():
            logger.error("\n❌ Crash analysis failed.")
            return False
        
        # Step 4: Test embeddings
        logger.info("\n[4/5] Testing embeddings...")
        if not self.test_embeddings():
            logger.error("\n❌ Embedding generation failed.")
            return False
        
        # Step 5: Compare models (optional)
        logger.info("\n[5/5] Running model comparison (optional)...")
        try:
            self.compare_models()
        except Exception as e:
            logger.warning(f"Model comparison failed: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ MIGRATION SUCCESSFUL!")
        logger.info("="*60)
        logger.info("\nYour Crashbot is now using Siemens AI API!")
        logger.info("\nNext steps:")
        logger.info("1. Start your services: docker-compose up")
        logger.info("2. Upload a test crash dump")
        logger.info("3. Monitor logs for Siemens API usage")
        logger.info("4. Check cost savings in analysis results")
        
        return True


def main():
    """Main entry point"""
    migration = SiemensMigration()
    
    import argparse
    parser = argparse.ArgumentParser(description="Siemens AI Migration Utility")
    parser.add_argument(
        "--check", action="store_true",
        help="Only check configuration"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Test API connection only"
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Compare different models"
    )
    
    args = parser.parse_args()
    
    if args.check:
        migration.check_configuration()
    elif args.test:
        migration.test_api_connection()
    elif args.compare:
        migration.compare_models()
    else:
        # Run full migration
        success = migration.run_migration()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
