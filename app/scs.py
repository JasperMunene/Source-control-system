import sys
import zlib
import hashlib
from pathlib import Path
from typing import List
import shutil
import os
import fnmatch

def read_object(parent: Path, sha: str) -> bytes:
    """
    Reads and decompresses an object from a .scs repository based on its SHA hash.

    Args:
        parent (Path): The parent directory path where the repository is located.
        sha (str): The SHA hash of the object to retrieve. The first two characters of the
                   hash are used to determine the directory structure, and the rest of
                   the hash identifies the specific object file.

    Returns:
        bytes: The decompressed content of the object.

    Raises:
        FileNotFoundError: If the object file does not exist at the calculated path.
        zlib.error: If there is an error during decompression.
    """
    # Split the SHA hash into its 'pre' (first two characters) and 'post' (remaining characters)
    pre = sha[:2]
    post = sha[2:]

    # Construct the file path to the object using the parent directory and SHA hash
    p = parent / ".scs" / "objects" / pre / post

    # Read the raw bytes from the object file
    bs = p.read_bytes()

    # Decompress the bytes and split on the first null byte to separate the header and content
    _, content = zlib.decompress(bs).split(b"\0", maxsplit=1)

    # Return the decompressed content
    return content

def write_object(parent: Path, ty: str, content: bytes) -> str:
    """
    Writes a compressed object to a .scs repository and returns its SHA-1 hash.

    This function takes the content of an object, compresses it, and stores it in
    a specific directory structure within the repository. The object is prefixed with
    its type and content length, and its SHA-1 hash is used to determine its storage path.

    Args:
        parent (Path): The parent directory path where the repository is located.
        ty (str): The type of the object being stored (e.g., "blob", "tree").
        content (bytes): The raw content of the object to be stored.

    Returns:
        str: The SHA-1 hash of the object, used to uniquely identify it in the repository.

    Raises:
        OSError: If there is an error creating directories or writing the object file.
    """
    # Prepare the content by adding type, length, and a null byte separator
    content = ty.encode() + b" " + f"{len(content)}".encode() + b"\0" + content

    # Calculate the SHA-1 hash of the content
    hash = hashlib.sha1(content, usedforsecurity=False).hexdigest()

    # Compress the content using zlib
    compressed_content = zlib.compress(content)

    # Determine the directory structure using the first two characters of the hash
    pre = hash[:2]
    post = hash[2:]

    # Construct the file path for storing the compressed object
    p = parent / ".scs" / "objects" / pre / post

    # Ensure the target directory exists
    p.parent.mkdir(parents=True, exist_ok=True)

    # Write the compressed content to the calculated path
    p.write_bytes(compressed_content)

    # Return the SHA-1 hash of the object
    return hash

def parse_ignore_file() -> list[str]:
    """
    Parses the .scsignore file to extract patterns for ignoring files.

    This function reads the contents of the .scsignore file, which contains patterns
    for files or directories to be ignored. It filters out comments and empty lines,
    returning a list of the valid patterns.

    Returns:
        list[str]: A list of patterns (as strings) to ignore. If the .scsignore file
                   doesn't exist, an empty list is returned.

    Example:
        If the .scsignore file contains the following:
        ```
        # Ignore all .log files
        *.log

        # Ignore temp directories
        temp/
        ```
        The function will return: ['*.log', 'temp/']
    """
    # Path to the ignore file
    ignore_file = Path(".scsignore")

    # Return an empty list if the ignore file does not exist
    if not ignore_file.exists():
        return []

    # Read the file and extract non-empty, non-comment lines
    with ignore_file.open() as f:
        patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    return patterns

