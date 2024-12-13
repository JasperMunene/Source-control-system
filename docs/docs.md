
# Distributed Source Control System (SCS) Documentation

## Abstract

This project presents the development of a Distributed Source Control System (SCS) that replicates essential functionalities of Git, a widely used version control system. The system enables repository initialization, file staging, commits, branch management, merging, and viewing commit histories. While it does not include all the features of Git, it lays the foundation for further enhancements, offering a lightweight alternative for small-scale projects or developers looking for a simpler solution.

## Introduction

The management of software development projects requires effective tools for tracking changes, collaborating with teams, and maintaining codebases over time. Distributed Source Control Systems (SCS), such as Git, have become the standard for version control, providing powerful features for managing code histories and enabling collaboration across distributed teams. However, these systems can be overwhelming for small teams or individual developers due to their complexity. The goal of this project is to develop a simplified SCS that retains core version control features while ensuring ease of use and scalability for smaller projects.

This documentation provides a detailed description of the SCS's features, design, implementation, and future potential.

## Problem Statement

Effective source code management is crucial for maintaining and evolving software projects, particularly as they grow in size and complexity. Existing version control systems, such as Git, are feature-rich and suitable for large-scale applications but may be too complex for small teams or individual developers. This project aims to address that gap by creating a lightweight, distributed source control system that offers essential version control features, without the overhead and complexity of existing solutions.

## Related Work
Git and other distributed source control systems have revolutionized the way developers manage and collaborate on code. Git, in particular, provides a powerful and flexible toolset for managing version history, branching, merging, and collaboration. However, its complexity and steep learning curve can be a barrier for some developers, particularly those who are working on smaller projects or need a more straightforward tool.

This project draws inspiration from Git, aiming to replicate its core features in a simpler, more lightweight manner. While Git's feature set is extensive, this SCS focuses on fundamental functionalities that can be easily extended in the future, addressing the need for a more accessible version control tool.

## System Design and Architecture

The architecture of the SCS is based on several key components, each responsible for handling a specific functionality, including repository management, object storage, commit history tracking, and branching. The design was influenced by Git’s internal structure, ensuring compatibility with existing tools and workflows. The modular nature of the system allows for future enhancements, such as network-based features or advanced conflict resolution algorithms.

### Repository Structure

The system organizes data into the following directories:
- `.scs`: The main directory that stores repository data.
  - `objects`: Contains compressed objects identified by SHA-1 hashes.
  - `refs`: Stores references to branches and commits.
  - `HEAD`: Points to the current branch or commit.

The repository layout mirrors that of Git to ensure familiarity and maintainability.


## Methodology

I developed the SCS using Python due to its simplicity and readability, which made it an ideal choice for implementing file management and hashing operations. Key libraries such as `hashlib` for SHA-1 hashing and `zlib` for object compression were used to manage the storage and retrieval of files. The system was designed to closely replicate Git’s internal structure, particularly in how data is stored and managed, which ensures that it can be expanded or integrated with Git-compatible tools if necessary.

### Core Functionalities

#### Repository Initialization

The `init` command initializes a new repository by creating the `.scs` directory and its subdirectories (such as `objects`, `refs`, and `HEAD`). This structure mirrors Git’s internal directory layout.

```python
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
```

#### Object Storage

In the SCS, files are stored as compressed objects, identified by SHA-1 hashes. The `write_object` function compresses content and stores it in the `objects` directory, while `read_object` decompresses and retrieves it.

```python
def write_object(parent: Path, ty: str, content: bytes) -> str:
    content = ty.encode() + b" " + f"{len(content)}".encode() + b"\0" + content
    hash = hashlib.sha1(content, usedforsecurity=False).hexdigest()
    compressed_content = zlib.compress(content)
    pre = hash[:2]
    post = hash[2:]
    p = parent / ".scs" / "objects" / pre / post
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(compressed_content)
    return hash

def read_object(parent: Path, sha: str) -> bytes:
    pre = sha[:2]
    post = sha[2:]
    p = parent / ".scs" / "objects" / pre / post
    bs = p.read_bytes()
    _, content = zlib.decompress(bs).split(b"\0", maxsplit=1)
    return content
```

#### Staging Files

The `stage_file` function stages files by calculating their hash and writing entries to the `index` file.

```python
def stage_file(parent: Path, path: Path) -> None:
    if not path.exists():
        print(f"File {path} does not exist")
        return

    ignore_patterns = parse_ignore_file()
    relative_path = str(path.relative_to(parent))
    if is_ignored(Path(relative_path), ignore_patterns):
        print(f"Ignoring {relative_path}")
        return

    file_hash = write_object(parent, "blob", path.read_bytes())
    mode = "100644"  # Regular file

    index_path = parent / ".scs" / "index"
    with index_path.open("a") as index:
        index.write(f"{mode} {relative_path} {file_hash}\n")
    print(f"Staged {relative_path}")
```

#### Committing Changes

The `build_tree_from_index` function consolidates staged files into a tree object, and commits reference the tree object along with metadata such as the author and timestamp.

```python
def build_tree_from_index(parent: Path) -> str:
    index_path = parent / ".scs" / "index"
    entries = []

    if not index_path.exists():
        print("Index file is empty or does not exist.")
        return ""

    with index_path.open("r") as index:
        for line in index:
            mode, relative_path, file_hash = line.strip().split(" ")
            entries.append((mode, relative_path, file_hash))

    entries.sort(key=lambda x: x[1])  # Sort by file path
    tree_content = b"".join(
        f"{mode} {path}\0".encode() + bytes.fromhex(hash)
        for mode, path, hash in entries
    )
    return write_object(parent, "tree", tree_content)
```

### Additional Features

- **Conflict Detection**: When merging branches, conflicting changes are flagged but not automatically resolved.
- **Cloning**: Repositories can be cloned locally by copying the `.scs` directory to a new location.

## Results and Evaluation

I conducted several tests to ensure the system performs as expected. These tests covered repository creation, staging, committing, branching, and merging. The results confirmed that the system operates correctly with small repositories, efficiently storing objects and tracking commit history. Performance benchmarks showed acceptable results for repositories containing up to 100 files, with minimal delays during staging and committing operations. However, the system may require optimization for handling larger repositories.

## Future Enhancements

1. Implement automatic conflict resolution during merges.
2. Add support for network-based cloning and remote repositories.
3. Extend functionality to support rebasing and stashing.

## How to Use

1. **Initialize a Repository**:

   ```bash
   python scs.py init
   ```

2. **Stage Files**:

   ```bash
   python scs.py add <file>
   ```

3. **Commit Changes**:

   ```bash
   python scs.py commit -m "Commit message"
   ```

4. **View Commit History**:

   ```bash
   python scs.py log
   ```

5. **Create Branches**:

   ```bash
   python scs.py branch <branch_name>
   ```

6. **Merge Branches**:

   ```bash
   python scs.py merge <branch_name>
   ```

7. **Clone Repository**:

   ```bash
   python scs.py clone <source_dir> <target_dir>
   ```

## Conclusion

This project has successfully implemented a Distributed Source Control System that replicates essential Git features, including repository initialization, file staging, committing, branching, and merging. While the system is still in its early stages, it provides a solid foundation for version control that is both lightweight and extensible. Future developments will focus on adding advanced features, improving performance, and supporting larger-scale projects.

## References

1. What is in that .git directory? https://blog.meain.io/2023/what-is-in-dot-git/
2. Git Documentation. (n.d.). https://git-scm.com/doc
3. Python Documentation https://docs.python.org/3/
