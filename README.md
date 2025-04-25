# Email Printer

A simple, modern Linux application that allows you to send files via email with a drag-and-drop interface.

## Features

- Drag-and-drop file selection
- SMTP email sending with SSL/TLS support
- Persistent settings storage
- Modern GTK3 interface
- Flathub-ready packaging

## Installation

### Dependencies

The application requires the following dependencies:

- Python 3.6+
- PyGObject
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
   - Recipient Email
   - Subject (optional)
   - Body (optional)
4. Save your settings
5. Switch to the Print tab
6. Drag and drop files or click "Choose File" to select files
7. Click "Print" to send the files via email

## Settings Storage

Settings are stored in `~/.config/email-printer/settings.json`. This file contains your SMTP and recipient settings in JSON format.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 