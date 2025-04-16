try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import from transformers: {str(e)}")
    logger.error("Please install transformers package: pip install transformers torch")
    raise

import logging
import os

logger = logging.getLogger(__name__)

class ModelLoader:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._model_loaded = False
        
    def load_model(self, model_path=None):
        """Load model from path or default cache location"""
        try:
            kwargs = {
                "device_map": "auto",
                "torch_dtype": torch.float16
            }
            
            if model_path:
                self.model = AutoModelForCausalLM.from_pretrained(model_path, **kwargs)
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            else:
                # Try loading from local models directory first
                default_model = os.path.join(os.path.dirname(__file__), "models", "sql-model")
                if os.path.exists(default_model):
                    self.model = AutoModelForCausalLM.from_pretrained(default_model, **kwargs)
                    self.tokenizer = AutoTokenizer.from_pretrained(default_model)
                else:
                    # Fallback to loading from Hugging Face
                    model_id = "pavankumarbalijepalli/phi2-sqlcoder"
                    self.model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
                    self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            
            self._model_loaded = True
            return True
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self._model_loaded = False
            return False
    
    def set_model_path(self, model_path):
        """Set and load model from specific path"""
        return self.load_model(model_path)
    
    def is_loaded(self):
        """Check if model is loaded"""
        return self._model_loaded
    
    def generate_sql(self, question, schema_context):
        """Generate SQL from question"""
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")
        
        # More focused prompt template
        prompt = f"""### Task: Generate only a SQL query (no explanations) for the following question.

### Question: 
{question}

### Available Tables and Their Relationships:
{schema_context}

### Response (SQL only):
"""
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True).to(self.model.device)
            
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,  # Reduced for faster response
                num_return_sequences=1,
                temperature=0.2,  # Slightly increased for better reasoning
                do_sample=False,   # Deterministic output
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Clean up the response
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the SQL query
            if "Response (SQL only):" in generated_text:
                sql_query = generated_text.split("Response (SQL only):")[-1].strip()
            else:
                sql_query = generated_text.strip()
            
            return sql_query.split(';')[0]  # Return only the first query if multiple are generated
            
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return "Error generating SQL query"

# Create singleton instance
model = ModelLoader()