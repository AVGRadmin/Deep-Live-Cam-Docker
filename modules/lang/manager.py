import importlib

class LanguageManager:
    def __init__(self):
        self.languages = {
            'english': 'modules.lang.english',
            'french': 'modules.lang.french',
            'spanish': 'modules.lang.spanish',
            'german': 'modules.lang.german',
            'arabic': 'modules.lang.arabic',
            'dutch': 'modules.lang.dutch',
            'hindi': 'modules.lang.hindi',
            'italian': 'modules.lang.italian',
            'korean': 'modules.lang.korean',
            'polish': 'modules.lang.polish',
            'turkish': 'modules.lang.turkish',
            'chinese_simplified': 'modules.lang.chinese_simplified',
            'japanese': 'modules.lang.japanese',
            'portuguese': 'modules.lang.portuguese',
            'russian': 'modules.lang.russian',
            'swedish': 'modules.lang.swedish'
        }
        self.current_language = 'english'
        self.load_language(self.current_language)

    def load_language(self, language_name):
        if language_name not in self.languages:
            raise ValueError(f"Language {language_name} is not supported")
        module_name = self.languages[language_name]
        module = importlib.import_module(module_name)
        self.ui_lang = module.UI()  # Load the UI class from the module

    def set_language(self, language_name):
        self.load_language(language_name)
        
    def get_language(self):
        return self.ui_lang

    def get_available_languages(self):
        return list(self.languages.keys())

    def get_text(self, key):
        # Attempt to get the text attribute from the UI class
        return getattr(self.ui_lang, key, f"Text for key '{key}' not found")
