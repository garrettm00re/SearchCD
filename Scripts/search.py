#from build_tree import load_tree_from_json
import json
import keyboard
import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox
import subprocess
import os
from graphviz import Digraph
from filelock import FileLock
from tkinter import simpledialog, messagebox, Listbox, Label, Scrollbar, VERTICAL, RIGHT, Y, BOTH, SINGLE
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
        #parent_path = search_folders(trie, parent, max_results=1, parent = None)
        #print(parent, [path.lower().split('\\') for path in ts])
        ts = {path : edits for path, edits in ts.items() if parent.lower() in path.lower().split('\\')} #prune by parent folder
        #return ts_pruned
    ts_with_edits = sorted([(k, v) for k, v in ts.items()], key = lambda x: x[1]) ## sort the results by number of edits used
    ts_top_results = [result[0] for i, result in enumerate(ts_with_edits) if i < max_results]
    return ts_top_results

#useless as of now
#def prune_trie_search(trie_search,  max_results = 5) -> list:
#    #should show only the most relevant search results
#    ts_with_edits = sorted([(k, v) for k, v in trie_search.items()], key = lambda x: x[1]) ## sort the results by number of edits used
#    ts_pruned = []
#    ts_top_results = [result[0] for i, result in enumerate(ts_with_edits) if i < max_number_results]


### Trie visualization (use for small directory tree/trie only)
def visualize_trie(trie):
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
    width = round((400 + len(max(options, key = len)))/2) ## an average between these is probably better
    top.geometry(f"{width}x{window_height}") #

    top.protocol("WM_DELETE_WINDOW", root.quit)
    root.wait_window(top)
    return selection

# Function to handle the hotkey action
def on_hotkey():
    root = tk.Tk()
    root.withdraw()
    folder_name = simpledialog.askstring("Input", "Enter folder name to search for:", parent=root)
    parent_folder = simpledialog.askstring("Input", "Enter parent folder to search within (optional):", parent=root)
    if folder_name:
        results = search_folders(trie, folder_name, parent = parent_folder, max_edits = 3)
        if results:
            selected_path = prompt_folder_selection(results)
            if selected_path:
                profile = simpledialog.askstring("Profile", "Enter terminal profile (cmd, powershell, bash):", parent=root)
                if profile:
                    choice = messagebox.askquestion("Navigate", "Do you want to open a new terminal window?", icon='question')
                    if choice == 'yes':
                        open_new_terminal(selected_path, profile)
                    else:
                        change_directory(selected_path, profile)
        else:
            messagebox.showinfo("Search Results", "No matching folders found.")

    root.destroy()

# Function to change directory in the active terminal
def change_directory(path, profile = 'cmd'):
    if os.name == 'nt':  # Windows
        if profile == 'cmd':
            subprocess.run(['cmd', '/K', f'cd /d {path}'])
        elif profile == 'powershell':
            subprocess.run(['powershell', '-NoExit', f'cd {path}'])
        elif profile == 'bash':
            #bash_path = r"C:\Program Files\Git\bin\bash.exe"
            bash_path = r'C:\Program Files\Git\git-bash.exe'  
            if os.path.exists(bash_path):
                try:
                    subprocess.run(['wsl', '--list'], check=True)
                    # Use WSL to open a bash shell in the specified directory
                    #subprocess.Popen(['wsl', 'bash', '-c', f'cd {path} && exec bash'])
                except subprocess.CalledProcessError:
                    print("WSL is not installed. Please install WSL and try again.")
                #print('hello')
                #subprocess.Popen([bash_path, '--login', '-i', '-c', f'cd "{path}" && exec bash'])
                #subprocess.run([bash_path, '-c', f'cd {path}; exec bash'], shell=True)
                #subprocess.Popen([bash_path, '-c', f'cd "{path}" && exec bash'])
            else:
                messagebox.showerror("Error", "Git Bash is not installed.")
        else:
            raise ValueError("Unsupported profile")
    else:  # Unix/Linux/Mac
        subprocess.run(['bash', '-c', f'cd {path} && exec $SHELL'])

# Function to open a new terminal window
def open_new_terminal(path, profile):
    if os.name == 'nt':  # Windows
        if profile == 'cmd':
            subprocess.run(['start', 'cmd', '/K', f'cd /d {path}'], shell=True)
        elif profile == 'powershell':
            subprocess.run(['powershell', '-NoExit', '-Command', f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd {path}"'], shell=True)
        elif profile == 'bash':
            bash_path = r'C:\Program Files\Git\git-bash.exe'
            subprocess.Popen([bash_path, '-c', f'cd "{path}" && exec bash'])
            #subprocess.run([bash_path, '-c', f'cd {path}; exec bash'], shell=True)
            #subprocess.Popen(['wsl', 'bash', '-c', f'cd {path} && exec bash'])
            #subprocess.run(['wsl', '-e', 'bash', '-c', f'cd {path}; exec bash'], shell=True)
        else:
            raise ValueError("Unsupported profile")
    else:  # Unix/Linux/Mac
        subprocess.run(['gnome-terminal', '--', 'bash', '-c', f'cd {path}; exec bash'])

#######
json_file = 'directory_tree.json'
graph_file = 'directory_tree'
lock_file = 'directory_tree.json.lock'

#trie_json = 'trie.json'
#trie_graphviz = 'trie'
#trie_lock = 'trie.json.lock'


if __name__ == "__main__":
    print('hello')
    # Load the directory tree and build the Trie
    parser = argparse.ArgumentParser(description='Monitor directory and update tree in real-time.')
    parser.add_argument('-v', '--visualization', action='store_true', help='Enable visualization')
    args = parser.parse_args()
    ###
    with open("JSON-Files/AlgorithmAttributes.json", 'r') as f:
        algoAttr = json.load(f)
    json_tree = algoAttr["tree"] 
    tree_lock = algoAttr["tree.lock"]
    json_trie = algoAttr["trie"]
    trie_lock = algoAttr["trie.lock"]
    ####
    tree = read_json_tree()
    trie = Trie()
    build_trie_from_tree(tree, trie)
    if args.visualization:
        graph = visualize_trie(trie)
        graph.render('../Visualizations/trie', format='png', view=True)
    # Set up the hotkey (Ctrl+G)
    keyboard.add_hotkey('ctrl+g', on_hotkey) # if ctrl g is pressed -> call on_hotkey()
    print('ready for action')
    keyboard.wait('esc') # Keep the script running