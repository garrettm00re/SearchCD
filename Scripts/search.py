#read/write json
import json
#hotkey setup
import keyboard 
#user interface
import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox
from tkinter import simpledialog, messagebox, Listbox, Label, Scrollbar, VERTICAL, RIGHT, Y, BOTH, SINGLE
from tkinter import ttk, messagebox
### opening terminal windows // changing directories
import subprocess
from findShellWindows import change_directory_in_shell
# generally useful
import os
import time
#ensure it's not possible for 2+ threads to read/write storage files
from filelock import FileLock
#visualization
from graphviz import Digraph
import argparse

def read_json_tree():
    # Load the directory tree from the JSON file
    lock = FileLock(tree_lock)
    with lock:
        with open(json_tree, 'r') as f:
            tree = json.load(f)
    return tree

def exact_search(tree, folder, parent = 'C:'):
    if tree['name'] == folder and (parent + '/' + folder) in tree["path"]:
        return tree["path"]
    for c in tree["children"]:
        est = exact_search(c, folder, parent)
        if est:
            return est
    return

def subtree(tree, folder):
    #DFS procedure that returns the subtree(s) with root = folder
    stack = [tree]
    results = []
    while stack:
        tree = stack.pop()
        if tree['name'] == folder:
            results.append(tree)
        for c in tree["children"]:
            stack.append(c)
    return results

