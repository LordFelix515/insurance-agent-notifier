# 🛡️ Insurance Policy WhatsApp Notification & Inquiry Bot

A Python-based automation system that tracks and analyzes insurance policy expiration dates stored in **Google Sheets**, automatically dispatches alert notifications via the **WhatsApp Business Cloud API** to authorized personnel, and supports two-way interactive policy queries via Webhooks.

> **Note:** The outgoing WhatsApp messages and user query keywords (`1 ay`, `list`) are localized in **Turkish** for Turkish insurance management operations.

---

## 🚀 Key Features

- **⏰ Automated Daily Cron Task:** Scans Google Sheets every morning for policies expiring in **exactly 15 days** and sends detailed WhatsApp alerts to authorized recipients.
- **💬 Interactive WhatsApp Bot (Webhook):** Authorized users can query upcoming policy expirations directly through WhatsApp:
  - `1 ay`: Lists all policies expiring within the next 30 days.
  - `list`: Lists policies expiring in exactly 15 days.
- **🔒 Security & Whitelisting:** Strictly processes incoming commands from authorized phone numbers defined in `.env` (unauthorized senders receive a `403 Forbidden` response).
- **📊 Google Sheets API Integration:** Seamlessly and securely reads spreadsheet records using a dedicated Google Service Account (OAuth2).
- **🛡️ Sensitive Data Protection:** All API tokens, phone IDs, and service account keys are stored strictly in `.env` and `credentials.json` (excluded from version control via `.gitignore`).

---

## 📁 Project Directory Structure

```text
Sigorta/
├── .env.example                          # Environment variables template (Root)
├── .gitignore                            # Git rules to exclude sensitive keys and tokens
├── LICENSE                               # MIT License
├── README.md                             # Project overview and documentation
└── insurance_bot/
    ├── bot.py                            # Main application (Webhook server, query engine & CLI menu)
    ├── cron_task.py                      # Scheduled daily cron task script
    ├── requirements.txt                  # Python dependencies
    ├── .env                              # Real API credentials & tokens (GIT-IGNORED)
    ├── .env.example                      # Environment variables template (Module)
    ├── credentials.example.json          # Google Service Account JSON template
    └── credentials.json                  # Real Google Service Account key (GIT-IGNORED)
```

---

## 📋 Google Sheets Column Format

To allow the bot to read your data accurately, your Google Spreadsheet should follow this column structure:

| Column | Field Name | Description |
| :---: | :--- | :--- |
| **A** | Müşteri Adı | Customer / Policyholder Name |
| **G** | Ürün / Hizmet Türü | Insurance Type (Kasko, Trafik, DASK, Konut, etc.) |
| **H** | Plaka | Vehicle License Plate (included in message if present) |
| **I** | Poliçe No | Policy Number |
| **K** | Eski Brüt Prim | Previous Gross Premium amount |
| **N** | Poliçe Bitiş Tarihi | Expiration Date (format: `DD.MM.YYYY`, e.g., `17.10.2026`, or `YYYY-MM-DD`) |

---

## ⚙️ Installation & Configuration

### 1. Clone the Repository
```bash
git clone https://github.com/LordFelix515/insurance-agent-notifier.git
cd insurance-agent-notifier/insurance_bot
```

### 2. Set Up Virtual Environment & Dependencies
```bash
# Create a virtual environment
python -m venv venv

# Activate virtual environment:
# On Linux / macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables (`.env`)
Copy `.env.example` to create your local `.env`:
```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:
```env
# Meta WhatsApp Business Cloud API Configuration
WHATSAPP_TOKEN=your_whatsapp_cloud_api_token
PHONE_NUMBER_ID=your_phone_number_id
VERIFY_TOKEN=your_custom_webhook_verify_token

# Whitelisted Authorized Phone Numbers (country code without '+' or spaces)
RECIPIENT_PHONE_1=905XXXXXXXXX
RECIPIENT_PHONE_2=

# Google Sheets Configuration
GOOGLE_SHEET_NAME=SigortaTakipTablosu
GOOGLE_CREDENTIALS_FILE=credentials.json
```

### 4. Google Sheets Service Account Setup (`credentials.json`)
1. Visit the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. Enable the **Google Sheets API** and **Google Drive API**.
3. Navigate to **IAM & Admin > Service Accounts**, create a service account, and generate a **JSON** private key.
4. Save the downloaded JSON file as `insurance_bot/credentials.json`.
5. Copy the `client_email` address from the JSON file and share your Google Spreadsheet with this address as a **Viewer**.

---

## 🖥️ Usage

### A. Interactive CLI Testing
To test the bot functionality directly from your terminal:
```bash
python bot.py
```
Choose from the interactive menu:
- `1`: Starts the Flask Webhook server on port 5000.
- `2`: Queries and displays policies expiring within the next 30 days, sending a WhatsApp alert to authorized numbers.
- `3`: Queries and displays policies expiring in exactly 15 days, sending a WhatsApp alert.

---

### B. Automated Scheduled Task (Cron Task)
To automatically check policies each morning and alert authorized contacts for policies expiring in 15 days, execute `cron_task.py`.

#### Linux Crontab Configuration:
```bash
crontab -e
```
Add the following line to schedule execution daily at 08:20 AM:
```cron
20 8 * * * /usr/bin/python3 /path/to/Sigorta/insurance_bot/cron_task.py >> /path/to/Sigorta/insurance_bot/cron.log 2>&1
```

#### Windows Task Scheduler Configuration:
- **Action:** Start a program (`python.exe`)
- **Arguments:** `C:\path\to\Sigorta\insurance_bot\cron_task.py`
- **Trigger:** Daily at 08:20 AM

---

### C. Live WhatsApp Webhook Bot
Start the Flask server to listen for incoming WhatsApp messages:
```bash
python bot.py
# Select option 1
```

Expose the server using Ngrok or a reverse proxy:
```bash
ngrok http 5000
```
- In the **Meta for Developers** portal under WhatsApp Webhook Configuration:
  - **Callback URL:** `https://your-domain.ngrok-free.app/webhook`
  - **Verify Token:** The value of `VERIFY_TOKEN` defined in your `.env`
  - **Webhook Fields:** Subscribe to `messages`.

---

## 📲 Sample WhatsApp Notification Format

When triggered, the bot delivers notifications in Turkish directly to the authorized WhatsApp recipients:

```text
📅 *OTOMATİK BİLDİRİM: Tam 15 Günü Kalan Poliçeler:*

👤 İsim: Ahmet Yılmaz
📄 Poliçe No: 123456789
🛠 Ürün/Hizmet: Kasko
🚙 Plaka: 34 ABC 123
💰 Eski Brüt Prim: 8500 TL
⏰ Bitiş Tarihi: 17.10.2026 (Kalan: 15 gün)
-----------------------
```

---

## 🔐 Security Considerations

- **Secrets Management:** `.env` and `credentials.json` are strictly excluded from Git tracking via `.gitignore`. Never commit them to a public repository.
- **Access Control:** Only messages originating from `RECIPIENT_PHONE_1` and `RECIPIENT_PHONE_2` can trigger data lookups.
- **Production Tokens:** For production environments, generate a permanent Meta System User Access Token rather than temporary developer tokens.

---

## 📄 License
This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
