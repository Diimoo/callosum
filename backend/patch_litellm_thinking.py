#!/usr/bin/env python3
"""
Patch litellm to handle Ollama's "thinking" field from chain-of-thought models.
This fixes the issue with models like qwen3-vl that use reasoning streams.
"""
import os
import sys

LITELLM_FILE = "/usr/local/lib/python3.11/site-packages/litellm/llms/ollama/completion/transformation.py"

def patch_litellm():
    if not os.path.exists(LITELLM_FILE):
        print(f"Warning: {LITELLM_FILE} not found, skipping patch")
        return
    
    with open(LITELLM_FILE, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if '"thinking" in chunk' in content:
        print("litellm already patched for 'thinking' field support")
        return
    
    # Find and replace the problematic section
    old_code = '''            elif chunk["response"]:
                text = chunk["response"]
                return GenericStreamingChunk(
                    text=text,
                    is_finished=is_finished,
                    finish_reason="stop",
                    usage=None,
                )
            else:
                raise Exception(f"Unable to parse ollama chunk - {chunk}")'''
    
    new_code = '''            elif "thinking" in chunk:
                # Handle chain-of-thought reasoning chunks from newer Ollama models
                # These chunks have "thinking" field but may have empty "response"
                return GenericStreamingChunk(
                    text="",
                    is_finished=False,
                    finish_reason=None,
                    usage=None,
                )
            elif chunk.get("response"):
                text = chunk["response"]
                return GenericStreamingChunk(
                    text=text,
                    is_finished=is_finished,
                    finish_reason="stop",
                    usage=None,
                )
            else:
                raise Exception(f"Unable to parse ollama chunk - {chunk}")'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(LITELLM_FILE, 'w') as f:
            f.write(content)
        print("✅ Successfully patched litellm for Ollama 'thinking' field support")
    else:
        print("⚠️  Could not find expected code pattern in litellm file")
        print("The litellm version may have changed. Manual patching required.")
        sys.exit(1)

if __name__ == "__main__":
    patch_litellm()
