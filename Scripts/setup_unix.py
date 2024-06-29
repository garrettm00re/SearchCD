import os
import subprocess

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
Comment=Start searchCD on login
""")
    
    print(f"Autostart entry created at {autostart_file}")

def run_script(script_path):
    subprocess.run(['python3', script_path])

if __name__ == "__main__":
    script_path = os.path.abspath('searchCD.py')
    create_unix_startup_entry(script_path)
    run_script(script_path)
