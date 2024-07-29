import os
import time
import subprocess
#import pygetwindow as gw
import pyautogui

def find_shell_windows():
    if os.name == 'nt':  # Windows
        import win32gui
        import win32process
        import psutil

        def get_window_title(hwnd):
            return win32gui.GetWindowText(hwnd)

        def get_window_class_name(hwnd):
            return win32gui.GetClassName(hwnd)

        def get_process_name(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                return proc.name()
            except psutil.NoSuchProcess:
                return None

        def is_shell_window(hwnd):
            title = get_window_title(hwnd).lower()
            class_name = get_window_class_name(hwnd).lower()
            process_name = get_process_name(hwnd).lower() if get_process_name(hwnd) else ""
            shell_keywords = [
                'command prompt', 'powershell', 'git bash', 'bash', 'terminal', 'cmd', 'mintty'
            ]
            shell_processes = ['cmd.exe', 'powershell.exe', 'bash.exe', 'mintty.exe']
            return any(keyword in title or keyword in class_name or process_name in shell_processes for keyword in shell_keywords)

        shell_windows = []
        def callback(hwnd, extra):
            if is_shell_window(hwnd):
                shell_windows.append(hwnd)
        win32gui.EnumWindows(callback, None)
        return shell_windows

    elif os.name == 'posix':  # Unix/Linux/Mac
        if 'darwin' in os.sys.platform:  # macOS
            try:
                output = subprocess.check_output(['osascript', '-e', 'tell application "System Events" to get the name of every window of (every process whose name is "Terminal")']).decode('utf-8')
                windows = [line.strip() for line in output.split(',')]
                return windows
            except subprocess.CalledProcessError:
                return []
        else:  # Linux
            try:
                output = subprocess.check_output(['wmctrl', '-l']).decode('utf-8')
                windows = [line for line in output.splitlines() if 'Terminal' in line]
                return windows
            except subprocess.CalledProcessError:
                return []

def activate_window(window, debug=False):
    if os.name == 'nt':  # Windows
        import win32gui
        import win32api
        import win32con

        print(f"Bringing window to foreground: {window}") if debug else None
        if win32gui.IsIconic(window):
            print("Window is minimized, restoring it.") if debug else None
            win32gui.ShowWindow(window, win32con.SW_RESTORE)
        elif not win32gui.IsWindowVisible(window):
            print("Window is hidden, showing it.") if debug else None
            win32gui.ShowWindow(window, win32con.SW_SHOW)

        pyautogui.press("alt")
        win32gui.SetForegroundWindow(window)
        time.sleep(0.2)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.2)
    elif os.name == 'posix':
        if 'darwin' in os.sys.platform:  # macOS
            script = f'''
            tell application "Terminal"
                do script ""
                activate
            end tell
            tell application "System Events"
                tell process "Terminal"
                    set frontmost to true
                    perform action "AXRaise" of window "{window}"
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script])
        else:  # Linux
            subprocess.run(['xdotool', 'windowactivate', window])

def send_command(command):
    if os.name == 'nt' or os.name == 'posix':  # Windows
        pyautogui.typewrite(command)
        time.sleep(0.2)
        pyautogui.press('enter')
    elif os.name == 'posix':
        if 'darwin' in os.sys.platform:  # macOS
            script = f'''
            tell application "Terminal"
                do script "{command}" in front window
            end tell
            '''
            subprocess.run(['osascript', '-e', script])
        else:  # Linux
            subprocess.run(['xdotool', 'type', '--delay', '1', command])
            subprocess.run(['xdotool', 'key', 'Return'])

def change_directory_in_shell(path, debug=False):
    shell_windows = find_shell_windows()
    if shell_windows:
        # Activate the most recently active shell window
        window = shell_windows[0]
        print(f"Activating window: {window}") if debug else None
        activate_window(window, debug)
        print(f"Sending command: cd {path}") if debug else None
        pyautogui.click()  # Click to focus the terminal window
        time.sleep(0.2)
        send_command(f"cd '{path}'")
    else:
        print("No active shell windows found.")

def open_new_terminal(path, profile):
    """
    Opens a new terminal window and changes the directory to the specified path.
    """
    if os.name == 'nt':  # Windows
        if profile == 'cmd':
            subprocess.Popen(['cmd.exe', '/K', f'cd /d {path}'], creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif profile == 'powershell':
            subprocess.Popen(['powershell.exe', '-NoExit', '-Command', f'cd "{path}"'], creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif profile == 'bash':
            bash_path = r'C:\Program Files\Git\git-bash.exe'  # Hardcoded path
            subprocess.Popen([bash_path, '-c', f'cd "{path}" && exec bash'], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            raise ValueError("Unsupported profile")
    elif os.name == 'posix':
        if 'darwin' in os.sys.platform:  # macOS
            script = f'''
            tell application "Terminal"
                do script "cd {path}"
                activate
            end tell
            '''
            subprocess.run(['osascript', '-e', script])
        else:  # Linux
            subprocess.run(['gnome-terminal', '--', 'bash', '-c', f'cd {path}; exec bash'])

