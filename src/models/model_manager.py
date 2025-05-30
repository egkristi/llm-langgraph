from typing import Dict, List, Any, Optional
import ollama
import json
from pathlib import Path
from langchain_core.language_models import LLM
from langchain_community.llms.ollama import Ollama

# Path to models.json file in the config directory
CONFIG_DIR = Path("config")
MODELS_FILE = CONFIG_DIR / "models.json"

# Create config directory if it doesn't exist
CONFIG_DIR.mkdir(exist_ok=True)

# Cache for model instances
_model_cache: Dict[str, LLM] = {}

class ModelManager:
    """Manages LLM models and their configuration."""
    
    def __init__(self, default_model: str = "llama3"):
        self.default_model = default_model
        self.ollama_host = "http://localhost:11434"
        self.load_models_file()
        
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
    
    def load_models_file(self) -> Dict:
        """Load the models.json file."""
        try:
            if MODELS_FILE.exists():
                with open(MODELS_FILE, 'r') as f:
                    return json.load(f)
            else:
                # Create default models file if it doesn't exist
                default_data = {
                    "recommended_models": [],
                    "installed_models": []
                }
                with open(MODELS_FILE, 'w') as f:
                    json.dump(default_data, f, indent=2)
                return default_data
        except Exception as e:
            print(f"Error loading models file: {str(e)}")
            return {"recommended_models": [], "installed_models": []}
    
    def save_models_file(self, data: Dict) -> bool:
        """Save data to the models.json file."""
        try:
            with open(MODELS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving models file: {str(e)}")
            return False
    
    def get_all_models(self) -> Dict[str, List]:
        """Get all recommended and installed models."""
        # Load models file
        models_data = self.load_models_file()
        
        # Get currently available models from Ollama
        available_models = self.list_available_models()
        
        # Update installed models
        models_data["installed_models"] = available_models
        
        # Save updated data
        self.save_models_file(models_data)
        
        return {
            "recommended": models_data.get("recommended_models", []),
            "installed": available_models
        }
    
    def is_model_installed(self, model_name: str) -> bool:
        """Check if a model is installed in Ollama."""
        available_models = self.list_available_models()
        return model_name in available_models
    
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
            
            # Update installed models list
            models_data = self.load_models_file()
            if model_name not in models_data["installed_models"]:
                models_data["installed_models"].append(model_name)
                self.save_models_file(models_data)
            
            return True
        except Exception as e:
            print(f"Error pulling model {model_name}: {str(e)}")
            return False
            
    def add_custom_model(self, model_name: str, display_name: str = None, 
                        description: str = None, tags: List[str] = None) -> bool:
        """Add a custom model to models.json with metadata.
        
        Args:
            model_name: The model name used for Ollama API calls
            display_name: Human-readable name for the UI (defaults to model_name if None)
            description: Description of the model (defaults to "Custom Ollama model" if None)
            tags: List of tags for the model (defaults to ["custom"] if None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Pull the model first to ensure it exists
            if not self.pull_model(model_name):
                return False
                
            # Prepare model metadata
            display_name = display_name or model_name
            description = description or f"Custom Ollama model: {model_name}"
            tags = tags or ["custom"]
            
            # Create model metadata entry
            model_entry = {
                "name": model_name,
                "display_name": display_name,
                "description": description,
                "tags": tags
            }
            
            # Load current models data
            models_data = self.load_models_file()
            
            # Check if model already exists in recommended_models
            existing_model = next((m for m in models_data.get("recommended_models", []) 
                                 if m.get("name") == model_name), None)
            
            if existing_model:
                # Update existing model entry
                existing_model.update(model_entry)
            else:
                # Add new model entry
                models_data.setdefault("recommended_models", []).append(model_entry)
            
            # Ensure model is in installed_models list
            if model_name not in models_data.setdefault("installed_models", []):
                models_data["installed_models"].append(model_name)
                
            # Save updated models data
            self.save_models_file(models_data)
            return True
            
        except Exception as e:
            print(f"Error adding custom model {model_name}: {str(e)}")
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