def is_ignored(file_path: Path, ignore_patterns: list[str]) -> bool:
    """
    Checks if a file should be ignored based on the provided ignore patterns.

    This function compares the given file path against a list of ignore patterns
    (e.g., file extensions or directory names) to determine if the file matches
    any of the patterns. If a match is found, the function returns `True`,
    indicating the file should be ignored.

    Args:
        file_path (Path): The file path to check.
        ignore_patterns (list[str]): A list of patterns to match against the file path.

    Returns:
        bool: `True` if the file matches any of the ignore patterns, otherwise `False`.

    Example:
        If the ignore patterns are ['*.log', 'temp/'] and the file path is 'temp/data.txt',
        the function will return `True` since the file path matches the 'temp/' pattern.

        Similarly, if the file path is 'error.log', the function will return `True` for
        the '*.log' pattern.
    """
    for pattern in ignore_patterns:
        # Check if the file path matches the current pattern
        if fnmatch.fnmatch(str(file_path), pattern):
            return True
    return False

def stage_file(parent: Path, path: Path) -> None:
    """
    Stages a file for version control by adding it to an index file and
    compressing its content into a blob object.

    This function checks if the file exists, if it should be ignored based
    on patterns in the `.scsignore` file, and if not, stages it by:
    1. Writing the file content to a blob object.
    2. Adding the blob object hash and file metadata to an index file.

    Args:
        parent (Path): The root directory of the repository.
        path (Path): The path of the file to be staged.

    Returns:
        None: This function does not return any value.

    Example:
        If the file exists and is not ignored, this function will create a
        corresponding entry in the index file and print a message indicating
        the file was staged.

        If the file is ignored or does not exist, it will print an appropriate
        message and not stage the file.

    Notes:
        - The file is staged as a "blob" with mode `100644` (regular file).
        - The `.scsignore` file is parsed for ignore patterns to decide if the
          file should be ignored.
    """
    # Check if the file exists
    if not path.exists():
        print(f"File {path} does not exist")
        return

    # Parse .scsignore patterns
    ignore_patterns = parse_ignore_file()
    relative_path = str(path.relative_to(parent))

    # Check if the file should be ignored
    if is_ignored(Path(relative_path), ignore_patterns):
        print(f"Ignoring {relative_path}")
        return

    # Write the blob object and get its hash
    file_hash = write_object(parent, "blob", path.read_bytes())
    mode = "100644"  # Regular file

    # Write to the index file
    index_path = parent / ".scs" / "index"
    with index_path.open("a") as index:
        index.write(f"{mode} {relative_path} {file_hash}\n")

    print(f"Staged {relative_path}")

def build_tree_from_index(parent: Path) -> str:
    """
    Builds a tree object from the entries in the index file and stores it as
    a compressed object in the repository's object store.

    This function reads the `.scs/index` file, which contains information about
    staged files, including their mode, path, and object hash. It creates a
    tree object by sorting the entries by file path and combining the metadata
    into a binary format. The tree object is then written to the repository's
    object store, and its hash is returned.

    Args:
        parent (Path): The root directory of the repository.

    Returns:
        str: The hash of the newly created tree object.

    Example:
        If the `.scs/index` file contains the following entries:
        ```
        100644 file1.txt abc123
        100644 file2.txt def456
        ```
        The function will create a tree object representing the directory structure
        and return its hash.

    Notes:
        - The `.scs/index` file must exist and contain at least one entry to
          generate a tree object.
        - The function sorts entries by file path before creating the tree object.
        - The resulting tree object is a compressed binary object, written to the
          `.scs/objects` directory.
    """
    index_path = parent / ".scs" / "index"
    entries = []

    # Check if the index file exists
    if not index_path.exists():
        print("Index file is empty or does not exist.")
        return ""

    # Read and parse the index file
    with index_path.open("r") as index:
        for line in index:
            mode, relative_path, file_hash = line.strip().split(" ")
            entries.append((mode, relative_path, file_hash))

    # Sort the entries by file path
    entries.sort(key=lambda x: x[1])  # Sort by file path

    # Build the tree content by combining file entries
    tree_content = b"".join(
        f"{mode} {path}\0".encode() + bytes.fromhex(hash)
        for mode, path, hash in entries
    )

    # Write the tree object and return its hash
    return write_object(parent, "tree", tree_content)


