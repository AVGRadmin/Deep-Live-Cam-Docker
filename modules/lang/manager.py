import importlib
from .english import English
from .arabic import Arabic
from .german import German



class LanguageManager:
    def __init__(self):
        self.language_modules = {
            'english': English(),
            'arabic': Arabic(),
            'german': German()
        }

        self.current_language = 'english'  # Default to 'english'
        self.load_language(self.current_language)

    def load_language(self, language_name):
       if language_name not in self.language_modules:
           raise ValueError(f"Language {language_name} is not supported")
       self.ui_lang = self.language_modules[language_name] 

    def set_language(self, language_name):
        self.load_language(language_name)
        self.current_language = language_name
        
    def get_language(self):
        return self.ui_lang

    def get_available_languages(self):
        return list(self.language_modules.keys())

    def get_text(self, key):
        return getattr(self.ui_lang, key, f"Text for key '{key}' not found")
