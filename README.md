# Email Printer

A simple, modern Linux application that allows you to send files via email with a drag-and-drop interface. This application supports multiple virtual printers, each with their own settings.

## Features

- Multiple virtual printers with independent settings
- Drag-and-drop file selection
- SMTP email sending with SSL/TLS support
- Log viewer for tracking email sending operations
- Test email functionality
- Persistent settings storage
- Modern GTK3 dark theme interface
- Responsive UI with proper resizing

## Installation

### Dependencies

The application requires the following dependencies:

- Python 3.6+
- PyGObject (GTK3)
- python-dotenv
- email-validator

### From Source

1. Clone the repository:
```bash
git clone https://github.com/yourusername/email-printer.git
cd email-printer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python email_printer.py
```

### Flatpak Installation (Coming Soon)

The application will be available on Flathub. To install:

```bash
flatpak install flathub com.github.emailprinter
```

## Usage

1. Launch the application
2. Configure your SMTP settings in the Settings tab:
   - SMTP Host
   - Port
   - Username
   - Password
   - Security (None/SSL/TLS)
3. Configure recipient settings:
   - Add recipient emails
   - Subject (optional)
   - Body (optional)
4. Save your settings
5. Send a test email to verify your settings are correct
6. Switch to the Print tab
7. Drag and drop files or click "Choose Files" to select files
8. Click "Print" to send the files via email
9. View logs in the Logs tab

### Multiple Printers

You can add multiple virtual printers by clicking the "+" tab. Each printer can have its own:
- Name
- SMTP settings
- Recipient list
- Email subject and body settings
- Log history

This is useful for sending to different destinations or using different SMTP servers.

## Settings Storage

Settings are stored in:
- `~/.config/email-printer/printers.json` - List of configured printers
- `~/.config/email-printer/settings_PrinterName.json` - Settings for each individual printer

## Logs

The application maintains logs of all operations, including:
- File additions and removals
- Email sending attempts
- Success and error messages

These logs are stored in memory during the application session and can be cleared using the "Clear Logs" button.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

This application was developed with the assistance of [Cursor AI](https://cursor.sh), an AI-powered code editor. 