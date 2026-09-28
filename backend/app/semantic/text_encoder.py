"""
CLIP Text Encoder for Semantic Search
Provides text embeddings compatible with CLIP image embeddings
"""

import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"

import torch
import numpy as np
from pathlib import Path
from transformers import CLIPProcessor, CLIPModel
import transformers.modeling_utils
transformers.modeling_utils.check_torch_load_is_safe = lambda: None
import transformers.utils.import_utils
transformers.utils.import_utils.check_torch_load_is_safe = lambda: None


class CLIPTextEncoder:
    """
    CLIP text encoder for text-to-image semantic search.
    Provides text embeddings compatible with CLIP image embeddings.
    """
    
    def __init__(self, model_name="openai/clip-vit-base-patch32", device="cpu"):
        """
        Initialize CLIP text encoder.
        
        Args:
            model_name: HuggingFace CLIP model name
            device: torch device ('cpu' or 'cuda')
        """
        self.device = torch.device(device)
        self.model_name = model_name
        
        print(f"Loading CLIP text encoder {model_name} to {self.device}...")
        
        # Load CLIP model and processor
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        
        # Set to evaluation mode
        self.model.eval()
        
        # Disable gradient computation for inference
        for param in self.model.parameters():
            param.requires_grad = False
            
        print(f"CLIP text encoder loaded successfully")
        print(f"Text embedding dimension: {self.model.config.text_config.hidden_size}")
    
    def encode_text(self, text_query: str) -> np.ndarray:
        """
        Encode text query into embedding vector compatible with CLIP image embeddings.
        
        Args:
            text_query: String query
            
        Returns:
            Normalized text embedding as numpy array (in same space as image embeddings)
        """
        with torch.no_grad():
            # Process text
            inputs = self.processor(text=[text_query], return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Use official CLIP method to get projected features
            text_features = self.model.get_text_features(**inputs)
            
            # Check if text_features is a tensor directly
            if isinstance(text_features, torch.Tensor):
                embedding = text_features.cpu().numpy()[0]
            else:
                # Extract the actual tensor from the output object
                if hasattr(text_features, 'text_embeds'):
                    embedding = text_features.text_embeds.cpu().numpy()[0]
                elif hasattr(text_features, 'pooler_output'):
                    embedding = text_features.pooler_output.cpu().numpy()[0]
                else:
                    # Fallback: try to extract tensor
                    for attr in dir(text_features):
                        if not attr.startswith('_') and hasattr(getattr(text_features, attr), 'cpu'):
                            tensor = getattr(text_features, attr)
                            if hasattr(tensor, 'numpy'):
                                embedding = tensor.numpy()[0]
                                break
                    else:
                        raise ValueError(f"Could not extract tensor from text_features. Type: {type(text_features)}")
            
            # Verify we got 512-D embedding
            if len(embedding) != 512:
                raise ValueError(f"Text embedding dimension is {len(embedding)}, expected 512")
            
            # Normalize for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)
            
        return embedding
    
    def encode_text_numpy(self, text_query: str) -> list:
        """
        Encode text query and return as list for Qdrant.
        
        Args:
            text_query: String query
            
        Returns:
            Text embedding as list
        """
        embedding = self.encode_text(text_query)
        return embedding.tolist()
    
    def get_embedding_dimension(self) -> int:
        """Return the dimension of text embeddings."""
        return self.model.config.text_config.hidden_size
    
    def __call__(self, text_query: str) -> str:
        """Convenience method for encoding text."""
        return self.encode_text_numpy(text_query)