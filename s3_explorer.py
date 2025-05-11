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
        self.tree.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.tree.bind("<Double-1>", self._download_selected_file)

        # Buttons
        self.download_button = ttk.Button(master, text="Download", command=self._download_selected_file, state=tk.DISABLED)
        self.download_button.grid(row=3, column=0, padx=5, pady=5, sticky="ew")

        self.upload_button = ttk.Button(master, text="Upload", command=self._upload_file, state=tk.DISABLED)
        self.upload_button.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        self.delete_button = ttk.Button(master, text="Delete", command=self._delete_selected_files, state=tk.DISABLED)
        self.delete_button.grid(row=3, column=2, padx=5, pady=5, sticky="ew")

        self.refresh_button = ttk.Button(master, text="Refresh", command=self._list_objects, state=tk.DISABLED)
        self.refresh_button.grid(row=3, column=3, padx=5, pady=5, sticky="ew")

        # Configure grid weights for resizing
        master.grid_columnconfigure(1, weight=1)
        master.grid_rowconfigure(2, weight=1)
        
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

    def _disable_buttons(self):
        self.download_button.config(state=tk.DISABLED)
        self.upload_button.config(state=tk.DISABLED)
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
            # Clear existing items before re-inserting
            for item in self.tree.get_children():
                self.tree.delete(item)
            for item in items:
                self.tree.insert("", tk.END, values=item)

    def _download_selected_file(self, event=None):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        file_key = self.tree.item(selected_item[0])['values'][0]
        save_path = filedialog.asksaveasfilename(
            defaultextension=os.path.splitext(file_key)[1],
            initialfile=os.path.basename(file_key)
        )

        if save_path:
            try:
                self.s3_client.download_file(self.bucket_name.get(), file_key, save_path)
                messagebox.showinfo("Success", f"Downloaded '{file_key}' to '{save_path}'.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to download '{file_key}': {e}")

    def _upload_file(self): 
        file_paths = filedialog.askopenfilenames()
        if file_paths:
            successful_uploads = []
            failed_uploads = {}
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                try:
                    self.s3_client.upload_file(file_path, self.bucket_name.get(), file_name)
                    successful_uploads.append(file_name)
                except Exception as e:
                    failed_uploads[file_name] = str(e)

            if successful_uploads:
                success_message = f"Successfully uploaded the following files to '{self.bucket_name.get()}':\n" + "\n".join(successful_uploads)
                messagebox.showinfo("Upload Success", success_message)

            if failed_uploads:
                error_message = "The following files failed to upload:\n"
                for file, error in failed_uploads.items():
                    error_message += f"- {file}: {error}\n"
                messagebox.showerror("Upload Error", error_message)

            self._list_objects()  # Refresh the file list after all uploads

    def _delete_selected_files(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select one or more files to delete.")
            return

        files_to_delete = [self.tree.item(item)['values'][0] for item in selected_items]

        if not files_to_delete:
            return

        confirmation = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the following files from '{self.bucket_name.get()}'?\n\n" + "\n".join(files_to_delete))

        if confirmation:
            deleted_count = 0
            failed_deletes = {}
            for file_key in files_to_delete:
                try:
                    self.s3_client.delete_object(Bucket=self.bucket_name.get(), Key=file_key)
                    deleted_count += 1
                except Exception as e:
                    failed_deletes[file_key] = str(e)

            if deleted_count > 0:
                message = f"Successfully deleted {deleted_count} file(s) from '{self.bucket_name.get()}'."
                if failed_deletes:
                    message += "\nThe following files failed to delete:"
                    for file, error in failed_deletes.items():
                        message += f"\n- {file}: {error}"
                    messagebox.showinfo("Delete Status", message)
                else:
                    messagebox.showinfo("Delete Success", message)
            elif failed_deletes:
                error_message = "Failed to delete the following files:\n"
                for file, error in failed_deletes.items():
                    error_message += f"- {file}: {error}\n"
                messagebox.showerror("Delete Error", error_message)
            else:
                messagebox.showinfo("Info", "No files were deleted.")

            self._list_objects()  # Refresh the file list after deletion attempts

if __name__ == "__main__":
    root = tk.Tk()
    app = S3ClientGUI(root)
    root.mainloop()
