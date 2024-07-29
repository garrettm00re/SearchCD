import os
import json
import argparse
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from concurrent.futures import ThreadPoolExecutor, as_completed  ##parallelization allows for quick tree-building
from graphviz import Digraph
from filelock import FileLock
import objgraph ## this will help identify memory leaks
import threading ### threading, threading_local ??? what do these do

class TreeEventHandler(FileSystemEventHandler):
    def __init__(self, json_file, graph_file, lock_file, visualize):
        self.json_file = json_file
        self.graph_file = graph_file
        self.visualize = visualize
        self.lock_file = lock_file
        print('initializing the tree event handler')

    ### EVENT HANDLERS

    def on_created(self, event):
        if event.is_directory:
            print('========')
            print('created', event)
            self.update_json_tree('add', src = event.src_path.split(os.sep))

    def on_deleted(self, event):
        """
        event.is_directory is broken for folder deletion events (sort of makes sense as folders are no longer anything if they've been deleted)
        thus, we default to the JSON tree to check if it is a directory.
        """
        self.update_json_tree('remove', src = event.src_path.split(os.sep), event = event)

    def on_moved(self, event): ## inefficient for renaming operations, probably doesn't matter much though
        if event.is_directory:
            print('========')
            print('moved', event)
            self.update_json_tree('moved', src = event.src_path.split(os.sep), dest = event.dest_path.split(os.sep))

    ### CORE LOGIC

    def update_json_tree(self, action, event = None, src = None, dest = None):
        """
        
        """
        tree = read_json_tree()
        tree, updated = self.modify_python_tree(tree, src, action, dest)
        if updated:
            if event and action == 'remove': ## here just for consistency in looking from the terminal
                print('deleted', event)
            print('TREE UPDATED', action)
            print('========')
        write_json_tree(tree)
        if self.visualize:
            graph = create_graph(tree)
            graph.render(self.graph_file, format='svg', view = True)

    def modify_python_tree(self, tree, src, action, dest = None):
        """
        Modifies the file tree for the appropriate action. Important nuance: this function is responsible
        for checking if a remove operation is necessary
        """  
        #print(tree["name"] + 'NAME', str(src) + "  SRC")  
        src = self.trim_tree(tree, src)
        if dest:
            dest = self.trim_tree(tree, dest)
        st = self.set_subtree(tree, src)
        updated = True
        if action == 'add':
            newPath = tree["path"] #
            for p, k in enumerate(src):
                if p == 0:
                    continue
                newPath += "\\" + k
            new = {"name": src[-1], "path": newPath, "children": []} #os.path.join(tree["path"], src_mod[1:])
            st["children"].append(new)

        elif action == "remove":
            if src[-1] in st["children"]:
                st["children"] = [c for c in st["children"] if not c["name"] == src[-1]]
            else:
                updated = False

        elif action == "moved":
            toMove = next((c for c in st["children"] if c["name"] == src[-1]), None) # this is the subtree that needs moving, could easily delete it now but ...
            st["children"] = [c for c in st["children"] if c and c["name"] != src[-1]] if st["children"] != None else []
            toMove["name"] = dest[-1] # this is the rename
            stMove = self.set_subtree(tree, dest)
            stMove["children"].append(toMove)
        return tree, updated
    
    ### UTILITY METHODS

    def directory_check(self, path):
        tree = read_json_tree(self.tree)
        src_path_parts = self.trim_tree(tree, path)
        st = self.set_subtree(tree, src_path_parts)
        if src_path_parts[-1] in st["children"]:
            return True

    def set_subtree(self, tree, parts):
        st = tree
        for i, p in enumerate(parts):
            for c in st["children"]:
                if c["name"] == p and not i == len(parts) - 1:
                    st = c
                    break
            if i == len(parts) - 1:
                return st
            
    def trim_tree(self, tree, parts): #does not actually trim a tree
        for i, p in enumerate(parts):
            if p == tree["name"]:
                return parts[i + 1:]
### FILESYSTEM EVENT DETECTION AND HANDLING

def monitor_directory(path, json_file, graph_file, lock_file, visualize):
    print('ok, monitoring directory changes and mutating tree')
    event_handler = TreeEventHandler(json_file, graph_file, lock_file, visualize)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(5)  # Keep the script running, experiment with different sleep settings
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

