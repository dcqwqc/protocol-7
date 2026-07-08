import os
import threading
from huggingface_hub import hf_hub_download

class LLMRewriter:
    def __init__(self, config):
        self.config = config
        self.llm = None
        self.is_loading = False
        self.repo_id = self.config.get("llama_repo", "bartowski/Llama-3.2-3B-Instruct-GGUF")
        self.filename = self.config.get("llama_filename", "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
        
    def load_model(self):
        if not self.config.get("enable_llm_rewrite", True):
            return
            
        backend = self.config.get("llm_backend", "Built-in (Llama.cpp)")
        if backend == "Ollama Server":
            print("Using Ollama backend for grammar correction. Skipping Llama.cpp load.")
            return

        if self.llm is not None or self.is_loading:
            return
            
        self.is_loading = True
        try:
            print("Downloading/Loading local LLaMA 3.2 1B for rewriting...")
            model_path = hf_hub_download(repo_id=self.repo_id, filename=self.filename)
            
            # Import here to avoid blocking startup if not used
            from llama_cpp import Llama
            self.llm = Llama(
                model_path=model_path,
                n_ctx=512,  # keep context tiny for speed
                n_threads=4,
                verbose=False
            )
            print("LLaMA ready for post-processing.")
        except Exception as e:
            print(f"Error loading local LLM: {e}")
        finally:
            self.is_loading = False

    def rewrite(self, text):
        backend = self.config.get("llm_backend", "Built-in (Llama.cpp)")
        if not self.config.get("enable_llm_rewrite", True):
            return text
        if backend != "Ollama Server" and self.llm is None:
            return text
            
        # Fast filter for common Whisper silence hallucinations
        clean_input = text.strip().lower()
        hallucinations = ["you", "you.", "thanks for watching.", "thanks.", "(silence)", "[silence]", "[blank_audio]", "am i?", "bye.", "thank you.", "thank you"]
        if not clean_input or clean_input in hallucinations:
            return ""
            
        default_prompt = """You are an expert Speech-to-Text (STT) editor. Your sole task is to process raw voice transcripts and output the speaker's final, intended message in clean, readable text.

### Core Directives:
1. Eliminate Disfluencies: Remove all filler words (um, uh, ah, like, you know) and stutters/repeated words (e.g., "I I went" becomes "I went").
2. Apply Self-Corrections: When the speaker changes their mind mid-sentence (using phrases like "I mean," "actually," "no wait"), strictly apply their final intent and delete the abandoned thought.
3. Fix Phonetic Typos: Correct obvious transcription errors based on context (e.g., "the dog parked" becomes "the dog barked").
4. Add Mechanics: Apply proper capitalization and punctuation to make the sentence grammatically correct.
5. Preserve Meaning: Do not summarize, paraphrase, or change the user's intended tone or vocabulary. Only fix the mechanics of the speech.
6. Absolute Constraint: Output ONLY the final cleaned text. Do not include introductory phrases, quotes, or explanations. 

### Examples:

Input: uh hey what's up man I I was wondering if you wanted to go
Output: Hey, what's up man? I was wondering if you wanted to go.

Input: set a timer for 10 or actually 15 minutes
Output: Set a timer for 15 minutes.

Input: let's meet at 7 a.m. oh wait i mean 8 a.m. no actually let's do noon in Los Angeles
Output: Let's meet at noon in Los Angeles.

Input: remind me to buy eggs milk and oh wait i don't need milk just eggs and bread
Output: Remind me to buy eggs and bread.

Input: the dog parked loudly at the mailman
Output: The dog barked loudly at the mailman."""

        system_prompt = self.config.get("llm_system_prompt", default_prompt)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Input: {text}"}
        ]
        
        try:
            print("Rewriting text with local LLM...")
            
            clean_text = ""
            backend = self.config.get("llm_backend", "Built-in (Llama.cpp)")
            
            if backend == "Ollama Server":
                import urllib.request
                import json
                ollama_model = self.config.get("ollama_model", "llama3.2")
                ollama_endpoint = self.config.get("ollama_endpoint", "http://127.0.0.1:11434").rstrip("/")
                data = {
                    "model": ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.0}
                }
                req = urllib.request.Request(f"{ollama_endpoint}/api/chat", data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req) as response:
                    res = json.loads(response.read().decode('utf-8'))
                    clean_text = res.get("message", {}).get("content", "").strip()
            else:
                response = self.llm.create_chat_completion(
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.0,
                    stop=["\n", "Text:", "User:"]
                )
                clean_text = response["choices"][0]["message"]["content"].strip()
                
            # If the LLM completely failed or output empty string, fallback to original
            if not clean_text:
                clean_text = text
                
            final_text = clean_text
            
            # LAYER 3: Google Translate
            translate_target = self.config.get("translate_target", "")
            # Whisper handles English natively if configured, but let's translate if target is non-English
            if translate_target and translate_target != "English":
                print(f"Translating to {translate_target} via Google Translate API...")
                
                lang_codes = {
                    "English": "en", "Spanish": "es", "French": "fr", "German": "de", "Italian": "it",
                    "Portuguese": "pt", "Russian": "ru", "Japanese": "ja", "Korean": "ko", "Chinese": "zh-CN",
                    "Arabic": "ar", "Hindi": "hi", "Dutch": "nl", "Turkish": "tr", "Polish": "pl",
                    "Swedish": "sv", "Danish": "da", "Finnish": "fi", "Norwegian": "no", "Greek": "el",
                    "Thai": "th", "Vietnamese": "vi", "Indonesian": "id", "Hebrew": "he", "Bengali": "bn",
                    "Romanian": "ro", "Czech": "cs", "Ukrainian": "uk", "Hungarian": "hu", "Malay": "ms"
                }
                
                target_code = lang_codes.get(translate_target, "en")
                
                import urllib.request
                import urllib.parse
                import json
                
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_code}&dt=t&q={urllib.parse.quote(clean_text)}"
                
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    # Google API returns nested arrays: [[[translated_text, original_text, ...]]]
                    final_text = "".join([sentence[0] for sentence in data[0]])

            # Debug Logging
            with open("/tmp/whisper_log.txt", "a") as f:
                f.write(f"--- TRANSCRIBED ---\nRAW: {text}\nLLM_CLEAN: {clean_text}\nTRANSLATED: {final_text}\n\n")

            return final_text
            
        except Exception as e:
            print(f"Processing failed: {e}")
            with open("/tmp/whisper_log.txt", "a") as f:
                f.write(f"ERROR: {e}\n\n")
            return text
