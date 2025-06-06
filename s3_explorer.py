import boto3
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkFont
from botocore.exceptions import NoCredentialsError, ProfileNotFound

class S3ClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("S3 Bucket Explorer")

        # --- Color Customization ---
        bg_color = "#e5eb34"  # yellow
        button_color = "#343aeb" # blue
        text_color = "white"  
        background = "black"

        master.config(bg=bg_color)

        # Style for ttk widgets
        style = ttk.Style(master)
        style.configure("TLabel", background=bg_color, foreground=text_color)
        style.configure("TButton", background=button_color, foreground=text_color)
        style.map("TButton",
                  background=[("active", button_color),  # Color when the mouse is over the button
                              ("pressed", button_color)]) # Color when the button is pressed
        style.configure("TEntry", background=background, foreground=text_color)
        style.configure("TCombobox", background=background, foreground=text_color)
        style.configure("Treeview", background=background, foreground=text_color)
        style.configure("Treeview.Heading", background=button_color, foreground=text_color)

        self.text_color = text_color  # Initialize with the default text color
        self.background = background  # Initialize with the default background
        self.dark_mode_on = True

        self._create_theme_toggle_button(master)

        self.default_profile = 'default'
        self.available_profiles = self._get_available_profiles()
        self.current_profile = tk.StringVar(master)
        self.current_profile.set(self.default_profile if self.default_profile in self.available_profiles else self.available_profiles[0] if self.available_profiles else '')
        self.bucket_name = tk.StringVar(master)
        self.s3_client = None
        self.current_objects = []

        # Profile Selection
        ttk.Label(master, text="AWS Profile:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.profile_menu = ttk.Combobox(master, textvariable=self.current_profile, values=self.available_profiles)
        self.profile_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.profile_menu.bind("<<ComboboxSelected>>", self._connect_s3)

        # Bucket Entry
        ttk.Label(master, text="Bucket Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.bucket_entry = ttk.Entry(master, textvariable=self.bucket_name)
        self.bucket_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # S3 Root Folder Entry
        ttk.Label(master, text="S3 Root Folder (optional, e.g., 'myfolder/'):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.s3_root_prefix_entry = ttk.Entry(master)
        self.s3_root_prefix_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Connect Button
        self.connect_button = ttk.Button(master, text="Connect to S3", command=self._connect_s3)
        self.connect_button.grid(row=2, column=2, padx=5, pady=5, sticky="ew")

        self.s3_root_prefix = ''

        # File List
        self.tree = ttk.Treeview(master, columns=("Name", "Size (Bytes)", "Last Modified"), show="headings")
        self.tree.heading("Name", text="Name", command=lambda: self._sort_column(self.tree, "Name", False))
        self.tree.heading("Size (Bytes)", text="Size (Bytes)", command=lambda: self._sort_column(self.tree, "Size (Bytes)", False))
        self.tree.heading("Last Modified", text="Last Modified", command=lambda: self._sort_column(self.tree, "Last Modified", False))
        self.tree.column("Name", minwidth=0, stretch=True)  # Set a minimum width and allow stretching
        self.tree.column("Size (Bytes)", width=50, anchor="e")  # Set a fixed width and right-align
        self.tree.column("Last Modified", width=150)      # Set a fixed width
        self.tree.grid(row=4, column=0, columnspan=6, padx=5, pady=5, sticky="nsew")
        self.tree.bind("<Double-1>", self._download_selected_file)

        # Buttons
        self.download_button = ttk.Button(master, text="Download", command=self._download_selected_file, state=tk.DISABLED)
        self.download_button.grid(row=5, column=0, padx=5, pady=5, sticky="ew")

        self.upload_button = ttk.Button(master, text="Upload Files", command=self._upload_file, state=tk.DISABLED)
        self.upload_button.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        self.upload_folder_button = ttk.Button(master, text="Upload Folder", command=self._upload_folder, state=tk.DISABLED)
        self.upload_folder_button.grid(row=5, column=2, padx=5, pady=5, sticky="ew")    

        self.delete_button = ttk.Button(master, text="Delete", command=self._delete_selected_files, state=tk.DISABLED)
        self.delete_button.grid(row=5, column=3, padx=5, pady=5, sticky="ew")

        self.create_folder_button = ttk.Button(master, text="Create Folder", command=self._create_s3_folder, state=tk.DISABLED)
        self.create_folder_button.grid(row=5, column=4, padx=5, pady=5, sticky="ew") 

        self.refresh_button = ttk.Button(master, text="Refresh", command=self._list_objects, state=tk.DISABLED)
        self.refresh_button.grid(row=5, column=5, padx=5, pady=5, sticky="ew")

    def _create_theme_toggle_button(self, master):
        style = ttk.Style()
        font_size = 12
        font_family = "Segoe UI Symbol"
        symbol_font = tkFont.Font(family=font_family, size=font_size)
        style.configure("UnicodeToggle.TButton", font=symbol_font, padding=0)
        
        self.theme_toggle_button = ttk.Button(
            master,
            text="☀️",  # Initial text (dark mode symbol)
            width=3,      # Make it very small for an icon
            command=self._toggle_theme,
            style="Toggle.TButton" # Optional: Use a specific style
            )
        # Place it in the top right with some padding
        self.theme_toggle_button.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-10, y=10)

        # Optional: Define a minimal style for the button
        style = ttk.Style()
        style.configure("Toggle.TButton", padding=0)

        # Configure grid weights for resizing
        master.grid_columnconfigure(0, weight=1)
        master.grid_columnconfigure(1, weight=1)
        master.grid_columnconfigure(2, weight=1)
        master.grid_columnconfigure(3, weight=0)
        master.grid_columnconfigure(4, weight=0)
        master.grid_rowconfigure(4, weight=1)
        
        self.sort_column_state = {} # To keep track of sort order for each column

    def _sort_column(self, tv, col, reverse):
        """Sorts the treeview based on the clicked column."""
        try:
            data = [(tv.set(child, col), child) for child in tv.get_children('')]

            # Sort based on the column type
            if col == "Size (Bytes)":
                data.sort(key=lambda s: int(s[0]), reverse=reverse)
            elif col == "Last Modified":
                data.sort(key=lambda s: s[0], reverse=reverse) # Assuming string comparison is sufficient
            else:
                data.sort(key=lambda s: s[0].lower(), reverse=reverse)

            for index, (val, child) in enumerate(data):
                tv.move(child, '', index)

            # Switch the sort order for the next click
            tv.heading(col, command=lambda: self._sort_column(tv, col, not reverse))
        except Exception as e:
            messagebox.showerror("Sorting Error", f"Error during sorting: {e}")

    def _toggle_theme(self):
        self.dark_mode_on = not self.dark_mode_on
        if self.dark_mode_on:
            self.text_color = "white"
            self.background = "black"
            self.theme_toggle_button.config(text="☀️") # Switch to light mode symbol
        else:
            self.text_color = "black"
            self.background = "white"
            self.theme_toggle_button.config(text="🌙") # Switch to dark mode symbol
        self._apply_text_background()

    def _apply_text_background(self):
        master = self.master
        text_color = self.text_color
        background = self.background

        style = ttk.Style(master)
        style.configure("TLabel", background=background, foreground=text_color)
        style.configure("TButton", foreground=text_color) # Keep button background
        style.configure("TEntry", background=background, foreground=text_color)
        style.configure("TCombobox", background=background, foreground=text_color)
        style.configure("Treeview", background=background, foreground=text_color)
        style.configure("Treeview.Heading", foreground=text_color) # Keep heading background

        for widget in master.winfo_children():
            self._apply_text_bg_to_widget(widget, text_color, background)

    def _apply_text_bg_to_widget(self, widget, text_color, background):
        try:
            widget_class = str(widget.winfo_class())
            if widget_class in ("Label",):
                widget.config(foreground=text_color, background=background)
            elif isinstance(widget, (tk.Toplevel,)):
                widget.config(bg=background)
                for child in widget.winfo_children():
                    self._apply_text_bg_to_widget(child, text_color, background)
            elif isinstance(widget, (ttk.Frame, tk.LabelFrame)):
                widget.config(bg=background)
                for child in widget.winfo_children():
                    self._apply_text_bg_to_widget(child, text_color, background)
        except tk.TclError:
            pass

    def _get_available_profiles(self):
        config_path = os.path.join(os.path.expanduser('~'), '.aws', 'credentials')
        profiles = []
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
                import configparser
                config = configparser.ConfigParser()
                config.read_string(content)
                profiles = config.sections()
                if 'default' in config:
                    profiles.insert(0, 'default')
        return sorted(list(set(profiles)))

    def _connect_s3(self, event=None):
        profile_name = self.current_profile.get()
        bucket = self.bucket_name.get()
        self.s3_root_prefix = self.s3_root_prefix_entry.get().strip()
        if self.s3_root_prefix and not self.s3_root_prefix.endswith('/'):
            self.s3_root_prefix += '/'
        if not bucket:
            messagebox.showerror("Error", "Please enter the S3 bucket name.")
            return

        try:
            session = boto3.Session(profile_name=profile_name)
            self.s3_client = session.client('s3')
            list_result = self._list_objects()
            if list_result == True:
                self.download_button.config(state=tk.NORMAL)
                self.upload_button.config(state=tk.NORMAL)
                self.upload_folder_button.config(state=tk.NORMAL)
                self.delete_button.config(state=tk.NORMAL)
                self.create_folder_button.config(state=tk.NORMAL, command=self._create_s3_folder)
                self.refresh_button.config(state=tk.NORMAL, command=self._refresh_object_list)
                messagebox.showinfo("Success", f"Connected to bucket '{bucket}' using profile '{profile_name}' with root folder '{self.s3_root_prefix}'.")
            else:
                self._disable_buttons()
                self.refresh_button.config(state=tk.DISABLED, command=None)
                self.create_folder_button.config(state=tk.DISABLED, command=None)
        except ProfileNotFound:
            messagebox.showerror("Error", f"AWS profile '{profile_name}' not found in your credentials file.")
            self.s3_client = None
            self._clear_file_list()
            self._disable_buttons()
            self.refresh_button.config(state=tk.DISABLED, command=None)
        except NoCredentialsError:
            messagebox.showerror("Error", "No AWS credentials found. Please configure your ~/.aws/credentials file.")
            self.s3_client = None
            self._clear_file_list()
            self._disable_buttons()
            self.refresh_button.config(state=tk.DISABLED, command=None)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to S3: {e}")
            self.s3_client = None
            self._clear_file_list()
            self._disable_buttons()
            self.refresh_button.config(state=tk.DISABLED, command=None)

    def _refresh_object_list(self):
        bucket = self.bucket_name.get()
        self.s3_root_prefix = self.s3_root_prefix_entry.get().strip()
        if self.s3_root_prefix and not self.s3_root_prefix.endswith('/'):
            self.s3_root_prefix += '/'

        if not bucket:
            messagebox.showerror("Error", "Please enter the S3 bucket name.")
            return

        if self.s3_client:
            self._list_objects()
        else:
            messagebox.showerror("Error", "Not connected to S3. Please connect first.")


    def _show_long_message(self, title, message):
        top = tk.Toplevel(self.master)
        top.title(title)
        text_area = tk.Text(top, width=80, height=10, wrap="none")  # Adjust width/height as needed
        scrollbar_y = ttk.Scrollbar(top, orient="vertical", command=text_area.yview)
        scrollbar_x = ttk.Scrollbar(top, orient="horizontal", command=text_area.xview)
        text_area.config(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(fill="y", side="right")
        scrollbar_x.pack(fill="x", side="bottom")
        text_area.pack(expand=True, fill="both", padx=10, pady=10)
        text_area.insert(tk.END, message)
        text_area.config(state=tk.DISABLED)
        ok_button = ttk.Button(top, text="OK", command=top.destroy)
        ok_button.pack(pady=5)

    def _disable_buttons(self):
        self.download_button.config(state=tk.DISABLED)
        self.upload_button.config(state=tk.DISABLED)
        self.upload_folder_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)

    def _clear_file_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.current_objects = []

    def _list_objects(self):
        if not self.s3_client or not self.bucket_name.get():
            messagebox.showerror("Error", "Not connected to S3 or bucket name is missing.")
            return

        self._clear_file_list()
        items = []  # Initialize items list here to ensure it always exists
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name.get(), Prefix=self.s3_root_prefix)
            if 'Contents' in response:
                self.current_objects = response['Contents']
                for obj in self.current_objects:
                    key = obj['Key']
                    if self.s3_root_prefix and key.startswith(self.s3_root_prefix):
                        display_key = key[len(self.s3_root_prefix):]
                        if display_key: # Don't show if it's just the prefix
                            size = obj['Size']
                            last_modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                            items.append((display_key, size, last_modified))
                    elif not self.s3_root_prefix:
                        size = obj['Size']
                        last_modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                        items.append((key, size, last_modified))
            else:
                messagebox.showinfo("Info", "Bucket is empty or prefix not found.")
                return "empty"

            # Clear existing items before re-inserting
            for item in self.tree.get_children():
                self.tree.delete(item)
            for item in items:
                self.tree.insert("", tk.END, values=item)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list objects: {e}")
            return False
        
    def _create_s3_folder(self):
        if not self.s3_client or not self.bucket_name.get():
            messagebox.showerror("Error", "Not connected to S3 or bucket name is missing.")
            return

        create_folder_dialog = tk.Toplevel(self.master)
        create_folder_dialog.title("Create New Folder")

        ttk.Label(create_folder_dialog, text="Enter folder name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        folder_name_entry = ttk.Entry(create_folder_dialog)
        folder_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        def create():
            new_folder_name = folder_name_entry.get().strip()
            if new_folder_name:
                s3_key = f"{self.s3_root_prefix}{new_folder_name}/"
                try:
                    self.s3_client.put_object(Bucket=self.bucket_name.get(), Key=s3_key)
                    messagebox.showinfo("Success", f"Folder '{new_folder_name}' created at '{self.s3_root_prefix}'.")
                    self._refresh_object_list()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to create folder: {e}")
                finally:
                    create_folder_dialog.destroy()
            else:
                messagebox.showerror("Error", "Folder name cannot be empty.")

        create_button = ttk.Button(create_folder_dialog, text="Create", command=create)
        create_button.grid(row=1, column=0, columnspan=2, padx=5, pady=10)

        create_folder_dialog.transient(self.master)
        create_folder_dialog.grab_set()
        self.master.wait_window(create_folder_dialog)

    def _download_selected_file(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        files_to_download = [self.tree.item(item)['values'][0] for item in selected_items]
        if not files_to_download:
            return

        destination_folder = filedialog.askdirectory()
        if not destination_folder:
            return  # User cancelled directory selection

        successful_downloads = []
        failed_downloads = {}

        for file_key_display in files_to_download:
            s3_key_full = f"{self.s3_root_prefix}{file_key_display}" if self.s3_root_prefix else file_key_display
            save_path = os.path.join(destination_folder, os.path.basename(file_key_display))
            try:
                self.s3_client.download_file(self.bucket_name.get(), s3_key_full, save_path)
                successful_downloads.append(f"{file_key_display} -> {save_path}")
            except Exception as e:
                failed_downloads[file_key_display] = str(e)

        if successful_downloads:
            self._show_long_message("Download Success", "Successfully downloaded the following files:\n" + "\n".join(successful_downloads))

        if failed_downloads:
            error_message = "The following files failed to download:\n"
            for file, error in failed_downloads.items():
                error_message += f"- {file}: {error}\n"
            messagebox.showerror("Download Error", error_message)

    def _show_upload_success(self, successful_uploads, bucket_name):
        top = tk.Toplevel(self.master)
        top.title("Upload Success")
        text_area = tk.Text(top, width=80, height=15, wrap="none")  # Increased width, disabled wrapping
        scrollbar_y = ttk.Scrollbar(top, orient="vertical", command=text_area.yview)
        scrollbar_x = ttk.Scrollbar(top, orient="horizontal", command=text_area.xview)
        text_area.config(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(fill="y", side="right")
        scrollbar_x.pack(fill="x", side="bottom")
        text_area.pack(expand=True, fill="both", padx=10, pady=10)
        text_area.insert(tk.END, f"Successfully uploaded the following files to '{bucket_name}':\n")
        for file in successful_uploads:
            text_area.insert(tk.END, f"- {file}\n")
        text_area.config(state=tk.DISABLED)  # Make it read-only
        ok_button = ttk.Button(top, text="OK", command=top.destroy)
        ok_button.pack(pady=5)

    def _upload_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder to Upload")
        if not folder_path:
            return

        bucket_name = self.bucket_name.get()
        if not self.s3_client or not bucket_name:
            messagebox.showerror("Error", "Not connected to S3 or bucket name is missing.")
            return

        folder_name = os.path.basename(folder_path)  # Get the name of the selected folder
        successful_uploads = []
        failed_uploads = {}

        for root, _, files in os.walk(folder_path):
            for filename in files:
                local_file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_file_path, folder_path)
                # Construct the S3 key with the folder name as a prefix
                s3_key = f"{self.s3_root_prefix}{folder_name}/{relative_path.replace(os.path.sep, '/')}" if self.s3_root_prefix else f"{folder_name}/{relative_path.replace(os.path.sep, '/')}"

                try:
                    self.s3_client.upload_file(local_file_path, bucket_name, s3_key)
                    successful_uploads.append(f"{local_file_path} -> s3://{bucket_name}/{s3_key}")
                except Exception as e:
                    failed_uploads[local_file_path] = str(e)

        if successful_uploads:
            self._show_long_message("Upload Success", f"Successfully uploaded '{folder_name}' and its contents under '{self.s3_root_prefix}' with folder structure:\n" + "\n".join(successful_uploads))

        if failed_uploads:
            error_message = "The following files failed to upload:\n"
            for file, error in failed_uploads.items():
                error_message += f"- {file}: {error}\n"
            messagebox.showerror("Upload Error", error_message)

        self._list_objects()

    def _upload_file(self):
        file_paths = filedialog.askopenfilenames(title="Select File(s) for Upload", multiple=True)
        if file_paths:
            successful_uploads = []
            failed_uploads = {}
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                s3_key = f"{self.s3_root_prefix}{file_name}" if self.s3_root_prefix else file_name
                try:
                    self.s3_client.upload_file(file_path, self.bucket_name.get(), s3_key)
                    successful_uploads.append(f"{file_path} -> s3://{self.bucket_name.get()}/{s3_key}")
                except Exception as e:
                    failed_uploads[file_path] = str(e)

            if successful_uploads:
                self._show_long_message("Upload Success", "Successfully uploaded the following files under '{self.s3_root_prefix}':\n" + "\n".join(successful_uploads))

            if failed_uploads:
                error_message = "The following files failed to upload:\n"
                for file, error in failed_uploads.items():
                    error_message += f"- {file}: {error}\n"
                messagebox.showerror("Upload Error", error_message)

            self._list_objects()

    def _delete_selected_files(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select one or more files to delete.")
            return

        files_to_delete_display = [self.tree.item(item)['values'][0] for item in selected_items]
        files_to_delete = [f"{self.s3_root_prefix}{key}" for key in files_to_delete_display] if self.s3_root_prefix else files_to_delete_display

        if not files_to_delete:
            return

        confirmation_message = f"Are you sure you want to delete the following files from '{self.bucket_name.get()}' under '{self.s3_root_prefix}'?\n\n" + "\n".join(files_to_delete_display)

        confirm_top = tk.Toplevel(self.master)
        confirm_top.title("Confirm Delete")
        text_area = tk.Text(confirm_top, width=80, height=10, wrap="none")
        scrollbar_y = ttk.Scrollbar(confirm_top, orient="vertical", command=text_area.yview)
        scrollbar_x = ttk.Scrollbar(confirm_top, orient="horizontal", command=text_area.xview)
        text_area.config(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(fill="y", side="right")
        scrollbar_x.pack(fill="x", side="bottom")
        text_area.pack(expand=True, fill="both", padx=10, pady=10)
        text_area.insert(tk.END, confirmation_message)
        text_area.config(state=tk.DISABLED)

        confirmed = tk.BooleanVar()

        def on_yes():
            confirmed.set(True)
            confirm_top.destroy()

        def on_no():
            confirmed.set(False)
            confirm_top.destroy()

        yes_button = ttk.Button(confirm_top, text="Yes", command=on_yes)
        no_button = ttk.Button(confirm_top, text="No", command=on_no)
        yes_button.pack(side="right", padx=10, pady=10)
        no_button.pack(side="left", padx=10, pady=10)

        confirm_top.wait_window()  # Wait for the confirmation window to close

        if confirmed.get():
            deleted_count = 0
            failed_deletes = {}
            deleted_files_list = []
            for i, file_key in enumerate(files_to_delete):
                display_key = files_to_delete_display[i]
                try:
                    self.s3_client.delete_object(Bucket=self.bucket_name.get(), Key=file_key)
                    deleted_count += 1
                    deleted_files_list.append(display_key)
                except Exception as e:
                    failed_deletes[display_key] = str(e)


            if deleted_count > 0 or failed_deletes:
                status_message = ""
                if deleted_count > 0:
                    status_message += f"Successfully deleted the following {deleted_count} file(s) under '{self.s3_root_prefix}':\n" + "\n".join(deleted_files_list) + "\n\n"
                if failed_deletes:
                    status_message += "The following files failed to delete:\n"
                    for file, error in failed_deletes.items():
                        status_message += f"- {file}: {error}\n"
                self._show_long_message("Delete Status", status_message)
            else:
                messagebox.showinfo("Info", "No files were deleted.")

            self._list_objects()

if __name__ == "__main__":
    root = tk.Tk()
    app = S3ClientGUI(root)
    root.geometry("1280x600")  # Set initial window size
    root.mainloop()