### TREE CREATION
kbi, ct = False, 0
def build_tree(path, debug = True): ### do UNIX systems not have a file TREE but instead a cyclic file GRAPH ?????????????
    """
    Parallelized function for building the tree from a base path. This tree will be read into json format for easy interconversion between storage and variable
    """
    #### TODO ####
    #figure out cause of "can't start new thread" error on UNIX systems --> does it actually impact anything?
    #figure out why max_workers does not correlate with # threads in an obvious way
    # figure out how to do the keyboard interrupt thing
    #message shreyas, distributed computing is pretty cool
    ### what is an unbound variable!!!!!!
    visited = set()
    print_lock = threading.Lock()
    kbi_event = threading.Event()
    def explorer(path):
        global ct, kbi
        tree = {"name": os.path.basename(path), "path": path, "children": []}
        if tree["name"] is None:
            print(path)
        #nonlocal ct ## why do I need this
        if ct % 10000 == 0 and debug: ##debugging
            with print_lock:
                print('=====================')
                print(f"kbi: {kbi_event.is_set()}")
                print(f'Number of nodes that have finished executing: {ct}')
                print(f"active threading count: {threading.active_count()}")
                print('=====================')
        if kbi_event.is_set():# #short circuit if keyboard interrupt is detected in any thread (doesn't work?)
            if debug:
                print('kbi detected, quitting execution')
            return
        try:
            mw = 1 + len(os.listdir(path))# * 2## max workers
            with ThreadPoolExecutor(max_workers=mw, thread_name_prefix = 'tree-build') as executor:  # Adjust max_workers as needed
                futures = []
                for entry in os.listdir(path):
                    full_path = os.path.join(path, entry)
                    if full_path not in visited and os.path.exists(full_path) and os.path.isdir(full_path) and not os.path.islink(full_path): ## handles symlinks ## may be data races with this
                        futures.append(executor.submit(explorer, full_path)) 
                        visited.add(full_path) ## handles symlinks
                for future in as_completed(futures):
                    try:
                        tree["children"].append(future.result())
                    except PermissionError:
                        pass
                    except Exception as e:
                        pass
        except PermissionError:
            pass
        except KeyboardInterrupt:
            kbi_event.set()
            if debug:
                print('kbi detected')
            raise
        except Exception as e:
            print(f"Error accessing {path}: {e}") if debug else None
        ct = ct + 1 
        return tree
    return explorer(path)

def add_nodes(graph, tree):
    """
    visualizing the tree using graphviz
    """
    node_id = str(hash(tree["path"].replace("\\", "/")))
    graph.node(node_id, label=tree["name"], fontsize="10")
    for child in tree["children"]:
        child_id = str(hash(child["path"].replace("\\", "/")))
        graph.node(child_id, label=child["name"], fontsize="10")
        graph.edge(node_id, child_id)
        add_nodes(graph, child)

### TREE VISUALIZATION

def create_graph(tree):
    graph = Digraph(comment='Directory Tree', format='svg')
    graph.attr(size="100,1000!")
    graph.attr(overlap="scale")
    graph.attr(splines="true")
    graph.attr(rankdir="LR")
    add_nodes(graph, tree)
    return graph

def read_json_tree():
    lock = FileLock(lock_file)
    with lock:
        with open(json_file, 'r') as f:
            tree = json.load(f)
    return tree

def write_json_tree(tree):
    lock = FileLock(lock_file)
    with lock:
        with open(json_file, 'w') as f:
            json.dump(tree, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Monitor directory and update tree in real-time.')
    parser.add_argument('-v', '--visualization', action='store_true', help='Enable visualization')
    parser.add_argument('-b', '--build', action='store_true', help='Build the tree on startup')
    args = parser.parse_args()
    if args.build:
        directory_tree = build_tree(root)
        lock = FileLock(lock_file)
        with lock:
            with open(json_file, "w") as f:
                json.dump(directory_tree, f, indent=2)
        with open('tree_built.info', 'w') as f:
            f.write('True') ## communicates to search loop that it's time to update the trie
    if args.visualization:
        directory_tree = read_json_tree() if not args.build else directory_tree
        graph = create_graph(directory_tree)
        graph.render(graph_file, format='svg', view = True)
    del directory_tree
    monitor_directory(root, json_file, graph_file, lock_file, args.visualization)
### global
r = os.path.abspath(os.getcwd())
root = r.split(os.sep)[0] + '\\\\' if os.name == 'nt' else '/'
print(f"Executing program from root: {root}")
#print(root, r.split(os.sep)[0])
#root = ro #= r"C:\\"
with open("JSON-Files/AlgorithmAttributes.json", 'r') as f:
    algoAttr = json.load(f)
json_file = algoAttr["tree"]
lock_file = algoAttr["tree.lock"]
graph_file = algoAttr["tree graph"]

if __name__ == "__main__":
    main()