def clear_staging_area(parent: Path) -> None:
    """
    Clears the staging area by emptying the index file in the repository.

    This function writes an empty string to the `.scs/index` file, effectively
    removing any staged changes or file entries that were previously added to
    the staging area.

    Args:
        parent (Path): The root directory of the repository.

    Example:
        Calling this function will result in the `.scs/index` file being cleared:
        ```
        clear_staging_area(Path("/path/to/repo"))
        ```

    Notes:
        - This action will remove all staged files from the index, and
          it cannot be undone.
        - The `.scs/index` file will be left empty after the function is called.
    """
    index_path = parent / ".scs" / "index"
    index_path.write_text("")

def get_current_branch_head(parent: Path) -> Path:
    """
    Retrieves the path of the current branch's head commit file.

    This function reads the `.scs/HEAD` file to determine the reference to
    the current branch and returns the path to the file that contains the
    hash of the current commit for that branch.

    Args:
        parent (Path): The root directory of the repository.

    Returns:
        Path: The path to the current branch's head commit file.

    Example:
        Calling this function will return the path to the file that contains
        the current commit hash for the active branch:
        ```
        current_head = get_current_branch_head(Path("/path/to/repo"))
        ```

    Notes:
        - The `.scs/HEAD` file must exist and be properly formatted to return
          the correct branch reference.
        - The returned path points to the commit hash file for the current branch.
    """
    head_ref = (parent / ".scs" / "HEAD").read_text().strip().split(": ")[1]
    return parent / ".scs" / head_ref

def update_branch_head(parent: Path, commit_hash: str) -> None:
    """
    Updates the current branch's head commit to point to a new commit hash.

    This function writes the provided commit hash into the file that represents
    the head of the current branch, as specified in the `.scs/HEAD` file.

    Args:
        parent (Path): The root directory of the repository.
        commit_hash (str): The commit hash to set as the current branch's head.

    Example:
        Calling this function will update the current branch's head to the new
        commit hash:
        ```
        update_branch_head(Path("/path/to/repo"), "abc123def4567890")
        ```

    Notes:
        - The function assumes that the `.scs/HEAD` file exists and contains
          a valid reference to the current branch.
        - The commit hash will overwrite the existing value in the current
          branch's head commit file.
    """
    head_path = get_current_branch_head(parent)
    head_path.write_text(commit_hash)

def get_commit_parents(parent: Path, commit_hash: str) -> List[str]:
    """
    Retrieves the parent commit hashes from a commit object.

    This function reads the commit object corresponding to the given commit hash
    and extracts the parent commit hashes from the commit's content. The parents
    are returned as a list of commit hashes.

    Args:
        parent (Path): The root directory of the repository.
        commit_hash (str): The hash of the commit whose parents are to be retrieved.

    Returns:
        List[str]: A list of parent commit hashes.

    Example:
        Calling this function will return the parent commits of a specific commit:
        ```
        parents = get_commit_parents(Path("/path/to/repo"), "abc123def4567890")
        ```

    Notes:
        - The function assumes that the commit object exists and contains parent
          information in the expected format.
        - If no parents are found in the commit, an empty list is returned.
    """
    commit_content = read_object(parent, commit_hash).decode()
    parents = []
    for line in commit_content.split("\n"):
        if line.startswith("parent"):
            parents.append(line.split(" ")[1])
    return parents


