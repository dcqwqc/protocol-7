import sys
from config import load_config

if __name__ == "__main__":
    config = load_config()
    
    if "--settings" in sys.argv:
        if sys.platform == "win32":
            import settings_ui_win
            settings_ui_win.run_settings(config)
        else:
            import settings_ui_linux
            settings_ui_linux.run_settings(config)
        sys.exit(0)
        
    if sys.platform == "win32":
        import main_win
        app = main_win.Protocol7App()
        app.run()
    else:
        import main_linux
        app = main_linux.Protocol7App()
        app.run()
