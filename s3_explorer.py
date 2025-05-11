import boto3
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from botocore.exceptions import NoCredentialsError, ProfileNotFound

class S3ClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("S3 Bucket Explorer")

        # --- Color Customization ---
        bg_color = "#e5eb34"  # yellow
        button_color = "#343aeb" # blue
        text_color = "#f2f2f5"  # white

        master.config(bg=bg_color)

        # Style for ttk widgets
        style = ttk.Style(master)
        style.configure("TLabel", background=bg_color, foreground=text_color)
        style.configure("TButton", background=button_color, foreground=text_color)
        style.map("TButton",
                  background=[("active", button_color),  # Color when the mouse is over the button
                              ("pressed", button_color)]) # Color when the button is pressed
        style.configure("TEntry", background="black", foreground=text_color)
        style.configure("TCombobox", background="black", foreground=text_color)
        style.configure("Treeview", background="black", foreground=text_color)
        style.configure("Treeview.Heading", background=button_color, foreground=text_color)

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

        # Connect Button
        self.connect_button = ttk.Button(master, text="Connect to S3", command=self._connect_s3)
        self.connect_button.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        # File List
        self.tree = ttk.Treeview(master, columns=("Name", "Size (Bytes)", "Last Modified"), show="headings")
        self.tree.heading("Name", text="Name", command=lambda: self._sort_column(self.tree, "Name", False))
        self.tree.heading("Size (Bytes)", text="Size (Bytes)", command=lambda: self._sort_column(self.tree, "Size (Bytes)", False))
        self.tree.heading("Last Modified", text="Last Modified", command=lambda: self._sort_column(self.tree, "Last Modified", False))
        self.tree.column("Name", minwidth=350, stretch=True)  # Set a minimum width and allow stretching
        self.tree.column("Size (Bytes)", width=50, anchor="e")  # Set a fixed width and right-align
        self.tree.column("Last Modified", width=150)      # Set a fixed width

        self.tree.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.tree.bind("<Double-1>", self._download_selected_file)

        # Buttons
        self.download_button = ttk.Button(master, text="Download", command=self._download_selected_file, state=tk.DISABLED)
        self.download_button.grid(row=3, column=0, padx=5, pady=5, sticky="ew")

        self.upload_button = ttk.Button(master, text="Upload Files", command=self._upload_file, state=tk.DISABLED)
        self.upload_button.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        self.upload_folder_button = ttk.Button(master, text="Upload Folder", command=self._upload_folder, state=tk.DISABLED)
        self.upload_folder_button.grid(row=3, column=2, padx=5, pady=5, sticky="ew")    

        self.delete_button = ttk.Button(master, text="Delete", command=self._delete_selected_files, state=tk.DISABLED)
        self.delete_button.grid(row=3, column=3, padx=5, pady=5, sticky="ew")

        self.refresh_button = ttk.Button(master, text="Refresh", command=self._list_objects, state=tk.DISABLED)
        self.refresh_button.grid(row=3, column=4, padx=5, pady=5, sticky="ew")

        master.grid_columnconfigure(1, weight=1)
        master.grid_rowconfigure(2, weight=1)
        
        self.sort_column_state = {} 

    def _sort_column(self, tv, col, reverse):
        """Sorts the treeview based on the clicked column."""
        try:
            data = [(tv.set(child, col), child) for child in tv.get_children('')]
            if col == "Size (Bytes)":
                data.sort(key=lambda s: int(s[0]), reverse=reverse)
            elif col == "Last Modified":
                data.sort(key=lambda s: s[0], reverse=reverse) 
            else:
                data.sort(key=lambda s: s[0].lower(), reverse=reverse)

            for index, (val, child) in enumerate(data):
                tv.move(child, '', index)
            tv.heading(col, command=lambda: self._sort_column(tv, col, not reverse))
        except Exception as e:
            messagebox.showerror("Sorting Error", f"Error during sorting: {e}")


    def _get_available_profiles(self):
        config_path = os.path.expanduser("~/.aws/credentials")
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
        if not bucket:
            messagebox.showerror("Error", "Please enter the S3 bucket name.")
            return

        try:
            session = boto3.Session(profile_name=profile_name)
            self.s3_client = session.client('s3')
            self._list_objects()
            self.download_button.config(state=tk.NORMAL)
            self.upload_button.config(state=tk.NORMAL)
            self.upload_folder_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
            self.refresh_button.config(state=tk.NORMAL)
            messagebox.showinfo("Success", f"Connected to bucket '{bucket}' using profile '{profile_name}'.")
        except ProfileNotFound:
            messagebox.showerror("Error", f"AWS profile '{profile_name}' not found in your credentials file.")
            self.s3_client = None
            self._clear_file_list()
            self._disable_buttons()
        except NoCredentialsError:
            messagebox.showerror("Error", "No AWS credentials found. Please configure your ~/.aws/credentials file.")
            self.s3_client = None
            self._clear_file_list()
            self._disable_buttons()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to S3: {e}")
            self.s3_client = None
            self._clear_file_list()
            self._disable_buttons()

    def _show_long_message(self, title, message):
        top = tk.Toplevel(self.master)
        top.title(title)
        text_area = tk.Text(top, width=80, height=10, wrap="none")  
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
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name.get())
            if 'Contents' in response:
                self.current_objects = response['Contents']
                for obj in self.current_objects:
                    key = obj['Key']
                    size = obj['Size']
                    last_modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                    self.tree.insert("", tk.END, values=(key, size, last_modified))
            else:
                messagebox.showinfo("Info", "Bucket is empty.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list objects: {e}")
        if 'Contents' in response:
            self.current_objects = response['Contents']
            items = []
            for obj in self.current_objects:
                key = obj['Key']
                size = obj['Size']
                last_modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                items.append((key, size, last_modified))
            for item in self.tree.get_children():
                self.tree.delete(item)
            for item in items:
                self.tree.insert("", tk.END, values=item)

    def _download_selected_file(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        files_to_download = [self.tree.item(item)['values'][0] for item in selected_items]
        if not files_to_download:
            return

        destination_folder = filedialog.askdirectory()
        if not destination_folder:
            return  

        successful_downloads = []
        failed_downloads = {}

        for file_key in files_to_download:
            save_path = os.path.join(destination_folder, os.path.basename(file_key))
            try:
                self.s3_client.download_file(self.bucket_name.get(), file_key, save_path)
                successful_downloads.append(f"{file_key} -> {save_path}")
            except Exception as e:
                failed_downloads[file_key] = str(e)

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
        text_area = tk.Text(top, width=80, height=15, wrap="none")  
        scrollbar_y = ttk.Scrollbar(top, orient="vertical", command=text_area.yview)
        scrollbar_x = ttk.Scrollbar(top, orient="horizontal", command=text_area.xview)
        text_area.config(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(fill="y", side="right")
        scrollbar_x.pack(fill="x", side="bottom")
        text_area.pack(expand=True, fill="both", padx=10, pady=10)
        text_area.insert(tk.END, f"Successfully uploaded the following files to '{bucket_name}':\n")
        for file in successful_uploads:
            text_area.insert(tk.END, f"- {file}\n")
        text_area.config(state=tk.DISABLED) 
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

        folder_name = os.path.basename(folder_path)  
        successful_uploads = []
        failed_uploads = {}

        for root, _, files in os.walk(folder_path):
            for filename in files:
                local_file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_file_path, folder_path)
                # Construct the S3 key with the folder name as a prefix
                s3_key = f"{folder_name}/{relative_path.replace(os.path.sep, '/')}"

                try:
                    self.s3_client.upload_file(local_file_path, bucket_name, s3_key)
                    successful_uploads.append(f"{local_file_path} -> s3://{bucket_name}/{s3_key}")
                except Exception as e:
                    failed_uploads[local_file_path] = str(e)

        if successful_uploads:
            self._show_long_message("Upload Success", f"Successfully uploaded '{folder_name}' and its contents with folder structure:\n" + "\n".join(successful_uploads))

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
                try:
                    self.s3_client.upload_file(file_path, self.bucket_name.get(), file_name)
                    successful_uploads.append(f"{file_path} -> s3://{self.bucket_name.get()}/{file_name}")
                except Exception as e:
                    failed_uploads[file_path] = str(e)

            if successful_uploads:
                self._show_long_message("Upload Success", "Successfully uploaded the following files:\n" + "\n".join(successful_uploads))

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

        files_to_delete = [self.tree.item(item)['values'][0] for item in selected_items]

        if not files_to_delete:
            return

        confirmation_message = f"Are you sure you want to delete the following files from '{self.bucket_name.get()}'?\n\n" + "\n".join(files_to_delete)

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
        yes_button.pack(side="left", padx=10, pady=10)
        no_button.pack(side="right", padx=10, pady=10)

        confirm_top.wait_window()  

        if confirmed.get():
            deleted_count = 0
            failed_deletes = {}
            deleted_files_list = []
            for file_key in files_to_delete:
                try:
                    self.s3_client.delete_object(Bucket=self.bucket_name.get(), Key=file_key)
                    deleted_count += 1
                    deleted_files_list.append(file_key)
                except Exception as e:
                    failed_deletes[file_key] = str(e)

            if deleted_count > 0 or failed_deletes:
                status_message = ""
                if deleted_count > 0:
                    status_message += f"Successfully deleted the following {deleted_count} file(s):\n" + "\n".join(deleted_files_list) + "\n\n"
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
    root.geometry("1280x600") 
    root.mainloop()