def reconcile_trees(base: str, current: str, target: str) -> str:
    """
    Merges three versions of a file (base, current, target) and resolves conflicts.

    This function performs a three-way merge of the base, current, and target versions
    of a file, identifying changes in each version and merging them. If there are conflicts,
    they are marked in the merged result. The output is a string that contains the merged content.

    Args:
        base (str): The base version of the file.
        current (str): The current version of the file (typically from the current branch).
        target (str): The target version of the file (typically from the branch to merge).

    Returns:
        str: The merged content of the file, with conflicts marked if necessary.

    Example:
        Calling this function will merge three file versions:
        ```
        merged_content = reconcile_trees(base, current, target)
        ```

    Notes:
        - This function assumes the input strings are the content of the respective file versions.
        - Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) are used to indicate conflicting lines.
        - The function does not resolve the conflicts automatically; it marks the conflicting lines for manual resolution.
    """
    base_lines = base.splitlines()
    current_lines = current.splitlines()
    target_lines = target.splitlines()

    merged_lines = []

    for line in set(base_lines + current_lines + target_lines):
        if line in current_lines and line in target_lines:
            merged_lines.append(line)  # No conflict; identical in both branches
        elif line in base_lines:
            if line in current_lines and line not in target_lines:
                # Modified in current branch only
                merged_lines.append(line)
            elif line in target_lines and line not in current_lines:
                # Modified in target branch only
                merged_lines.append(line)
            else:
                # Modified in both branches; this is a conflict
                merged_lines.append(f"<<<<<<< Current Branch\n{line}\n=======\n{line}\n>>>>>>> Target Branch")
        else:
            # Line added in one branch
            if line in current_lines:
                merged_lines.append(line)
            elif line in target_lines:
                merged_lines.append(line)

    return "\n".join(merged_lines)


def read_commit_tree(commit_hash: str) -> str:
    """
    Reads the tree hash from a commit object.

    This function reads the commit object corresponding to the provided commit hash
    and retrieves the hash of the tree object associated with the commit. The tree hash
    is returned as a string.

    Args:
        commit_hash (str): The hash of the commit from which to read the tree hash.

    Returns:
        str: The hash of the tree object associated with the commit.

    Example:
        Calling this function will return the tree hash of the specified commit:
        ```
        tree_hash = read_commit_tree("abc123def4567890")
        ```

    Raises:
        ValueError: If the commit object does not contain a valid tree reference.

    Notes:
        - The function assumes that the commit object exists and is correctly formatted.
        - The tree hash is expected to be on a line starting with "tree ".
    """
    commit_data = read_object(commit_hash, "commit")
    for line in commit_data.splitlines():
        if line.startswith("tree "):
            return line.split()[1]
    raise ValueError(f"Invalid commit object: {commit_hash}")


def checkout_tree(tree_hash: str):
    """
    Recursively checks out the contents of a tree object into the working directory.

    This function takes a tree object hash, reads the tree's contents, and recreates the directory
    structure and files in the working directory. Directories are created recursively, and files
    are written with the content from the corresponding blob object.

    Args:
        tree_hash (str): The hash of the tree object to checkout.

    Example:
        Calling this function will recreate the working directory state from a specific tree:
        ```
        checkout_tree("abc123def4567890")
        ```

    Notes:
        - The function assumes that the tree object and associated blob objects exist.
        - Directories are created with `mkdir(parents=True, exist_ok=True)` to ensure that parent directories are created if needed.
        - If the tree contains files, their content is fetched from the corresponding blob hash and written to disk.
    """
    tree_content = read_object(tree_hash, "tree").decode()
    for line in tree_content.splitlines():
        mode, name, obj_hash = line.split()
        if mode == "40000":  # Directory
            Path(name).mkdir(parents=True, exist_ok=True)
            checkout_tree(obj_hash)
        else:  # File
            file_content = read_object(obj_hash, "blob")
            Path(name).write_bytes(file_content)
    print("Working directory recreated from tree.")



