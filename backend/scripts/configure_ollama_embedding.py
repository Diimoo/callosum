#!/usr/bin/env python3
"""
Script to configure Ollama as the embedding provider.
Run this after adding the Ollama embedding support code.
"""

import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.orm import Session

from onyx.db.engine.sql_engine import get_sqlalchemy_engine
from onyx.db.models import CloudEmbeddingProvider, SearchSettings
from shared_configs.enums import EmbeddingProvider


def configure_ollama_embedding():
    """Configure Ollama as the embedding provider for qwen3-embedding."""
    
    engine = get_sqlalchemy_engine()
    
    with Session(engine) as db_session:
        # First, check if Ollama provider exists
        existing_provider = db_session.query(CloudEmbeddingProvider).filter_by(
            provider_type=EmbeddingProvider.OLLAMA
        ).first()
        
        if not existing_provider:
            # Create Ollama embedding provider
            ollama_provider = CloudEmbeddingProvider(
                provider_type=EmbeddingProvider.OLLAMA,
                api_url="http://localhost:11434",
                api_key=None,  # Ollama doesn't need an API key
            )
            db_session.add(ollama_provider)
            db_session.commit()
            print("✓ Created Ollama embedding provider")
        else:
            print("✓ Ollama embedding provider already exists")
        
        # Update current search settings to use Ollama
        current_settings = db_session.query(SearchSettings).filter_by(
            model_name="qwen3-embedding"
        ).first()
        
        if current_settings:
            current_settings.provider_type = EmbeddingProvider.OLLAMA
            db_session.commit()
            print(f"✓ Updated search settings to use Ollama provider")
            print(f"  Model: {current_settings.model_name}")
            print(f"  Dimension: {current_settings.model_dim}")
        else:
            # Check for any search settings and show them
            all_settings = db_session.query(SearchSettings).all()
            if all_settings:
                print("\nExisting search settings:")
                for s in all_settings:
                    print(f"  - {s.model_name} (provider: {s.provider_type}, dim: {s.model_dim})")
                print("\nTo update, modify the model_name filter in this script.")
            else:
                print("⚠ No search settings found. You may need to configure embedding through the admin UI.")
        
        print("\n✓ Ollama embedding configuration complete!")
        print("  Restart the backend services to apply changes.")


if __name__ == "__main__":
    configure_ollama_embedding()
