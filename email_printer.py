import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, Gio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from pathlib import Path
import json
from dotenv import load_dotenv
import threading
import datetime
import traceback

class PrinterTab(Gtk.Box):
    def __init__(self, name, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_homogeneous(False)
        self.name = name
        self.parent = parent
        self.selected_files = []
        
        # Create notebook for this printer (will contain our tabs)
        self.notebook = Gtk.Notebook()
        self.notebook.set_vexpand(True)
        self.notebook.set_hexpand(True)
        # Fill this box with the notebook
        self.pack_start(self.notebook, True, True, 0)
        
        # Create main page
        self.main_page = self.create_main_page()
        main_icon = Gtk.Image.new_from_icon_name("document-send-symbolic", Gtk.IconSize.BUTTON)
        main_label = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        main_label.pack_start(main_icon, False, False, 0)
        main_label.pack_start(Gtk.Label(label="Print"), False, False, 0)
        main_label.show_all()
        self.notebook.append_page(self.main_page, main_label)
        
        # Create settings page
        self.settings_page = self.create_settings_page()
        settings_icon = Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.BUTTON)
        settings_label = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        settings_label.pack_start(settings_icon, False, False, 0)
        settings_label.pack_start(Gtk.Label(label="Settings"), False, False, 0)
        settings_label.show_all()
        self.notebook.append_page(self.settings_page, settings_label)
        
        # Create logs page
        self.logs_page = self.create_logs_page()
        logs_icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.BUTTON)
        logs_label = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        logs_label.pack_start(logs_icon, False, False, 0)
        logs_label.pack_start(Gtk.Label(label="Logs"), False, False, 0)
        logs_label.show_all()
        self.notebook.append_page(self.logs_page, logs_label)
        
        # Load settings
        self.settings = self.load_settings()
        self.load_settings_into_ui()

    def create_main_page(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_vexpand(True)
        main_box.set_hexpand(True)
        
        # Main content will be split between drop area (top) and file list (bottom)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_vexpand(True)
        content_box.set_hexpand(True)
        main_box.pack_start(content_box, True, True, 0)
        
        # Create drag and drop area (takes upper portion)
        drop_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        drop_area.set_vexpand(True)
        drop_area.set_hexpand(True)
        drop_area.set_margin_top(10)
        drop_area.set_margin_bottom(10)
        
        # Style the drop area
        drop_area_style = drop_area.get_style_context()
        drop_area_style.add_class("frame")
        
        # Configure drag and drop
        drop_area.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        drop_area.drag_dest_add_uri_targets()
        drop_area.connect("drag-data-received", self.on_drag_data_received)
        
        # Add drop area icon and label
        drop_icon = Gtk.Image.new_from_icon_name("mail-attachment-symbolic", Gtk.IconSize.DIALOG)
        drop_area.pack_start(drop_icon, True, False, 0)
        
        drop_label = Gtk.Label()
        drop_label.set_markup("<span size='large'>Drop files here or click to select</span>")
        drop_area.pack_start(drop_label, True, False, 0)
        
        # Add choose file button
        choose_button = Gtk.Button(label="Choose Files")
        choose_button.set_halign(Gtk.Align.CENTER)
        choose_button.connect("clicked", self.on_choose_file_clicked)
        drop_area.pack_start(choose_button, True, False, 0)
        
        content_box.pack_start(drop_area, True, True, 0)
        
        # Create file list with scrolling (takes lower portion)
        list_frame = Gtk.Frame()
        list_frame.set_shadow_type(Gtk.ShadowType.NONE)
        list_frame.set_vexpand(True)
        list_frame.set_hexpand(True)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        
        self.file_list = Gtk.ListBox()
        self.file_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self.file_list)
        list_frame.add(scrolled)
        content_box.pack_start(list_frame, True, True, 0)
        
        # Create bottom box for progress and button
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # Create progress bar (hidden by default)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("Sending email...")
        self.progress_bar.set_visible(False)
        bottom_box.pack_start(self.progress_bar, False, False, 0)
        
        # Create print button
        self.print_button = Gtk.Button(label="Print")
        self.print_button.get_style_context().add_class("suggested-action")
        self.print_button.set_sensitive(False)
        self.print_button.connect("clicked", self.on_print_clicked)
        bottom_box.pack_start(self.print_button, False, False, 0)
        
        main_box.pack_end(bottom_box, False, False, 0)
        
        return main_box

    def create_settings_page(self):
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        settings_box.set_margin_start(10)
        settings_box.set_margin_end(10)
        settings_box.set_margin_top(10)
        settings_box.set_margin_bottom(10)
        
        # Printer Name and Remove Button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Name section
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Printer Name:")
        self.printer_name = Gtk.Entry()
        self.printer_name.set_text(self.name)
        self.printer_name.connect("changed", self.on_printer_name_changed)
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(self.printer_name, True, True, 0)
        
        # Remove button
        remove_button = Gtk.Button(label="Remove Printer")
        remove_button.get_style_context().add_class("destructive-action")
        remove_button.connect("clicked", self.on_remove_printer_clicked)
        
        header_box.pack_start(name_box, True, True, 0)
        header_box.pack_start(remove_button, False, False, 0)
        settings_box.pack_start(header_box, False, False, 0)
        
        # SMTP Settings Frame
        smtp_frame = Gtk.Frame(label="SMTP Settings")
        smtp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        smtp_box.set_margin_start(10)
        smtp_box.set_margin_end(10)
        smtp_box.set_margin_top(10)
        smtp_box.set_margin_bottom(10)
        
        # SMTP fields
        self.smtp_host = self.create_entry_row("SMTP Host:", smtp_box)
        self.smtp_port = self.create_entry_row("SMTP Port:", smtp_box)
        self.smtp_username = self.create_entry_row("Username:", smtp_box)
        self.smtp_password = self.create_entry_row("Password:", smtp_box, True)
        self.smtp_security = self.create_combo_row("Security:", ["None", "SSL", "TLS"], smtp_box)
        
        # Add test email button
        test_button = Gtk.Button(label="Send Test Email")
        test_button.connect("clicked", self.on_test_email_clicked)
        test_button.set_margin_top(10)
        smtp_box.pack_start(test_button, False, False, 0)
        
        smtp_frame.add(smtp_box)
        settings_box.pack_start(smtp_frame, False, False, 0)
        
        # Recipient Settings Frame
        recipient_frame = Gtk.Frame(label="Recipient Settings")
        recipient_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        recipient_box.set_margin_start(10)
        recipient_box.set_margin_end(10)
        recipient_box.set_margin_top(10)
        recipient_box.set_margin_bottom(10)
        
        # Recipient emails list
        recipient_list_label = Gtk.Label(label="Recipient Emails:")
        recipient_box.pack_start(recipient_list_label, False, False, 0)
        
        # Create scrolled window for recipient list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)  # Add vertical expansion
        scrolled.set_hexpand(True)  # Add horizontal expansion
        scrolled.set_size_request(-1, 80)  # Reduced from 100
        
        self.recipient_list = Gtk.ListBox()
        self.recipient_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self.recipient_list)
        recipient_box.pack_start(scrolled, True, True, 0)
        
        # Add recipient controls
        recipient_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.new_recipient_entry = Gtk.Entry()
        self.new_recipient_entry.set_placeholder_text("New recipient email")
        recipient_controls.pack_start(self.new_recipient_entry, True, True, 0)
        
        add_recipient_button = Gtk.Button(label="Add")
        add_recipient_button.connect("clicked", self.on_add_recipient_clicked)
        recipient_controls.pack_start(add_recipient_button, False, False, 0)
        
        recipient_box.pack_start(recipient_controls, False, False, 0)
        
        # Other recipient fields
        self.email_subject = self.create_entry_row("Subject:", recipient_box)
        self.email_body = self.create_text_view_row("Body:", recipient_box)
        
        recipient_frame.add(recipient_box)
        settings_box.pack_start(recipient_frame, False, False, 0)
        
        # Save button
        save_button = Gtk.Button(label="Save Settings")
        save_button.connect("clicked", self.on_save_settings_clicked)
        settings_box.pack_end(save_button, False, False, 0)
        
        return settings_box

    def create_entry_row(self, label_text, parent, is_password=False):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label(label=label_text)
        entry = Gtk.Entry()
        if is_password:
            entry.set_visibility(False)
        box.pack_start(label, False, False, 0)
        box.pack_start(entry, True, True, 0)
        parent.pack_start(box, False, False, 0)
        return entry

    def create_combo_row(self, label_text, options, parent):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label(label=label_text)
        combo = Gtk.ComboBoxText()
        for option in options:
            combo.append_text(option)
        combo.set_active(0)
        box.pack_start(label, False, False, 0)
        box.pack_start(combo, True, True, 0)
        parent.pack_start(box, False, False, 0)
        return combo

    def create_text_view_row(self, label_text, parent):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        label = Gtk.Label(label=label_text)
        text_view = Gtk.TextView()
        text_view.set_vexpand(True)  # Add expansion
        text_view.set_hexpand(True)  # Add expansion
        box.pack_start(label, False, False, 0)
        box.pack_start(text_view, True, True, 0)
        parent.pack_start(box, True, True, 0)  # Change to allow expansion
        return text_view

    def create_logs_page(self):
        logs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        logs_box.set_margin_start(10)
        logs_box.set_margin_end(10)
        logs_box.set_margin_top(10)
        logs_box.set_margin_bottom(10)
        logs_box.set_vexpand(True)  # Add vertical expansion
        
        # Initialize logs list
        self.logs = []
        
        # Create scrolled window for logs
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)  # Add vertical expansion
        scrolled.set_hexpand(True)  # Add horizontal expansion
        
        # Create text view for logs
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.log_view.set_vexpand(True)  # Add vertical expansion
        self.log_buffer = self.log_view.get_buffer()
        
        scrolled.add(self.log_view)
        logs_box.pack_start(scrolled, True, True, 0)
        
        # Create clear logs button
        clear_button = Gtk.Button(label="Clear Logs")
        clear_button.connect("clicked", self.on_clear_logs_clicked)
        logs_box.pack_end(clear_button, False, False, 0)
        
        return logs_box

    def log_message(self, message, level="INFO"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        self.logs.append(log_entry)
        
        # Update log view
        def update_logs():
            end_iter = self.log_buffer.get_end_iter()
            self.log_buffer.insert(end_iter, log_entry)
        
        GLib.idle_add(update_logs)

    def on_clear_logs_clicked(self, button):
        self.logs = []
        self.log_buffer.set_text("")

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        uris = data.get_uris()
        for uri in uris:
            file_path = uri.replace('file://', '')
            # Handle URL encoding (e.g., spaces encoded as %20)
            file_path = GLib.uri_unescape_string(file_path)
            if os.path.exists(file_path):
                self.add_file_to_list(file_path)
            else:
                self.log_message(f"File not found: {file_path}", "ERROR")
        
        # Complete the drag operation
        drag_context.finish(True, False, time)

    def on_choose_file_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Choose Files",
            parent=self.parent,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_select_multiple(True)
        
        # Add file filters
        all_files = Gtk.FileFilter()
        all_files.set_name("All Files")
        all_files.add_pattern("*")
        dialog.add_filter(all_files)
        
        # Common document types
        documents = Gtk.FileFilter()
        documents.set_name("Documents")
        documents.add_mime_type("application/pdf")
        documents.add_mime_type("application/msword")
        documents.add_mime_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        documents.add_mime_type("application/vnd.ms-excel")
        documents.add_mime_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        documents.add_mime_type("text/plain")
        dialog.add_filter(documents)
        
        # Images
        images = Gtk.FileFilter()
        images.set_name("Images")
        images.add_mime_type("image/jpeg")
        images.add_mime_type("image/png")
        images.add_mime_type("image/gif")
        images.add_mime_type("image/tiff")
        dialog.add_filter(images)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            files = dialog.get_filenames()
            for file_path in files:
                if os.path.exists(file_path):
                    self.add_file_to_list(file_path)
                else:
                    self.log_message(f"File not found: {file_path}", "ERROR")
        
        dialog.destroy()

    def add_file_to_list(self, file_path):
        # Remove the uniqueness check to allow duplicate files
        self.selected_files.append(file_path)
        
        # Create row box for the file
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Add file icon
        icon_theme = Gtk.IconTheme.get_default()
        try:
            file_info = Gio.File.new_for_path(file_path).query_info(
                "standard::*", Gio.FileQueryInfoFlags.NONE, None)
            icon_name = file_info.get_icon().get_names()[0]
            icon = icon_theme.load_icon(icon_name, 16, 0)
        except:
            icon = icon_theme.load_icon("text-x-generic", 16, 0)
        
        icon_image = Gtk.Image.new_from_pixbuf(icon)
        row_box.pack_start(icon_image, False, False, 0)
        
        # Add file name
        label = Gtk.Label(label=os.path.basename(file_path))
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(40)
        label.set_tooltip_text(file_path)  # Show full path on hover
        row_box.pack_start(label, True, True, 0)
        
        # Add file size
        try:
            size = os.path.getsize(file_path)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"
            size_label = Gtk.Label(label=size_str)
            size_label.set_margin_end(6)
            row_box.pack_start(size_label, False, False, 0)
        except:
            pass
        
        # Add remove button
        remove_button = Gtk.Button()
        remove_button.set_relief(Gtk.ReliefStyle.NONE)
        remove_icon = Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.SMALL_TOOLBAR)
        remove_button.add(remove_icon)
        
        # Create ListBoxRow and add the box to it
        list_box_row = Gtk.ListBoxRow()
        list_box_row.add(row_box)
        
        # Store the file path and row reference for removal
        list_box_row.file_path = file_path  # Store the file path in the row
        remove_button.connect("clicked", self.on_remove_file_clicked, list_box_row)
        row_box.pack_start(remove_button, False, False, 0)
        
        self.file_list.add(list_box_row)
        self.file_list.show_all()
        self.print_button.set_sensitive(True)
        
        # Log the addition
        self.log_message(f"Added file: {os.path.basename(file_path)}")

    def on_remove_file_clicked(self, button, list_box_row):
        file_path = list_box_row.file_path  # Get the file path from the row
        try:
            # Remove the first occurrence of this file path
            self.selected_files.remove(file_path)
            # Remove the row from the list
            self.file_list.remove(list_box_row)
            
            if not self.selected_files:
                self.print_button.set_sensitive(False)
            
            # Log the removal
            self.log_message(f"Removed file: {os.path.basename(file_path)}")
        except Exception as e:
            self.log_message(f"Error removing file: {str(e)}", "ERROR")

    def on_print_clicked(self, button):
        if not self.validate_settings():
            return
        
        # Start email sending in a separate thread
        thread = threading.Thread(target=self.send_email_thread)
        thread.daemon = True
        thread.start()

    def validate_settings(self):
        required_fields = {
            "SMTP Host": self.smtp_host.get_text(),
            "SMTP Port": self.smtp_port.get_text(),
            "Username": self.smtp_username.get_text(),
            "Password": self.smtp_password.get_text()
        }
        
        for field, value in required_fields.items():
            if not value:
                dialog = Gtk.MessageDialog(
                    parent=self.parent,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"Please fill in the {field} field"
                )
                dialog.run()
                dialog.destroy()
                return False
        
        # Check if at least one recipient is added
        if len(self.recipient_list.get_children()) == 0:
            dialog = Gtk.MessageDialog(
                parent=self.parent,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Please add at least one recipient email"
            )
            dialog.run()
            dialog.destroy()
            return False
        
        return True

    def send_email_thread(self):
        try:
            # Update UI to show progress
            GLib.idle_add(self.progress_bar.set_visible, True)
            GLib.idle_add(self.print_button.set_sensitive, False)
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username.get_text()
            
            # Get all recipient emails
            recipient_emails = []
            for row in self.recipient_list.get_children():
                box = row.get_child()  # Get the Box widget
                label = box.get_children()[0]  # Get the Label widget
                recipient_emails.append(label.get_text())
            msg['To'] = ", ".join(recipient_emails)
            
            msg['Subject'] = self.email_subject.get_text() or "Files from Email Printer"
            
            self.log_message("Creating email message...")
            
            # Add body
            body = self.email_body.get_buffer().get_text(
                self.email_body.get_buffer().get_start_iter(),
                self.email_body.get_buffer().get_end_iter(),
                True
            )
            msg.attach(MIMEText(body, 'plain'))
            
            # Add attachments
            total_files = len(self.selected_files)
            for i, file_path in enumerate(self.selected_files, 1):
                self.log_message(f"Attaching file: {os.path.basename(file_path)}")
                with open(file_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                msg.attach(part)
                
                # Update progress
                progress = i / total_files
                GLib.idle_add(self.progress_bar.set_fraction, progress)
            
            # Connect to SMTP server
            self.log_message(f"Connecting to SMTP server: {self.smtp_host.get_text()}")
            
            # Handle security
            security = self.smtp_security.get_active_text()
            if security == "SSL":
                smtp = smtplib.SMTP_SSL(self.smtp_host.get_text(), int(self.smtp_port.get_text()))
            else:
                smtp = smtplib.SMTP(self.smtp_host.get_text(), int(self.smtp_port.get_text()))
                if security == "TLS":
                    smtp.starttls()
            
            # Login and send
            self.log_message("Logging in to SMTP server...")
            smtp.login(self.smtp_username.get_text(), self.smtp_password.get_text())
            
            self.log_message("Sending email...")
            smtp.send_message(msg)
            smtp.quit()
            
            self.log_message("Email sent successfully!", "SUCCESS")
            
            # Show success dialog
            GLib.idle_add(self.show_success_dialog)
            
        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            self.log_message(f"Error sending email: {error_msg}\n{tb}", "ERROR")
            GLib.idle_add(self.show_error_dialog, error_msg)
        
        finally:
            # Reset UI
            GLib.idle_add(self.progress_bar.set_visible, False)
            GLib.idle_add(self.progress_bar.set_fraction, 0)
            GLib.idle_add(self.print_button.set_sensitive, True)

    def show_success_dialog(self):
        dialog = Gtk.MessageDialog(
            parent=self.parent,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Email sent successfully!"
        )
        dialog.run()
        dialog.destroy()

    def show_error_dialog(self, error_msg):
        dialog = Gtk.MessageDialog(
            parent=self.parent,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error sending email",
            secondary_text=error_msg
        )
        dialog.run()
        dialog.destroy()

    def on_save_settings_clicked(self, button):
        # Get all recipient emails
        recipient_emails = []
        for row in self.recipient_list.get_children():
            box = row.get_child()  # Get the Box widget
            label = box.get_children()[0]  # Get the Label widget
            recipient_emails.append(label.get_text())
        
        self.settings = {
            "smtp": {
                "host": self.smtp_host.get_text(),
                "port": self.smtp_port.get_text(),
                "username": self.smtp_username.get_text(),
                "password": self.smtp_password.get_text(),
                "security": self.smtp_security.get_active_text()
            },
            "recipient": {
                "emails": recipient_emails,
                "subject": self.email_subject.get_text(),
                "body": self.email_body.get_buffer().get_text(
                    self.email_body.get_buffer().get_start_iter(),
                    self.email_body.get_buffer().get_end_iter(),
                    True
                )
            }
        }
        self.save_settings()
        
        dialog = Gtk.MessageDialog(
            parent=self.parent,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Settings saved successfully!"
        )
        dialog.run()
        dialog.destroy()

    def load_settings(self):
        settings_path = os.path.expanduser(f"~/.config/email-printer/settings_{self.name}.json")
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                return json.load(f)
        return {
            "smtp": {
                "host": "",
                "port": "",
                "username": "",
                "password": "",
                "security": "None"
            },
            "recipient": {
                "emails": [],
                "subject": "",
                "body": ""
            }
        }

    def save_settings(self):
        settings_path = os.path.expanduser("~/.config/email-printer")
        os.makedirs(settings_path, exist_ok=True)
        with open(os.path.join(settings_path, f"settings_{self.name}.json"), 'w') as f:
            json.dump(self.settings, f, indent=4)

    def load_settings_into_ui(self):
        # SMTP settings
        self.smtp_host.set_text(self.settings["smtp"]["host"])
        self.smtp_port.set_text(self.settings["smtp"]["port"])
        self.smtp_username.set_text(self.settings["smtp"]["username"])
        self.smtp_password.set_text(self.settings["smtp"]["password"])
        
        # Set security combo
        security_index = ["None", "SSL", "TLS"].index(self.settings["smtp"]["security"])
        self.smtp_security.set_active(security_index)
        
        # Recipient settings
        # Clear existing recipients
        for row in self.recipient_list.get_children():
            self.recipient_list.remove(row)
        
        # Add saved recipients
        for email in self.settings["recipient"].get("emails", []):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            label = Gtk.Label(label=email)
            remove_button = Gtk.Button(label="Remove")
            remove_button.connect("clicked", self.on_remove_recipient_clicked, email)
            row.pack_start(label, True, True, 0)
            row.pack_start(remove_button, False, False, 0)
            self.recipient_list.add(row)
        
        self.recipient_list.show_all()
        self.email_subject.set_text(self.settings["recipient"]["subject"])
        self.email_body.get_buffer().set_text(self.settings["recipient"]["body"])

    def send_test_email_thread(self):
        try:
            # Update UI
            GLib.idle_add(lambda: self.notebook.get_nth_page(1).set_sensitive(False))
            self.log_message("Sending test email...")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username.get_text()
            
            # Get all recipient emails
            recipient_emails = []
            for row in self.recipient_list.get_children():
                box = row.get_child()  # Get the Box widget
                label = box.get_children()[0]  # Get the Label widget
                recipient_emails.append(label.get_text())
            
            if not recipient_emails:
                GLib.idle_add(self.show_error_dialog, "Please add at least one recipient email")
                return
                
            msg['To'] = ", ".join(recipient_emails)
            
            msg['Subject'] = "Email Printer Test"
            
            # Add body
            test_body = """
            This is a test email from Email Printer.
            
            If you're receiving this email, your SMTP settings are configured correctly!
            
            Configuration used:
            - SMTP Host: {host}
            - SMTP Port: {port}
            - Security: {security}
            - From: {from_email}
            """.format(
                host=self.smtp_host.get_text(),
                port=self.smtp_port.get_text(),
                security=self.smtp_security.get_active_text(),
                from_email=self.smtp_username.get_text()
            )
            
            msg.attach(MIMEText(test_body, 'plain'))
            
            # Connect to SMTP server
            self.log_message(f"Connecting to SMTP server: {self.smtp_host.get_text()}")
            
            # Handle security
            security = self.smtp_security.get_active_text()
            if security == "SSL":
                smtp = smtplib.SMTP_SSL(self.smtp_host.get_text(), int(self.smtp_port.get_text()))
            else:
                smtp = smtplib.SMTP(self.smtp_host.get_text(), int(self.smtp_port.get_text()))
                if security == "TLS":
                    smtp.starttls()
            
            # Login and send
            self.log_message("Logging in to SMTP server...")
            smtp.login(self.smtp_username.get_text(), self.smtp_password.get_text())
            
            self.log_message("Sending test email...")
            smtp.send_message(msg)
            smtp.quit()
            
            self.log_message("Test email sent successfully!", "SUCCESS")
            GLib.idle_add(self.show_success_dialog_with_message, 
                         "Test email sent successfully!\n\nPlease check your inbox.")
            
        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            self.log_message(f"Error sending test email: {error_msg}\n{tb}", "ERROR")
            GLib.idle_add(self.show_error_dialog, f"Failed to send test email: {error_msg}")
        
        finally:
            # Re-enable settings page
            GLib.idle_add(lambda: self.notebook.get_nth_page(1).set_sensitive(True))

    def show_success_dialog_with_message(self, message):
        dialog = Gtk.MessageDialog(
            parent=self.parent,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.run()
        dialog.destroy()

    def on_test_email_clicked(self, button):
        if not self.validate_settings():
            return
        
        # Start test email sending in a separate thread
        thread = threading.Thread(target=self.send_test_email_thread)
        thread.daemon = True
        thread.start()

    def on_printer_name_changed(self, entry):
        new_name = entry.get_text()
        if new_name != self.name:
            self.name = new_name
            self.parent.update_printer_tab_name(self)

    def on_remove_printer_clicked(self, button):
        dialog = Gtk.MessageDialog(
            transient_for=self.parent,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Remove printer '{self.name}'?"
        )
        dialog.format_secondary_text("This will delete all settings for this printer.")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Delete the settings file for this printer
            settings_file = os.path.expanduser(f"~/.config/email-printer/settings_{self.name}.json")
            try:
                if os.path.exists(settings_file):
                    os.remove(settings_file)
            except Exception as e:
                print(f"Error removing settings file: {e}")
            
            # Tell the parent window to remove this printer tab
            self.parent.remove_printer(self)

    def on_add_recipient_clicked(self, button):
        email = self.new_recipient_entry.get_text().strip()
        if email:
            # Create row with email and remove button
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            label = Gtk.Label(label=email)
            remove_button = Gtk.Button(label="Remove")
            remove_button.connect("clicked", self.on_remove_recipient_clicked, email)
            row.pack_start(label, True, True, 0)
            row.pack_start(remove_button, False, False, 0)
            self.recipient_list.add(row)
            self.recipient_list.show_all()
            self.new_recipient_entry.set_text("")

    def on_remove_recipient_clicked(self, button, email):
        for row in self.recipient_list.get_children():
            if row.get_children()[0].get_text() == email:
                self.recipient_list.remove(row)
                break

class EmailPrinterWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Email Printer")
        self.set_default_size(675, 400)
        self.set_resizable(True)
        
        # Set minimum size
        self.set_size_request(400, 300)
        
        # Set window icon
        try:
            self.set_icon_name("mail-send")
        except:
            try:
                icon_theme = Gtk.IconTheme.get_default()
                icon = icon_theme.load_icon("mail-send", 48, 0)
                self.set_icon(icon)
            except:
                pass
        
        # Create the outermost container
        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(outer_box)
        
        # Add padding around the content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        outer_box.pack_start(main_box, True, True, 0)
        
        # Create printer tabs notebook directly in the main box
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        main_box.pack_start(self.notebook, True, True, 0)
        
        # Add "+" button with icon
        add_button = Gtk.Button()
        add_button.set_relief(Gtk.ReliefStyle.NONE)
        add_icon = Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU)
        add_button.add(add_icon)
        add_button.connect("clicked", self.on_add_printer_clicked)
        add_button.show_all()
        self.notebook.append_page(Gtk.Box(), add_button)
        
        # Connect to realize signal to ensure content is visible
        self.connect("realize", self.on_window_realize)
        
        # Load saved printers
        self.load_printers()
    
    def on_window_realize(self, widget):
        # Force show all and resize after window is realized
        self.show_all()
        # Ensure all printer tabs are visible and expanded
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            if isinstance(page, PrinterTab):
                page.show_all()
        # Switch to first tab if available
        if self.notebook.get_n_pages() > 1:  # At least one printer + add button
            self.notebook.set_current_page(0)
        # Schedule another resize after a short delay
        GLib.timeout_add(200, self.final_resize)

    def load_printers(self):
        printers_file = os.path.expanduser("~/.config/email-printer/printers.json")
        try:
            if os.path.exists(printers_file):
                with open(printers_file, 'r') as f:
                    data = json.load(f)
                    printers = data.get("printers", []) if isinstance(data, dict) else data
                    
                    # If no printers found, add a default one
                    if not printers:
                        self.add_printer("Printer 1")
                    else:
                        # Add all saved printers with consistent naming format
                        for printer_name in printers:
                            # Ensure proper spacing in printer name
                            if printer_name.startswith("Printer") and " " not in printer_name:
                                # Convert "PrinterX" to "Printer X"
                                number = printer_name.replace("Printer", "")
                                printer_name = f"Printer {number}"
                            self.add_printer(printer_name)
            else:
                # If file doesn't exist, add a default printer
                self.add_printer("Printer 1")
        except Exception as e:
            print(f"Error loading printers: {e}")
            # If there was an error, add a default printer
            self.add_printer("Printer 1")

    def save_printers(self):
        # Create config directory if it doesn't exist
        config_dir = os.path.expanduser("~/.config/email-printer")
        os.makedirs(config_dir, exist_ok=True)
        
        # Get all printer names except the "+" button
        printer_names = []
        for i in range(self.notebook.get_n_pages() - 1):  # Exclude the last tab (+ button)
            page = self.notebook.get_nth_page(i)
            if isinstance(page, PrinterTab):
                printer_names.append(page.name)
        
        # Save to JSON file
        printers_file = os.path.join(config_dir, "printers.json")
        try:
            with open(printers_file, 'w') as f:
                json.dump({"printers": printer_names}, f)
        except Exception as e:
            print(f"Error saving printers: {e}")

    def add_printer(self, name):
        printer_tab = PrinterTab(name, self)
        
        # Find the "+" button tab index
        add_button_index = -1
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            if not isinstance(page, PrinterTab):
                add_button_index = i
                break
        
        # Create tab label
        tab_label = Gtk.Label(label=name)
        tab_label.set_size_request(80, 24)  # Set minimum size for tab label
        
        # Insert the printer tab before the "+" button
        if add_button_index >= 0:
            # Insert before the "+" button
            self.notebook.insert_page(printer_tab, tab_label, add_button_index)
        else:
            # If "+" button not found, just append and we'll handle recreating the "+" button later
            self.notebook.append_page(printer_tab, tab_label)
            
            # Add the "+" button
            add_button = Gtk.Button()
            add_button.set_relief(Gtk.ReliefStyle.NONE)
            add_icon = Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU)
            add_button.add(add_icon)
            add_button.connect("clicked", self.on_add_printer_clicked)
            add_button.show_all()
            self.notebook.append_page(Gtk.Box(), add_button)
        
        self.notebook.set_tab_reorderable(printer_tab, True)
        self.notebook.set_tab_detachable(printer_tab, True)
        
        # Show and switch to the new tab
        self.notebook.show_all()
        
        # Find the index of the newly added tab and switch to it
        for i in range(self.notebook.get_n_pages()):
            if self.notebook.get_nth_page(i) == printer_tab:
                self.notebook.set_current_page(i)
                break
        
        # Force resize
        printer_tab.queue_resize()
        self.notebook.queue_resize()
        
        # Save printer list
        self.save_printers()
        
        return printer_tab

    def on_add_printer_clicked(self, button):
        # Find the next available printer number
        printer_count = self.notebook.get_n_pages() - 1  # -1 for the "+" button
        new_name = f"Printer {printer_count + 1}"  # Add space between "Printer" and number
        self.add_printer(new_name)

    def update_printer_tab_name(self, printer_tab):
        page_num = self.notebook.page_num(printer_tab)
        if page_num >= 0:
            self.notebook.set_tab_label(printer_tab, Gtk.Label(label=printer_tab.name))
            self.save_printers()

    def remove_printer(self, printer_tab):
        # Find the tab to remove
        target_index = -1
        for i in range(self.notebook.get_n_pages()):
            if self.notebook.get_nth_page(i) == printer_tab:
                target_index = i
                break
        
        if target_index == -1:
            return  # Tab not found
        
        # Get the current active page
        current_page = self.notebook.get_current_page()
        
        # Delete the settings file for this printer
        try:
            settings_file = os.path.expanduser(f"~/.config/email-printer/settings_{printer_tab.name}.json")
            if os.path.exists(settings_file):
                os.remove(settings_file)
        except Exception as e:
            print(f"Error removing settings file: {e}")
        
        # Just remove the single tab without rebuilding everything
        self.notebook.remove_page(target_index)
        
        # Make sure we select an appropriate tab
        if current_page == target_index:
            # If we removed the active tab, select previous tab or first tab
            if target_index > 0:
                self.notebook.set_current_page(target_index - 1)
            else:
                self.notebook.set_current_page(0)
        elif current_page > target_index:
            # If we removed a tab before the current one, adjust the selected tab
            self.notebook.set_current_page(current_page - 1)
        
        # Force UI update
        while Gtk.events_pending():
            Gtk.main_iteration()
        
        # Check if we still have the + button
        has_add_button = False
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            if not isinstance(page, PrinterTab):
                has_add_button = True
                break
        
        # If add button is missing, recreate it
        if not has_add_button:
            add_button = Gtk.Button()
            add_button.set_relief(Gtk.ReliefStyle.NONE)
            add_icon = Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU)
            add_button.add(add_icon)
            add_button.connect("clicked", self.on_add_printer_clicked)
            add_button.show_all()
            self.notebook.append_page(Gtk.Box(), add_button)
        
        # If there are no printers left (only the + button), add a default printer
        printer_count = 0
        for i in range(self.notebook.get_n_pages()):
            if isinstance(self.notebook.get_nth_page(i), PrinterTab):
                printer_count += 1
        
        if printer_count == 0:
            self.add_printer("Printer 1")
        
        # Save the updated printer list
        self.save_printers()
        
        # Force notebook update
        self.notebook.queue_resize()
        self.notebook.queue_draw()

    def final_resize(self):
        # Force a final resize of all components
        self.notebook.queue_resize()
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            if isinstance(page, PrinterTab):
                # Force internal notebooks to resize
                page.notebook.queue_resize()
                
                # Make sure each page's content is sized properly
                for j in range(page.notebook.get_n_pages()):
                    child = page.notebook.get_nth_page(j)
                    child.queue_resize()
        
        # Don't call this function again
        return False