def main():
    if len(sys.argv) < 2:
        print("No argument provided")
        sys.exit(1)

    match sys.argv[1:]:
        case ["init"]:
            try:
                repo_path = Path(".scs")
                if repo_path.exists():
                    print("Repository already initialized.")
                    return
                repo_path.mkdir(parents=True)
            except Exception as e:
                print(f"Error initializing repository: {e}")
                sys.exit(1)

            Path(".scs/objects").mkdir(parents=True)
            Path(".scs/refs").mkdir(parents=True)
            Path(".scs/refs/heads").mkdir(parents=True)
            Path(".scs/refs/heads/main").write_text("")
            Path(".scs/HEAD").write_text("ref: refs/heads/main\n")
            (Path(".scs") / "index").touch()
            print("Initialized scs directory")
        case ["cat-file", "-p", blob_sha]:
            sys.stdout.buffer.write(read_object(Path("."), blob_sha))
        case ["hash-object", "-w", path]:
            hash = write_object(Path("."), "blob", Path(path).read_bytes())
            print(hash)
        case ["add", *paths]:
            for path in paths:
                stage_file(Path("."), Path(path))
            print(f"Staged files: {', '.join(paths)}")
        case ["ls-tree", "--name-only", tree_sha]:
            items = []
            contents = read_object(Path("."), tree_sha)
            while contents:
                mode, contents = contents.split(b" ", 1)
                name, contents = contents.split(b"\0", 1)
                sha = contents[:20]
                contents = contents[20:]
                items.append((mode.decode(), name.decode(), sha.hex()))
            for _, name, _ in items:
                print(name)
        case ["write-tree"]:
            parent = Path(".")
            tree_hash = build_tree_from_index(parent)
            if tree_hash:
                print(tree_hash)
        case ["commit", "-m", message]:
            parent = Path(".")
            tree_hash = build_tree_from_index(parent)
            if not tree_hash:
                print("Nothing to commit")
                return

            head_path = get_current_branch_head(parent)
            parent_commit = head_path.read_text().strip()
            contents = b"".join(
                [
                    b"tree %b\n" % tree_hash.encode(),
                    b"parent %b\n" % parent_commit.encode() if parent_commit else b"",
                    b"author user <user@example.com> 1714599041 -0600\n",
                    b"committer user <user@example.com> 1714599041 -0600\n\n",
                    message.encode(),
                    b"\n",
                ]
            )
            commit_hash = write_object(parent, "commit", contents)
            update_branch_head(parent, commit_hash)
            clear_staging_area(parent)
            print(f"Committed as {commit_hash}")
        case ["log"]:
            parent = Path(".")
            try:
                head_path = get_current_branch_head(parent)
                if not head_path.exists() or not head_path.read_text().strip():
                    print("No commits yet.")
                    return

                current_commit = head_path.read_text().strip()

                while current_commit:
                    commit_content = read_object(parent, current_commit).decode()
                    lines = commit_content.split("\n")
                    print(f"commit {current_commit}")
                    for line in lines:
                        if line.startswith("author"):
                            print(line)
                        elif not line.startswith(("tree", "parent", "committer")):
                            print(f"    {line}")
                    parents = get_commit_parents(parent, current_commit)
                    current_commit = parents[0] if parents else None
            except FileNotFoundError:
                print("No commits yet.")
        case ["branch"]:
            parent = Path(".")
            refs_dir = parent / ".scs" / "refs" / "heads"
            head_ref = (parent / ".scs" / "HEAD").read_text().strip().split(": ")[1]

            print("Branches:")
            for branch in refs_dir.iterdir():
                branch_name = branch.name
                if f"refs/heads/{branch_name}" == head_ref:
                    print(f"* {branch_name}")  # Current branch
                else:
                    print(f"  {branch_name}")
        case ["branch", branch_name]:
            parent = Path(".")
            head_path = get_current_branch_head(parent)
            current_commit = head_path.read_text().strip()
            branch_path = parent / ".scs" / "refs" / "heads" / branch_name
            if branch_path.exists():
                print(f"Branch '{branch_name}' already exists.")
            else:
                branch_path.write_text(current_commit)
                print(f"Branch '{branch_name}' created.")

        case ["branch", "-d", branch_name]:
            parent = Path(".")
            branch_path = parent / ".scs" / "refs" / "heads" / branch_name
            if not branch_path.exists():
                print(f"Branch '{branch_name}' does not exist.")
            elif f"refs/heads/{branch_name}" in (parent / ".scs" / "HEAD").read_text():
                print(f"Cannot delete the current branch '{branch_name}'.")
            else:
                branch_path.unlink()
                print(f"Branch '{branch_name}' deleted.")

        case ["checkout", branch_name]:
            parent = Path(".")
            branch_path = parent / ".scs" / "refs" / "heads" / branch_name
            if not branch_path.exists():
                print(f"Branch '{branch_name}' does not exist.")
            else:
                (parent / ".scs" / "HEAD").write_text(f"ref: refs/heads/{branch_name}\n")
                print(f"Switched to branch '{branch_name}'.")

        case ["merge", target_branch]:
            parent = Path(".")
            target_branch_ref = parent / ".scs" / "refs" / "heads" / target_branch

            if not target_branch_ref.exists():
                print(f"Branch {target_branch} does not exist.")
                return

            # Get current branch and target branch HEAD commits
            head_ref = get_current_branch_head(parent)
            current_commit = head_ref.read_text().strip()
            target_commit = target_branch_ref.read_text().strip()

            if not current_commit or not target_commit:
                print("One of the branches has no commits.")
                return

            # Find the merge base (for simplicity, assume the target branch's HEAD is the base)
            merge_base = target_commit  # Placeholder logic, real merge base calculation requires history traversal

            # Reconcile changes
            current_tree = read_object(parent, current_commit).decode()
            target_tree = read_object(parent, target_commit).decode()
            base_tree = read_object(parent, merge_base).decode()

            # Perform tree reconciliation
            merged_tree_content = reconcile_trees(base_tree, current_tree, target_tree)

            if ">>>>>>>" in merged_tree_content:
                print("Merge conflicts detected!")
                print("Please resolve conflicts in the files and then commit the changes manually.")

                # Write the conflicted tree to a temporary location for manual resolution
                temp_conflict_file = Path(".conflicted_merge")
                temp_conflict_file.write_text(merged_tree_content)
                print(f"Conflicted merge written to {temp_conflict_file}. Resolve the conflicts and commit manually.")
                return

            # If no conflicts, write the merged tree and create a merge commit
            merged_tree_hash = write_object(parent, "tree", merged_tree_content.encode())
            merge_message = f"Merge branch '{target_branch}' into current branch"
            contents = b"".join(
                [
                    b"tree %b\n" % merged_tree_hash.encode(),
                    b"parent %b\n" % current_commit.encode(),
                    b"parent %b\n" % target_commit.encode(),
                    b"author user <user@example.com> 1714599041 -0600\n",
                    b"committer user <user@example.com> 1714599041 -0600\n\n",
                    merge_message.encode(),
                    b"\n",
                ]
            )
            merge_commit_hash = write_object(parent, "commit", contents)
            update_branch_head(parent, merge_commit_hash)
            print(f"Merged {target_branch} into current branch successfully.")

        case ["clone", source_path, target_path]:
            source = Path(source_path)
            target = Path(target_path)

            if not source.exists() or not (source / ".scs").exists():
                print(f"Error: Source repository at {source_path} does not exist or is not an SCS repository.")
                return

            if target.exists():
                print(f"Error: Target directory {target_path} already exists.")
                return

            # Create target directory and initialize as repository
            target.mkdir(parents=True, exist_ok=False)
            (target / ".scs").mkdir()

            # Copy all contents of the `.scs` folder
            source_scs = source / ".scs"
            target_scs = target / ".scs"

            for item in source_scs.iterdir():
                if item.is_dir():
                    shutil.copytree(item, target_scs / item.name)
                else:
                    shutil.copy2(item, target_scs / item.name)

            print(f"Cloned repository from {source_path} to {target_path}.")

            # Checkout the HEAD commit to create the working directory
            os.chdir(target)
            head_commit_hash = (target / ".scs/HEAD").read_text().strip()
            tree_hash = read_commit_tree(head_commit_hash)
            checkout_tree(tree_hash)
            print(f"Checked out the HEAD commit in {target_path}.")

        case _:
            print("Unknown command")

if __name__ == "__main__":
    main()
