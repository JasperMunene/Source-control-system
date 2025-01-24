# Distributed Source Control System (SCS)

## Overview

The **Distributed Source Control System (SCS)** is a lightweight version control tool inspired by Git. It demonstrates core version control concepts, such as initializing repositories, staging files, creating commits, branching, merging, and more.
---

## Problem Statement

The challenge was to create a distributed source control system with the following features:
- Initialize a repository in a directory, storing the repository in a dot-prefixed subdirectory.
- Support staging and committing files, creating branches, merging, and viewing commit history.
- Detect conflicting changes during merges.
- Clone the repository on disk (network functionality not required).
- Implement a file ignore mechanism for specific files or directories.

This solution aims to capture these functionalities while demonstrating clear thinking, determination, and technical expertise.

---

## Features

1. **Repository Initialization**  
   Create a repository in a specified directory, setting up the necessary subdirectories and metadata files.
   
2. **Staging and Committing**  
   Track file changes by staging (`add`) and recording them in commits with meaningful messages.
   
3. **Commit History**  
   View a linear or branch-based history of changes with details such as commit ID, author, timestamp, and message.
   
4. **Branching**  
   Support isolated development workflows by allowing branch creation and switching.
   
5. **Merging**  
   Combine changes from different branches while detecting and flagging conflicts.
   
6. **Repository Cloning**  
   Duplicate repositories on disk, including all commit histories and metadata.
   
7. **Ignore Files**  
   Use `.scsignore` files to exclude specified files or directories from version control.

---

## Technical Implementation

### Core Concepts

1. **Data Storage**  
   - Versioned files are stored as compressed objects using `zlib`.
   - Files are hashed with SHA-1 to ensure unique identification.
   
2. **Commit Structure**  
   - Commits store references to file trees, parent commits, and metadata.
   - Trees are constructed to represent the repository’s state at the time of the commit.

3. **Branching and Merging**  
   - Branches are implemented as pointers to commits.
   - Merging uses a simple three-way merge algorithm, flagging conflicts for manual resolution.

4. **Performance Optimization**  
   - Efficient storage is achieved by using content-based deduplication via hashing.
   - Only changes between commits are stored.

---

## Usage

### 1. Initialize a Repository
```bash
python scs.py init
```

### 2. Stage Files for Commit
```bash
python scs.py add <file>
```

### 3. Commit Staged Files
```bash
python scs.py commit -m "Commit message"
```

### 4. View Commit History
```bash
python scs.py log
```

### 5. Branching
```bash
python scs.py branch <branch_name>
python scs.py checkout <branch_name>
```

### 6. Merge Branches
```bash
python scs.py merge <branch_name>
```

### 7. Clone Repository
```bash
python scs.py clone <source_dir> <target_dir>
```

### 8. Exclude Files
Add file patterns to `.scsignore` to prevent them from being tracked.

---

## Challenges and Solutions

1. **Conflict Detection**  
   - **Challenge**: Identifying and handling conflicting changes during merges.
   - **Solution**: Implemented a simple three-way merge algorithm that flags conflicts for manual resolution.
   
2. **Efficient Storage**  
   - **Challenge**: Avoiding redundant storage of unchanged files.
   - **Solution**: Adopted Git’s model of storing objects by content hash, enabling deduplication.

3. **Scalability**  
   - **Challenge**: Designing a system that mimics Git’s modularity.
   - **Solution**: Followed a modular architecture with distinct layers for object storage, commit management, and branching.

---

## Why This Project?

This project was built to:
- Deepen my understanding of distributed version control systems.
- Demonstrate my problem-solving and software engineering skills.
- Build a functional tool that reflects Git's core principles in a simplified manner.

It emphasizes my ability to work independently, think critically, and deliver a well-documented, practical solution.

---

## Future Improvements

Given more time, I would:
1. Add remote repository support for distributed workflows.
2. Enhance merge functionality with automated conflict resolution.
3. Implement additional features like stashing, rebasing, and interactive commits.

---

## About Me

My name is **Jasper Munene**, and I’m passionate about solving complex problems through code. I built this project to showcase my skills in software development, system design, and problem-solving. Feel free to reach out to me via [email](mailto:devjaspermunene@gmail.com).

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

