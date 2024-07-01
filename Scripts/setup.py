import os
import subprocess
import json

def create_windows_startup_entry(script_path, base):
    startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
    startup_script_path = os.path.join(startup_folder, 'start_searchCD.bat')

    with open(startup_script_path, 'w') as startup_script:
        startup_script.write(f'@echo off\ncd "{base}"\npython3 "{script_path}"\n')
    print(f"Startup script created at {startup_script_path}")

def create_unix_startup_entry(script_path):
    autostart_dir = os.path.expanduser('~/.config/autostart')
    os.makedirs(autostart_dir, exist_ok=True)
    autostart_file = os.path.join(autostart_dir, 'searchCD.desktop')
    with open(autostart_file, 'w') as f:
        f.write(f"""[Desktop Entry]
                Type=Application
                Exec=python3 {script_path}
                Hidden=false
                NoDisplay=false
                X-GNOME-Autostart-enabled=true
                Name=searchCD
                Comment=Start searchCD on login""")

def run_script(script_path):
    subprocess.run(['python3', script_path]) 

if __name__ == "__main__": #### this file must be executed in the base directory of the project with "python3 Scripts/setup.py"
    script_path = os.path.abspath('Scripts/searchCD.py')

    with open("JSON-Files/AlgorithmAttributes.json", 'r') as f:
        algoAttr = json.load(f)
    base = os.getcwd()
    algoAttr["base"] = base
    with open("JSON-Files/AlgorithmAttributes.json", 'w') as f:
        json.dump(algoAttr, f)
    
    if os.name == 'nt':
        create_windows_startup_entry(script_path, base)
    else:
        create_unix_startup_entry(script_path)
    run_script(script_path)
    
