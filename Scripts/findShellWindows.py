import time
import pygetwindow as gw
import pyautogui
import win32gui
import win32process
import win32api
import win32con
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

def find_shell_windows():
    shell_windows = []
    def callback(hwnd, extra):
        if is_shell_window(hwnd):
            shell_windows.append(hwnd)
    win32gui.EnumWindows(callback, None)
    return shell_windows

def activate_window(hwnd, debug = False): 
    print(f"Bringing window to foreground: {hwnd}") if debug else None
    # Ensure the window is not minimized or hidden
    if win32gui.IsIconic(hwnd):
        print("Window is minimized, restoring it.") if debug else None
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    elif not win32gui.IsWindowVisible(hwnd):
        print("Window is hidden, showing it.") if debug else None
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

    pyautogui.press("alt") ################# WHY THE FUCK IS THIS NECESSARY
    win32gui.SetForegroundWindow(hwnd) 
    time.sleep(0.2)
    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0) # Force the window to the foreground if necessary
    time.sleep(0.2)

def change_directory_in_shell(path, debug = False):
    shell_windows = find_shell_windows()
    if shell_windows:
        # Activate the most recently active shell window
        hwnd = shell_windows[0]
        window_title = get_window_title(hwnd)
        window_class = get_window_class_name(hwnd)
        process_name = get_process_name(hwnd)
        print(f"Activating window: Title='{window_title}', Class='{window_class}', Process='{process_name}'") if debug else None
        activate_window(hwnd)
        print(f"Sending command: cd {path}") if debug else None
        pyautogui.click() ## no idea where this will click, likely in the center of the screen which is obviously problematic. need to get window dimensions
        time.sleep(0.2)
        pyautogui.typewrite(f"cd '{path}'") #removed /d
        time.sleep(0.2)
        pyautogui.press('enter')
        time.sleep(0.2)
    else:
        print("No active shell windows found.")
