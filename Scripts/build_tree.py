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
        tree = read_json_tree()
        
        #src_parts = src.split(os.sep)
        #dest_parts = None
        #if action == "moved":
        #    dest_parts = dest.split(os.sep)
        
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

def build_tree(path):   
    tree = {"name": os.path.basename(path), "path": path, "children": []}
    #print(tree["name"], tree['path'])
    try:
        with ThreadPoolExecutor(max_workers=16) as executor:  # Adjust max_workers as needed
            futures = []
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    futures.append(executor.submit(build_tree, full_path))
            for future in as_completed(futures):
                try:
                    tree["children"].append(future.result())
                except PermissionError:
                    pass
                except Exception as e:
                    print(f"Error processing {full_path}: {e}")
    except PermissionError:
        pass
    except Exception as e:
        print(f"Error accessing {path}: {e}")
    return tree

def add_nodes(graph, tree):
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
        with open(json_file, "w") as f:
            json.dump(directory_tree, f, indent=2)
        del directory_tree
        if args.visualization:
            graph = create_graph(directory_tree)
            graph.render(graph_file, format='svg', view = True)

    if args.visualization:
        directory_tree = read_json_tree() if not args.build else directory_tree
        graph = create_graph(directory_tree)
        graph.render(graph_file, format='svg', view = True)

    monitor_directory(root, json_file, graph_file, lock_file, args.visualization)

root = r"C:"
with open("JSON-Files/AlgorithmAttributes.json", 'r') as f:
    algoAttr = json.load(f)
json_file = algoAttr["tree"]
lock_file = algoAttr["tree.lock"]
graph_file = algoAttr["tree graph"]

if __name__ == "__main__":
    main()