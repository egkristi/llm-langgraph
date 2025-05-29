from typing import Dict, Optional, Any
import ollama
from langchain_community.llms.ollama import Ollama
from langchain_core.language_models import LLM

# Cache for LLM instances to avoid recreating them
_model_cache: Dict[str, LLM] = {}

class ModelManager:
    """Manages LLM models and their configuration."""
    
    def __init__(self, default_model: str = "llama3"):
        self.default_model = default_model
        self.ollama_host = "http://localhost:11434"
        
    def set_default_model(self, model_name: str):
        """Set the default model to use."""
        self.default_model = model_name
        
    def set_ollama_host(self, host: str):
        """Set the Ollama host."""
        self.ollama_host = host
        
    def get_model(self, model_name: Optional[str] = None) -> LLM:
        """Get an LLM instance for the specified model."""
        model_name = model_name or self.default_model
        return get_model(model_name, self.ollama_host)
        
    def list_available_models(self) -> list:
        """List all available models from Ollama."""
        try:
            # Set Ollama base URL before making the API call
            original_base_url = ollama.BASE_URL
            ollama.BASE_URL = self.ollama_host
            
            # Make the API call
            response = ollama.list()
            
            # Restore original base URL
            ollama.BASE_URL = original_base_url
            
            # Check if response has models attribute (object format)
            if hasattr(response, 'models') and isinstance(response.models, list):
                models = []
                for model in response.models:
                    if hasattr(model, 'model'):
                        # Extract model name (removing ':latest' if present)
                        model_name = model.model.split(':')[0] if ':' in model.model else model.model
                        models.append(model_name)
                    else:
                        # Fallback to string representation
                        models.append(str(model))
                return models
            
            # Check dict format as fallback
            if isinstance(response, dict) and 'models' in response:
                if isinstance(response['models'], list):
                    models = []
                    for model in response['models']:
                        if isinstance(model, dict):
                            # Try different field names that might contain the model name
                            for field in ['model', 'name', 'id']:
                                if field in model:
                                    model_name = model[field]
                                    # Remove version tag if present
                                    if isinstance(model_name, str) and ':' in model_name:
                                        model_name = model_name.split(':')[0]
                                    models.append(model_name)
                                    break
                            else:
                                # If no recognized fields, use string representation
                                models.append(str(model))
                    return models
            
            # If response is a dict without models key but has other keys, use those as fallback
            if isinstance(response, dict) and len(response) > 0 and 'models' not in response:
                print("Unexpected Ollama response format, attempting to extract model names")
                return list(response.keys())
            
            print("Could not parse Ollama API response")
            return []
        except Exception as e:
            print(f"Error listing models: {str(e)}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a new model from Ollama."""
        try:
            # Set Ollama base URL before making the API call
            original_base_url = ollama.BASE_URL
            ollama.BASE_URL = self.ollama_host
            
            # Pull the model
            ollama.pull(model_name)
            
            # Restore original base URL
            ollama.BASE_URL = original_base_url
            return True
        except Exception as e:
            print(f"Error pulling model {model_name}: {str(e)}")
            return False

def get_model(model_name: str, host: str = "http://localhost:11434") -> LLM:
    """Get or create an LLM instance for the specified model."""
    cache_key = f"{model_name}@{host}"
    
    if cache_key not in _model_cache:
        _model_cache[cache_key] = Ollama(
            model=model_name,
            base_url=host,
            temperature=0.7,
        )
    
    return _model_cache[cache_key]
