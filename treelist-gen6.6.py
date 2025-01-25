import subprocess
import json
from tqdm import tqdm
import argparse
import re
import os

def run_rclone_lsjson(remote_path):
    """Run rclone lsjson on a remote path and return the parsed JSON output."""
    command = ["rclone", "lsjson", remote_path, "--recursive"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Error running rclone: {result.stderr}")
    return json.loads(result.stdout)

def group_by_depth_and_sum_size(files, depth):
    """Group files by directory at specified depth and sum sizes."""
    grouped = {}
    for file in files:
        if file['IsDir']:
            continue
            
        path_parts = file['Path'].split('/')
        dir_path = '/'.join(path_parts[:depth]) if depth > 0 else file['Path']
        
        if dir_path not in grouped:
            grouped[dir_path] = 0
        grouped[dir_path] += file['Size']
    return grouped

def convert_size(size_bytes, unit):
    """Convert size from bytes to specified unit."""
    units = {
        "kb": 1024,
        "mb": 1024**2,
        "gb": 1024**3
    }
    return size_bytes / units.get(unit.lower(), 1)

def save_grouped_data(data, output_file, remote_name, unit):
    """Save grouped directory data to JSON."""
    result = {
        "remote": remote_name,
        "unit": unit,
        "directories": data
    }
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=4)

def save_files_data(files, output_file, remote_name, unit):
    """Save raw file list data for tree generation."""
    result = {
        "remote": remote_name,
        "unit": unit,
        "files": files
    }
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=4)

def build_tree_structure(entries):
    """Build nested tree structure from rclone lsjson output."""
    tree = {}
    for entry in entries:
        path = entry['Path'].rstrip('/')
        is_dir = entry['IsDir']
        parts = path.split('/') if path else []
        current = tree
        size = entry['Size'] if not is_dir else 0

        for i, part in enumerate(parts):
            if not part:
                continue
                
            if part not in current:
                current[part] = {
                    '_size': 0,
                    '_children': {},
                    '_isdir': False
                }
            
            node = current[part]
            if i == len(parts) - 1:  # Leaf node
                if is_dir:
                    node['_isdir'] = True
                else:
                    node['_size'] += size
            else:  # Directory node
                if not isinstance(node, dict):
                    current[part] = {
                        '_size': node,
                        '_children': {},
                        '_isdir': False
                    }
                    node = current[part]
                
                node['_size'] += size
                current = node['_children']
    
    def clean_node(node):
        cleaned = {}
        for k, v in node.items():
            if isinstance(v, dict) and '_children' in v:
                cleaned[k] = clean_node(v['_children'])
                cleaned[k]['_size'] = v['_size']
                cleaned[k]['_isdir'] = v['_isdir']
            else:
                cleaned[k] = v
        return cleaned
    
    return clean_node(tree)

def extract_number(name):
    """Extract leading numbers for numeric sorting."""
    match = re.match(r'^(\d+)', name)
    return int(match.group(1)) if match else float('inf')

def generate_tree_html(node, current_depth=1):
    """Generate HTML tree with numeric sorting at first level."""
    html = '<ul>'
    dirs = []
    files = []

    for name, value in node.items():
        if name in ['_size', '_isdir']:
            continue
        
        if isinstance(value, dict) and '_isdir' in value:
            if value['_isdir']:
                dirs.append((name, value))
            else:
                files.append((name, value))
        else:
            files.append((name, value))

    # Sort first-level directories numerically
    if current_depth == 1:
        dirs.sort(key=lambda x: extract_number(x[0]))
    else:
        dirs.sort(key=lambda x: x[0].lower())
    
    # Sort files alphabetically
    files.sort(key=lambda x: x[0].lower())

    # Add directories
    for name, children in dirs:
        html += f'<li><span class="folder">{name}</span>{generate_tree_html(children, current_depth + 1)}</li>'

    # Add files
    for name, value in files:
        html += f'<li><span class="file">{name}</span></li>'

    html += '</ul>'
    return html

def generate_html_from_json(json_file):
    """Generate HTML tree from JSON file."""
    with open("template.html", "r") as template_file:
        html_template = template_file.read()

    with open(json_file, "r") as f:
        json_data = json.load(f)
    
    if 'files' not in json_data:
        raise ValueError("JSON missing 'files' key. Use --generate-tree flag.")
    
    tree = build_tree_structure(json_data['files'])
    tree_html = generate_tree_html(tree)

    with open("treelist.html", "w") as output_file:
        output_file.write(html_template.format(tree_structure=tree_html))

def main():
    parser = argparse.ArgumentParser(description="Analyze remote storage and generate reports")
    parser.add_argument("remote", help="Remote path (e.g., 'remote:bucket/path')")
    parser.add_argument("--output", default="output.json", help="Output JSON file name")
    parser.add_argument("--depth", type=int, default=1, help="Grouping depth for size analysis")
    parser.add_argument("--unit", default="bytes", choices=["bytes", "kb", "mb", "gb"], help="Size unit")
    parser.add_argument("--generate-tree", action="store_true", help="Generate HTML directory tree")
    args = parser.parse_args()

    remote_name = args.remote.split(':')[0]
    print(f"Fetching data from {args.remote}...")
    files = run_rclone_lsjson(args.remote)

    if args.generate_tree:
        print("Saving raw file data...")
        save_files_data(files, args.output, remote_name, args.unit)
    else:
        print(f"Analyzing directory structure at depth {args.depth}...")
        grouped = group_by_depth_and_sum_size(files, args.depth)
        converted = {k: convert_size(v, args.unit) for k, v in grouped.items()}
        sorted_data = dict(sorted(converted.items(), key=lambda x: x[0]))
        
        print(f"\nDirectory sizes ({args.unit}):")
        for path, size in sorted_data.items():
            print(f"{path}: {size:.2f}")
        
        save_grouped_data(sorted_data, args.output, remote_name, args.unit)

    if args.generate_tree:
        print("Generating HTML tree...")
        generate_html_from_json(args.output)
        print("Tree saved to treelist.html")

if __name__ == "__main__":
    main()