def main():
    # Set dark theme preference
    settings = Gtk.Settings.get_default()
    settings.set_property("gtk-application-prefer-dark-theme", True)
    
    # Fix bug with certain GTK versions that prevent proper resizing
    try:
        settings.set_property("gtk-overlay-scrolling", False)
    except:
        pass
    
    # Load custom CSS
    css_provider = Gtk.CssProvider()
    css = """
    /* Global styles */
    window {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    
    /* Make all boxes expand properly */
    box {
        min-height: 10px;
        min-width: 10px;
    }
    
    /* Notebook (tabs) styling */
    notebook {
        background-color: #252525;
    }
    
    notebook stack {
        min-height: 200px;
    }
    
    scrolledwindow {
        min-height: 100px;
    }
    
    notebook header {
        background-color: #2d2d2d;
        border-bottom: 1px solid #383838;
        min-height: 36px;
    }
    
    notebook header tabs {
        min-height: 36px;
    }
    
    notebook tab {
        padding: 8px 12px;
        background-color: #2d2d2d;
        border: none;
        color: #b0b0b0;
        min-height: 24px;  /* Ensure minimum height for tabs */
        min-width: 80px;   /* Ensure minimum width for tabs */
    }
    
    notebook tab:checked {
        background-color: #383838;
        color: #ffffff;
    }
    
    /* Button styling */
    button {
        background-color: #383838;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        color: #e0e0e0;
        transition: all 200ms ease;
    }
    
    button:hover {
        background-color: #404040;
    }
    
    button.suggested-action {
        background-color: #2b5797;
        color: white;
    }
    
    button.suggested-action:hover {
        background-color: #3266ad;
    }
    
    button.destructive-action {
        background-color: #962b2b;
        color: white;
    }
    
    button.destructive-action:hover {
        background-color: #ad3232;
    }
    
    /* Entry fields */
    entry {
        background-color: #2d2d2d;
        border: 1px solid #383838;
        border-radius: 6px;
        padding: 8px;
        color: #e0e0e0;
    }
    
    entry:focus {
        border-color: #2b5797;
    }
    
    /* Frame styling */
    frame {
        border: 1px solid #383838;
        border-radius: 8px;
        padding: 4px;
    }
    
    frame > label {
        color: #2b5797;
        font-weight: bold;
        margin: 0 8px;
    }
    
    /* Drop area styling */
    .frame {
        border: 2px dashed #383838;
        border-radius: 12px;
        background-color: #252525;
        padding: 20px;
        margin: 10px;
    }
    
    /* List styling */
    list {
        background-color: #252525;
        border-radius: 6px;
    }
    
    list row {
        padding: 8px;
        border-bottom: 1px solid #383838;
    }
    
    list row:hover {
        background-color: #2d2d2d;
    }
    
    /* TextView styling */
    textview {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border-radius: 6px;
    }
    
    textview text {
        background-color: #2d2d2d;
        color: #e0e0e0;
    }
    
    /* Progress bar */
    progressbar {
        border-radius: 6px;
        margin-bottom: 12px;
    }
    
    progressbar trough {
        background-color: #2d2d2d;
        border: none;
        border-radius: 6px;
        min-height: 12px;
    }
    
    progressbar progress {
        background-color: #2b5797;
        border-radius: 6px;
        min-height: 12px;
    }
    
    progressbar text {
        margin-top: 6px;
        margin-bottom: 6px;
    }
    
    /* Scrollbar styling */
    scrollbar {
        background-color: #252525;
        border: none;
    }
    
    scrollbar slider {
        background-color: #383838;
        border-radius: 6px;
        min-width: 8px;
        min-height: 8px;
    }
    
    scrollbar slider:hover {
        background-color: #404040;
    }
    """
    css_provider.load_from_data(css.encode())
    
    # Apply the CSS to all screens
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    
    # Create window but don't show immediately
    win = EmailPrinterWindow()
    win.connect("destroy", Gtk.main_quit)
    
    # Add a slight delay before showing the window
    # This helps ensure everything is properly initialized
    def delayed_show():
        win.show_all()
        # Force a resize after showing
        GLib.timeout_add(100, lambda: win.resize(675, 400))
        return False
    
    # Show window after slight delay
    GLib.timeout_add(50, delayed_show)
    
    Gtk.main()

if __name__ == "__main__":
    main() 