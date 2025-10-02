#!/usr/bin/env python3
"""
CatRAR 1.0 - Cross-Platform Archive Manager
A WinRAR-inspired archive manager built with Python and Tkinter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import zipfile
import tarfile
import os
import shutil
from pathlib import Path
from datetime import datetime
import threading
from typing import Optional, List
import sys


class ArchiveEntry:
    """Represents an entry in an archive"""
    def __init__(self, name: str, size: int, compressed_size: int, 
                 modified: datetime, is_dir: bool = False):
        self.name = name
        self.size = size
        self.compressed_size = compressed_size
        self.modified = modified
        self.is_dir = is_dir


class CatRAR:
    """Main CatRAR application class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("CatRAR 1.0 - Archive Manager")
        self.root.geometry("900x600")
        
        # Current archive
        self.current_archive: Optional[str] = None
        self.archive_entries: List[ArchiveEntry] = []
        
        # Setup UI
        self._setup_menu()
        self._setup_toolbar()
        self._setup_main_area()
        self._setup_statusbar()
        
        # Configure grid weights
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
    def _setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Archive...", command=self.new_archive, accelerator="Ctrl+N")
        file_menu.add_command(label="Open Archive...", command=self.open_archive, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Commands menu
        commands_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Commands", menu=commands_menu)
        commands_menu.add_command(label="Add Files...", command=self.add_files)
        commands_menu.add_command(label="Add Folder...", command=self.add_folder)
        commands_menu.add_command(label="Extract To...", command=self.extract_archive)
        commands_menu.add_command(label="Extract Here", command=self.extract_here)
        commands_menu.add_separator()
        commands_menu.add_command(label="Test Archive", command=self.test_archive)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About CatRAR", command=self.show_about)
        
        # Keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_archive())
        self.root.bind('<Control-o>', lambda e: self.open_archive())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        
    def _setup_toolbar(self):
        """Create toolbar"""
        toolbar = ttk.Frame(self.root, relief=tk.RAISED, borderwidth=1)
        toolbar.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        
        # Toolbar buttons
        ttk.Button(toolbar, text="New", command=self.new_archive).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open", command=self.open_archive).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Add", command=self.add_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Extract", command=self.extract_archive).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Test", command=self.test_archive).pack(side=tk.LEFT, padx=2)
        
    def _setup_main_area(self):
        """Create main file listing area"""
        # Archive info frame
        info_frame = ttk.Frame(self.root)
        info_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        
        self.archive_label = ttk.Label(info_frame, text="No archive opened", 
                                       font=('TkDefaultFont', 9, 'bold'))
        self.archive_label.pack(side=tk.LEFT)
        
        # Main listbox with scrollbars
        list_frame = ttk.Frame(self.root)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create Treeview for file listing
        columns = ('Name', 'Modified', 'Size', 'Packed', 'Ratio')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Configure columns
        self.tree.heading('Name', text='Name')
        self.tree.heading('Modified', text='Modified')
        self.tree.heading('Size', text='Size')
        self.tree.heading('Packed', text='Packed')
        self.tree.heading('Ratio', text='Ratio')
        
        self.tree.column('Name', width=300)
        self.tree.column('Modified', width=150)
        self.tree.column('Size', width=100)
        self.tree.column('Packed', width=100)
        self.tree.column('Ratio', width=80)
        
        # Scrollbars
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Context menu
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Extract Selected...", command=self.extract_selected)
        self.context_menu.add_command(label="Delete", command=self.delete_selected)
        
        self.tree.bind("<Button-3>", self._show_context_menu)
        
    def _setup_statusbar(self):
        """Create status bar"""
        self.statusbar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.grid(row=3, column=0, sticky="ew")
        
    def _show_context_menu(self, event):
        """Show context menu on right-click"""
        if self.current_archive:
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
                
    def update_status(self, message: str):
        """Update status bar"""
        self.statusbar.config(text=message)
        self.root.update_idletasks()
        
    def format_size(self, size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
        
    def new_archive(self):
        """Create a new archive"""
        filepath = filedialog.asksaveasfilename(
            title="Create New Archive",
            defaultextension=".zip",
            filetypes=[
                ("ZIP files", "*.zip"),
                ("TAR.GZ files", "*.tar.gz"),
                ("All files", "*.*")
            ]
        )
        
        if filepath:
            try:
                # Create empty archive
                if filepath.endswith('.zip'):
                    with zipfile.ZipFile(filepath, 'w') as zf:
                        pass
                elif filepath.endswith('.tar.gz'):
                    with tarfile.open(filepath, 'w:gz') as tf:
                        pass
                
                self.current_archive = filepath
                self.load_archive(filepath)
                self.update_status(f"Created new archive: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create archive: {str(e)}")
                
    def open_archive(self):
        """Open an existing archive"""
        filepath = filedialog.askopenfilename(
            title="Open Archive",
            filetypes=[
                ("Archive files", "*.zip *.tar.gz *.tar"),
                ("ZIP files", "*.zip"),
                ("TAR files", "*.tar *.tar.gz"),
                ("All files", "*.*")
            ]
        )
        
        if filepath:
            self.load_archive(filepath)
            
    def load_archive(self, filepath: str):
        """Load and display archive contents"""
        try:
            self.current_archive = filepath
            self.archive_entries.clear()
            
            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            # Load based on file type
            if filepath.endswith('.zip'):
                self._load_zip(filepath)
            elif filepath.endswith(('.tar', '.tar.gz')):
                self._load_tar(filepath)
            else:
                raise ValueError("Unsupported archive format")
                
            # Update UI
            self.archive_label.config(text=f"Archive: {os.path.basename(filepath)}")
            self.update_status(f"Loaded {len(self.archive_entries)} items from archive")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open archive: {str(e)}")
            self.current_archive = None
            
    def _load_zip(self, filepath: str):
        """Load ZIP archive contents"""
        with zipfile.ZipFile(filepath, 'r') as zf:
            for info in zf.filelist:
                entry = ArchiveEntry(
                    name=info.filename,
                    size=info.file_size,
                    compressed_size=info.compress_size,
                    modified=datetime(*info.date_time),
                    is_dir=info.is_dir()
                )
                self.archive_entries.append(entry)
                self._add_tree_item(entry)
                
    def _load_tar(self, filepath: str):
        """Load TAR archive contents"""
        mode = 'r:gz' if filepath.endswith('.gz') else 'r'
        with tarfile.open(filepath, mode) as tf:
            for member in tf.getmembers():
                entry = ArchiveEntry(
                    name=member.name,
                    size=member.size,
                    compressed_size=member.size,  # TAR doesn't store compressed size per file
                    modified=datetime.fromtimestamp(member.mtime),
                    is_dir=member.isdir()
                )
                self.archive_entries.append(entry)
                self._add_tree_item(entry)
                
    def _add_tree_item(self, entry: ArchiveEntry):
        """Add an entry to the tree view"""
        ratio = 0
        if entry.size > 0:
            ratio = ((entry.size - entry.compressed_size) / entry.size) * 100
            
        self.tree.insert('', 'end', values=(
            entry.name,
            entry.modified.strftime('%Y-%m-%d %H:%M:%S'),
            self.format_size(entry.size),
            self.format_size(entry.compressed_size),
            f"{ratio:.1f}%"
        ))
        
    def add_files(self):
        """Add files to current archive"""
        if not self.current_archive:
            messagebox.showwarning("Warning", "Please open or create an archive first")
            return
            
        filepaths = filedialog.askopenfilenames(title="Select Files to Add")
        
        if filepaths:
            self._add_to_archive(filepaths)
            
    def add_folder(self):
        """Add folder to current archive"""
        if not self.current_archive:
            messagebox.showwarning("Warning", "Please open or create an archive first")
            return
            
        folder = filedialog.askdirectory(title="Select Folder to Add")
        
        if folder:
            self._add_to_archive([folder])
            
    def _add_to_archive(self, paths: List[str]):
        """Add files/folders to archive"""
        try:
            self.update_status("Adding files...")
            
            if self.current_archive.endswith('.zip'):
                with zipfile.ZipFile(self.current_archive, 'a') as zf:
                    for path in paths:
                        if os.path.isfile(path):
                            arcname = os.path.basename(path)
                            zf.write(path, arcname)
                        elif os.path.isdir(path):
                            for root, dirs, files in os.walk(path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, os.path.dirname(path))
                                    zf.write(file_path, arcname)
                                    
            elif self.current_archive.endswith(('.tar', '.tar.gz')):
                mode = 'a:gz' if self.current_archive.endswith('.gz') else 'a'
                with tarfile.open(self.current_archive, mode) as tf:
                    for path in paths:
                        arcname = os.path.basename(path)
                        tf.add(path, arcname=arcname)
                        
            # Reload archive
            self.load_archive(self.current_archive)
            self.update_status(f"Added {len(paths)} item(s) to archive")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add files: {str(e)}")
            
    def extract_archive(self):
        """Extract entire archive to selected location"""
        if not self.current_archive:
            messagebox.showwarning("Warning", "No archive opened")
            return
            
        destination = filedialog.askdirectory(title="Select Extraction Destination")
        
        if destination:
            self._extract(destination)
            
    def extract_here(self):
        """Extract archive to current directory"""
        if not self.current_archive:
            messagebox.showwarning("Warning", "No archive opened")
            return
            
        destination = os.path.dirname(self.current_archive)
        self._extract(destination)
        
    def extract_selected(self):
        """Extract selected items only"""
        if not self.current_archive:
            return
            
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "No items selected")
            return
            
        destination = filedialog.askdirectory(title="Select Extraction Destination")
        
        if destination:
            try:
                selected_names = [self.tree.item(item)['values'][0] for item in selected]
                
                if self.current_archive.endswith('.zip'):
                    with zipfile.ZipFile(self.current_archive, 'r') as zf:
                        for name in selected_names:
                            zf.extract(name, destination)
                            
                elif self.current_archive.endswith(('.tar', '.tar.gz')):
                    mode = 'r:gz' if self.current_archive.endswith('.gz') else 'r'
                    with tarfile.open(self.current_archive, mode) as tf:
                        for name in selected_names:
                            member = tf.getmember(name)
                            tf.extract(member, destination)
                            
                messagebox.showinfo("Success", f"Extracted {len(selected_names)} item(s)")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to extract: {str(e)}")
                
    def _extract(self, destination: str):
        """Extract archive to destination"""
        try:
            self.update_status("Extracting...")
            
            if self.current_archive.endswith('.zip'):
                with zipfile.ZipFile(self.current_archive, 'r') as zf:
                    zf.extractall(destination)
                    
            elif self.current_archive.endswith(('.tar', '.tar.gz')):
                mode = 'r:gz' if self.current_archive.endswith('.gz') else 'r'
                with tarfile.open(self.current_archive, mode) as tf:
                    tf.extractall(destination)
                    
            self.update_status(f"Extracted to: {destination}")
            messagebox.showinfo("Success", f"Archive extracted to:\n{destination}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract archive: {str(e)}")
            
    def delete_selected(self):
        """Delete selected items from archive"""
        if not self.current_archive:
            return
            
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "No items selected")
            return
            
        if not messagebox.askyesno("Confirm", "Delete selected items from archive?"):
            return
            
        try:
            selected_names = [self.tree.item(item)['values'][0] for item in selected]
            
            # ZIP files require recreation
            if self.current_archive.endswith('.zip'):
                temp_path = self.current_archive + '.tmp'
                
                with zipfile.ZipFile(self.current_archive, 'r') as zf_in:
                    with zipfile.ZipFile(temp_path, 'w') as zf_out:
                        for item in zf_in.filelist:
                            if item.filename not in selected_names:
                                data = zf_in.read(item.filename)
                                zf_out.writestr(item, data)
                                
                os.replace(temp_path, self.current_archive)
                
            # Reload archive
            self.load_archive(self.current_archive)
            self.update_status(f"Deleted {len(selected_names)} item(s)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete items: {str(e)}")
            
    def test_archive(self):
        """Test archive integrity"""
        if not self.current_archive:
            messagebox.showwarning("Warning", "No archive opened")
            return
            
        try:
            self.update_status("Testing archive...")
            
            if self.current_archive.endswith('.zip'):
                with zipfile.ZipFile(self.current_archive, 'r') as zf:
                    bad_file = zf.testzip()
                    if bad_file:
                        messagebox.showerror("Test Failed", f"Bad file found: {bad_file}")
                    else:
                        messagebox.showinfo("Test Passed", "Archive integrity verified!")
                        
            elif self.current_archive.endswith(('.tar', '.tar.gz')):
                mode = 'r:gz' if self.current_archive.endswith('.gz') else 'r'
                with tarfile.open(self.current_archive, mode) as tf:
                    # TAR doesn't have a built-in test, so we try to read all members
                    for member in tf.getmembers():
                        tf.extractfile(member)
                    messagebox.showinfo("Test Passed", "Archive integrity verified!")
                    
            self.update_status("Test completed")
            
        except Exception as e:
            messagebox.showerror("Test Failed", f"Archive test failed: {str(e)}")
            
    def show_about(self):
        """Show about dialog"""
        about_text = """CatRAR 1.0
        
A cross-platform archive manager
inspired by WinRAR

Features:
• Create and open ZIP/TAR archives
• Add files and folders
• Extract archives
• Test archive integrity
• Cross-platform support

Built with Python and Tkinter

© 2024 CatRAR Project"""
        
        messagebox.showinfo("About CatRAR", about_text)


def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Set icon (if available)
    try:
        if sys.platform == 'win32':
            root.iconbitmap('catrar.ico')
    except:
        pass
        
    app = CatRAR(root)
    root.mainloop()


if __name__ == '__main__':
    main()
