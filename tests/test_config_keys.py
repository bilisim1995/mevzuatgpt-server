#!/usr/bin/env python3
"""
Test configuration keys from both environment and .env
"""

import os
import sys
sys.path.append('/home/runner/workspace')

from core.config import settings

def test_api_keys():
    """Test API key sources"""
    
    print("🔑 API KEY CONFIGURATION TEST")
    print("=" * 40)
    
    print("Environment Variables:")
    openai_env = os.getenv('OPENAI_API_KEY', 'Not set')
    groq_env = os.getenv('GROQ_API_KEY', 'Not set')
    print(f"  OPENAI_API_KEY: {openai_env[:20]}..." if openai_env != 'Not set' else "  OPENAI_API_KEY: Not set")
    print(f"  GROQ_API_KEY: {groq_env[:20]}..." if groq_env != 'Not set' else "  GROQ_API_KEY: Not set")
    
    print("\nSettings Configuration:")
    print(f"  settings.OPENAI_API_KEY: {settings.OPENAI_API_KEY[:20]}...")
    print(f"  settings.GROQ_API_KEY: {settings.GROQ_API_KEY[:20]}..." if settings.GROQ_API_KEY != "your-groq-api-key-here" else "  settings.GROQ_API_KEY: Default value")
    print(f"  settings.AI_PROVIDER: {settings.AI_PROVIDER}")
    
    print("\nKey Validation:")
    openai_valid = settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith('sk-')
    groq_valid = settings.GROQ_API_KEY and settings.GROQ_API_KEY.startswith('gsk_')
    print(f"  OpenAI key valid: {'✅' if openai_valid else '❌'}")
    print(f"  Groq key valid: {'✅' if groq_valid else '❌'}")
    
    print(f"\nSystem ready: {'✅' if openai_valid and groq_valid else '❌'}")

if __name__ == "__main__":
    test_api_keys()