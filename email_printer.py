import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from pathlib import Path
import json
from dotenv import load_dotenv

class EmailPrinterWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Email Printer")
        self.set_default_size(800, 600)
        
        # Initialize settings
        self.settings = self.load_settings()
        self.selected_files = []
        
        # Create main notebook
        self.notebook = Gtk.Notebook()
        self.add(self.notebook)
        
        # Create main page
        self.main_page = self.create_main_page()
        self.notebook.append_page(self.main_page, Gtk.Label(label="Print"))
        
        # Create settings page
        self.settings_page = self.create_settings_page()
        self.notebook.append_page(self.settings_page, Gtk.Label(label="Settings"))
        
        # Load settings into UI
        self.load_settings_into_ui()

    def create_main_page(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        
        # Create drag and drop area
        drop_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        drop_area.set_vexpand(True)
        drop_area.set_hexpand(True)
        drop_area.set_margin_top(20)
        drop_area.set_margin_bottom(20)
        
        # Configure drag and drop
        drop_area.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        drop_area.drag_dest_add_uri_targets()
        drop_area.connect("drag-data-received", self.on_drag_data_received)
        
        # Add drop area label
        drop_label = Gtk.Label(label="Drop files here or click to select")
        drop_area.add(drop_label)
        
        # Add choose file button
        choose_button = Gtk.Button(label="Choose File")
        choose_button.connect("clicked", self.on_choose_file_clicked)
        drop_area.add(choose_button)
        
        main_box.pack_start(drop_area, True, True, 0)
        
        # Create file list
        self.file_list = Gtk.ListBox()
        self.file_list.set_selection_mode(Gtk.SelectionMode.NONE)
        main_box.pack_start(self.file_list, True, True, 0)
        
        # Create print button
        self.print_button = Gtk.Button(label="Print")
        self.print_button.set_sensitive(False)
        self.print_button.connect("clicked", self.on_print_clicked)
        main_box.pack_end(self.print_button, False, False, 0)
        
        return main_box

    def create_settings_page(self):
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        settings_box.set_margin_start(10)
        settings_box.set_margin_end(10)
        settings_box.set_margin_top(10)
        settings_box.set_margin_bottom(10)
        
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
        
        smtp_frame.add(smtp_box)
        settings_box.pack_start(smtp_frame, False, False, 0)
        
        # Recipient Settings Frame
        recipient_frame = Gtk.Frame(label="Recipient Settings")
        recipient_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        recipient_box.set_margin_start(10)
        recipient_box.set_margin_end(10)
        recipient_box.set_margin_top(10)
        recipient_box.set_margin_bottom(10)
        
        # Recipient fields
        self.recipient_email = self.create_entry_row("Recipient Email:", recipient_box)
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
        text_view.set_size_request(-1, 100)
        box.pack_start(label, False, False, 0)
        box.pack_start(text_view, True, True, 0)
        parent.pack_start(box, False, False, 0)
        return text_view

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        for uri in data.get_uris():
            file_path = uri.replace('file://', '')
            file_path = file_path.replace('%20', ' ')
            self.add_file_to_list(file_path)

    def on_choose_file_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Choose File",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        dialog.set_select_multiple(True)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            for file_path in dialog.get_filenames():
                self.add_file_to_list(file_path)
        dialog.destroy()

    def add_file_to_list(self, file_path):
        if file_path not in self.selected_files:
            self.selected_files.append(file_path)
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            label = Gtk.Label(label=os.path.basename(file_path))
            remove_button = Gtk.Button(label="Remove")
            remove_button.connect("clicked", self.on_remove_file_clicked, file_path)
            row.pack_start(label, True, True, 0)
            row.pack_start(remove_button, False, False, 0)
            self.file_list.add(row)
            self.file_list.show_all()
            self.print_button.set_sensitive(True)

    def on_remove_file_clicked(self, button, file_path):
        self.selected_files.remove(file_path)
        for row in self.file_list.get_children():
            if row.get_children()[0].get_text() == os.path.basename(file_path):
                self.file_list.remove(row)
                break
        if not self.selected_files:
            self.print_button.set_sensitive(False)

    def on_print_clicked(self, button):
        if not self.validate_settings():
            return
        
        try:
            self.send_email()
            dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Email sent successfully!"
            )
            dialog.run()
            dialog.destroy()
        except Exception as e:
            dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"Error sending email: {str(e)}"
            )
            dialog.run()
            dialog.destroy()

    def validate_settings(self):
        required_fields = {
            "SMTP Host": self.smtp_host.get_text(),
            "SMTP Port": self.smtp_port.get_text(),
            "Username": self.smtp_username.get_text(),
            "Password": self.smtp_password.get_text(),
            "Recipient Email": self.recipient_email.get_text()
        }
        
        for field, value in required_fields.items():
            if not value:
                dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"Please fill in the {field} field"
                )
                dialog.run()
                dialog.destroy()
                return False
        return True

    def send_email(self):
        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.smtp_username.get_text()
        msg['To'] = self.recipient_email.get_text()
        msg['Subject'] = self.email_subject.get_text() or "Files from Email Printer"
        
        # Add body
        body = self.email_body.get_buffer().get_text(
            self.email_body.get_buffer().get_start_iter(),
            self.email_body.get_buffer().get_end_iter(),
            True
        )
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachments
        for file_path in self.selected_files:
            with open(file_path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            msg.attach(part)
        
        # Connect to SMTP server
        smtp = smtplib.SMTP(self.smtp_host.get_text(), int(self.smtp_port.get_text()))
        
        # Handle security
        security = self.smtp_security.get_active_text()
        if security == "SSL":
            smtp = smtplib.SMTP_SSL(self.smtp_host.get_text(), int(self.smtp_port.get_text()))
        elif security == "TLS":
            smtp.starttls()
        
        # Login and send
        smtp.login(self.smtp_username.get_text(), self.smtp_password.get_text())
        smtp.send_message(msg)
        smtp.quit()

    def on_save_settings_clicked(self, button):
        self.settings = {
            "smtp": {
                "host": self.smtp_host.get_text(),
                "port": self.smtp_port.get_text(),
                "username": self.smtp_username.get_text(),
                "password": self.smtp_password.get_text(),
                "security": self.smtp_security.get_active_text()
            },
            "recipient": {
                "email": self.recipient_email.get_text(),
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
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Settings saved successfully!"
        )
        dialog.run()
        dialog.destroy()

    def load_settings(self):
        settings_path = os.path.expanduser("~/.config/email-printer/settings.json")
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
                "email": "",
                "subject": "",
                "body": ""
            }
        }

    def save_settings(self):
        settings_path = os.path.expanduser("~/.config/email-printer")
        os.makedirs(settings_path, exist_ok=True)
        with open(os.path.join(settings_path, "settings.json"), 'w') as f:
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
        self.recipient_email.set_text(self.settings["recipient"]["email"])
        self.email_subject.set_text(self.settings["recipient"]["subject"])
        self.email_body.get_buffer().set_text(self.settings["recipient"]["body"])

def main():
    win = EmailPrinterWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main() 