#############################

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.path = []

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word, path):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.path.append(path)

    def search(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                return None
            node = node.children[char]
        return node if node.is_end_of_word else None

    def search_fuzzy(self, word, max_edits=3): #### seemingly returns duplicates
        #####################################################
        #node.path is now a list, changes must be made
        #####################################################
        print(word)
        def search_recursive(node, word, idx, edits):
            if edits > max_edits:
                return
            if idx == len(word):
                if node.is_end_of_word and edits <= max_edits:
                    for p in node.path:
                        results[p] = edits # no duplicates this way
                return
            if word[idx] in node.children:
                search_recursive(node.children[word[idx]], word, idx + 1, edits) # exact match 
            for char in node.children:
                search_recursive(node.children[char], word, idx + 1, edits + 1) #replace word[idx] with char (cost = 1)
                search_recursive(node.children[char], word, idx, edits + 1) #insert char into word (cost = 1)
            search_recursive(node, word, idx + 1, edits + 1) #missing character
        results = {} # (path, min edit distance)
        search_recursive(self.root, word, 0, 0)
        return results

### Trie Construction
def build_trie_from_tree(tree, trie):
    # Build the Trie from the directory tree
    trie.insert(tree["name"], tree["path"])
    for child in tree["children"]:
        build_trie_from_tree(child, trie)

### High level search algorithm
def search_folders(trie, name, max_edits = 3, max_results = 5, parent=None): ##trie search
    ts = trie.search_fuzzy(name, max_edits = max_edits)
    if parent:
        ts = {path : edits for path, edits in ts.items() if parent.lower() in path.lower().split('\\')} #prune by parent folder
    ts_with_edits = sorted([(k, v) for k, v in ts.items()], key = lambda x: x[1]) ## sort the results by number of edits used
    ts_top_results = [result[0] for i, result in enumerate(ts_with_edits) if i < max_results]
    return ts_top_results

### Trie visualization (use for small directory tree/trie only)
def visualize_trie(trie):
    """
    Visualize the trie as a png image. Depending on the computer, this file will likely be super large
    so it's best to split the file (though this method does not do that)
    """
    def add_nodes(graph, node, prefix):
        for char, child in node.children.items():
            node_name = prefix + char
            graph.node(node_name, label=char)
            graph.edge(prefix, node_name)
            add_nodes(graph, child, node_name)
        if node.is_end_of_word:
            graph.node(prefix, style='filled', fillcolor='lightblue')

    graph = Digraph(comment='Trie Visualization')
    graph.node('root', label='Root')
    add_nodes(graph, trie.root, 'root')
    graph.render('trie_visualization', format='png', view=True)
    return graph

# Function to prompt user to select a folder from a list
def prompt_folder_selection(options):
    """
    User interface for the folder selection menu (search result selection)
    """
    root = tk.Tk()
    root.withdraw()
    selection = None
    def on_select(event):
        nonlocal selection
        selection = listbox.get(listbox.curselection())
        top.destroy()
    top = tk.Toplevel(root)
    top.title("Select Folder")
    # Header
    label = Label(top, text="Search Results", font=('Arial', 14))
    label.pack()
    # Listbox with scrollbar
    frame = tk.Frame(top)
    frame.pack(fill=BOTH, expand=True)
    scrollbar = Scrollbar(frame, orient=VERTICAL)
    listbox = Listbox(frame, selectmode=SINGLE, yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    listbox.pack(fill=BOTH, expand=True)
    for option in options:
        listbox.insert(tk.END, option)
    listbox.bind('<<ListboxSelect>>', on_select)
    # Adjust window size based on the number of items
    num_items = len(options)
    window_height = min(num_items * 50, 200)
    width = round((600 + 10*(len(max(options, key = len)) - len(min(options, key = len))))/2) #
    top.geometry(f"{width}x{window_height}") #
    top.protocol("WM_DELETE_WINDOW", root.quit)
    root.wait_window(top)
    return selection

def select_profile():
    """
    In case user wants to select a shell
    """
    def on_select(): # Function to handle selection
        if selected_profile.get():
            top.quit()
        else:
            messagebox.showerror("Error", "Please select a profile")
    def update_profile(value):
        selected_profile.set(value)
        print(f"Selected: {selected_profile.get()}") 

    root = tk.Tk() # Create the main window but keep it hidden
    root.withdraw()
    top = tk.Toplevel(root) # Create the top-level window
    top.title("Select Terminal Profile")
    top.geometry("300x200")
    selected_profile = tk.StringVar(value="")  # Variable to store the selected profile
    profiles = [("Command Prompt", "cmd"), ("PowerShell", "powershell"), ("Bash", "bash")]
    for text, value in profiles: # Create radio buttons for each profile option
        ttk.Radiobutton(top, text=text, value=value, command =lambda v=value: update_profile(v)).pack(pady=5)
    ttk.Button(top, text="Select", command=on_select).pack(pady=20)# Create the Select button
    top.protocol("WM_DELETE_WINDOW", top.quit)  # Handle window close
    top.mainloop()
    profile = selected_profile.get()
    root.destroy() # Destroy all tkinter windows
    return profile


def on_hotkey():
    """
    Function to handle hotkey action. This is the UI.
    """
    root = tk.Tk()
    root.withdraw()
    folder_name = simpledialog.askstring("Input", "Enter folder name to search for:", parent=root)
    parent_folder = simpledialog.askstring("Input", "Enter parent folder to search within (optional):", parent=root)
    if folder_name:
        results = search_folders(trie, folder_name, parent = parent_folder, max_edits = 3)
        if results:
            selected_path = prompt_folder_selection(results)
            if selected_path:
                choice = messagebox.askquestion("Navigate", "Do you want to open a new terminal window?", icon='question')
                if choice == 'yes':
                    profile = select_profile()
                    print(profile, 'p')
                    #profile = simpledialog.askstring("Profile", "Enter terminal profile (cmd, powershell, bash):", parent=root)
                    if profile:
                        open_new_terminal(selected_path, profile)
                else:
                    change_directory_in_shell(selected_path)
        else:
            messagebox.showinfo("Search Results", "No matching folders found.")
    root.destroy()

def open_new_terminal(path, profile):
    """
    Does as described, Unix/Mac support likely doesn't work, haven't been able to test/confirm.
    """
    if os.name == 'nt':  # Windows
        if profile == 'cmd':
            subprocess.run(['start', 'cmd', '/K', f'cd /d {path}'], shell=True)
        elif profile == 'powershell':
            subprocess.run(['powershell', '-NoExit', '-Command', f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd {path}"'], shell=True)
        elif profile == 'bash':
            bash_path = r'C:\Program Files\Git\git-bash.exe' ### hardcoded, should ask for user input
            subprocess.Popen([bash_path, '-c', f'cd "{path}" && exec bash'])
        else:
            raise ValueError("Unsupported profile")
    else:  # Unix/Linux/Mac
        subprocess.run(['gnome-terminal', '--', 'bash', '-c', f'cd {path}; exec bash'])

### UTILITY
def get_attr_and_methods(obj):
    """
    Get a list of all attributes and methods of the object
    """
    attributes_and_methods = dir(obj)
    attributes = []
    methods = []
    for name in attributes_and_methods:
        attr = getattr(obj, name)
        if callable(attr):
            methods.append(name)
        else:
            attributes.append(name)
    return f"ATTRIBUTES: \n{attributes} \n\nMETHODS: \n {methods}"

if __name__ == "__main__":
    """
    MAIN "FUNCTION" (making this a function would affect global scope which could be combated with use of nonlocal)
    builds the trie for searching from the directory tree
    listens for the hotkey
    """
    parser = argparse.ArgumentParser(description='Monitor directory and update tree in real-time.')
    parser.add_argument('-v', '--visualization', action='store_true', help='Enable visualization') ## add -v for visualization
    args = parser.parse_args()
    with open("./JSON-Files/AlgorithmAttributes.json", 'r') as f:
        algoAttr = json.load(f)
    json_tree = algoAttr["tree"] ##load file names...
    tree_lock = algoAttr["tree.lock"]
    json_trie = algoAttr["trie"]
    trie_lock = algoAttr["trie.lock"]
    tree = read_json_tree()
    trie = Trie()
    build_trie_from_tree(tree, trie)
    if args.visualization:
        graph = visualize_trie(trie)
        graph.render('../Visualizations/trie', format='png', view=True)
    keyboard.add_hotkey('ctrl+g', on_hotkey) # if ctrl g is pressed -> call on_hotkey()
    print('ready for action')
    keyboard.wait('esc') # Keep the script running

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
####################### DEPRECATED METHODS #######################
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
def change_directory(path, profile='cmd'):
    """
    Function to change directory in the active terminal
    DOES NOT WORK PROPERLY
    """
    print(path)
    if profile == 'cmd':
        os.system(f'cd /d {path}')
    elif profile == 'powershell':
        subprocess.run(['powershell', '-NoExit', '-Command', f'Set-Location -Path {path}'], shell=True)
    elif profile == 'bash':
        bash_path = r'C:\Program Files\Git\git-bash.exe'
        if os.path.exists(bash_path):
            subprocess.run([bash_path, '-c', f'cd {path}; exec bash'], shell=True)
        else:
            print("Git Bash is not installed.")
    else:
        raise ValueError("Unsupported profile")
    
def is_shell_window(window):
    """
    DOES NOT WORK PROPERLY, the title attr of windows objects returned by pygetwindow is not the best
    """
    time.sleep(0.01)
    title = window.title.lower()
    shell_keywords = ['command prompt', 'powershell', 'git bash', 'bash', 'terminal', 'cmd']
    return any(keyword in title for keyword in shell_keywords) #and window.isActive 

def find_shell_CD(path):
    """
    DOES NOT WORK PROPERLY, is_shell_window doesn't work and thus this method is broken
    """
    windows = gw.getAllWindows() # Get the list of all windows
    shell_windows = [w for w in windows if is_shell_window(w) ] #Filter the windows to get shell windows
    titles = [w.title for w in windows]
    if shell_windows:
        shell_window = shell_windows[0] 
        shell_window.activate() # Activate the most recently active shell window
        time.sleep(0.5) # wait for the window to activate
        pyautogui.typewrite(f'cd /d {path}')
        pyautogui.press('enter')
    else:
        print("No active shell windows found.")

def prune_trie_search(trie_search,  max_results = 5) -> list:
   """
   I don't even know why I made this
   """
   ts_with_edits = sorted([(k, v) for k, v in trie_search.items()], key = lambda x: x[1]) ## sort the results by number of edits used
   ts_pruned = []
   ts_top_results = [result[0] for i, result in enumerate(ts_with_edits) if i < max_results]