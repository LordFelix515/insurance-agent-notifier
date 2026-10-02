# -*- coding: utf-8 -*-
import os
import sys
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# Windows terminal UTF-8 character support (emojis and Turkish characters)
if hasattr(sys.stdout, "reconfigure"):
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
  sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Search for .env first in script directory, fallback to current working directory
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
  load_dotenv(env_path)
else:
  load_dotenv()

app = Flask(__name__)

# Settings & Environment Variables
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "sigorta_bot_gizli_token_123")

# Resolve Google Credentials file path (convert relative path to absolute based on script directory)
cred_env = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
if not os.path.isabs(cred_env):
  candidate_path = os.path.join(BASE_DIR, cred_env)
  if os.path.exists(candidate_path):
    CREDENTIALS_FILE = candidate_path
  else:
    CREDENTIALS_FILE = os.path.abspath(cred_env)
else:
  CREDENTIALS_FILE = cred_env

# Whitelisted Authorized Phone Numbers (automatically filters empty entries)
ALLOWED_NUMBERS = [
    num for num in [os.getenv("RECIPIENT_PHONE_1"), os.getenv("RECIPIENT_PHONE_2")]
    if num and num.strip()
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def send_whatsapp_message(phone, message):
  url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
  headers = {
      "Authorization": f"Bearer {TOKEN}",
      "Content-Type": "application/json",
  }
  payload = {
      "messaging_product": "whatsapp",
      "to": phone,
      "type": "text",
      "text": {"body": message},
  }
  try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if response.status_code != 200:
      print(f"❌ Meta API Hatası ({response.status_code}): {response.text}")
    return response.status_code == 200
  except Exception as e:
    print(f"❌ WhatsApp Gönderim Hatası: {e}")
    return False


def get_expiring_policies(exact_days=None, max_days=None):
  # Google Sheets Connection
  if not os.path.exists(CREDENTIALS_FILE):
    print(f"Hata: '{CREDENTIALS_FILE}' dosyası bulunamadı! Lütfen Google Service Account dosyanızı ekleyin.")
    return []

  creds = Credentials.from_service_account_file(
      CREDENTIALS_FILE, scopes=SCOPES
  )
  client = gspread.authorize(creds)

  try:
    sheet = client.open(SHEET_NAME).sheet1
    rows = sheet.get_all_values()  # Reads by cell position rather than headers
  except Exception as e:
    print(f"Google Sheet okunamadı: {e}")
    return []

  today = date.today()
  expiring_policies = []

  # First row (index 0) is headers, start from index 1
  for i in range(1, len(rows)):
    row = rows[i]
    
    # Column letter indexes (A=0, G=6, H=7, I=8, K=10, N=13)
    # Safe retrieval in case a row has fewer columns
    def get_col(idx):
        return row[idx] if len(row) > idx else ""

    cust_name = get_col(0)       # Column A
    product = get_col(6)         # Column G
    plate = get_col(7)           # Column H
    policy_no = get_col(8)       # Column I
    prev_prim = get_col(10)      # Column K
    expiry_date_str = get_col(13) # Column N

    if not expiry_date_str or not policy_no:
      continue

    raw_date = str(expiry_date_str).replace("\xa0", " ").strip()
    clean_date = raw_date.replace(",", ".").replace("/", ".").replace(" ", "")

    expiry_date = None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y.%m.%d", "%d.%m.%y"):
      try:
        expiry_date = datetime.strptime(clean_date if "." in fmt else raw_date, fmt).date()
        break
      except Exception:
        continue

    if not expiry_date:
      continue

    delta = (expiry_date - today).days

    add_to_list = False
    if exact_days is not None:
      if delta == exact_days:
        add_to_list = True
    elif max_days is not None:
      if 0 <= delta <= max_days:
        add_to_list = True

    if add_to_list:
      expiring_policies.append({
          "name": cust_name,
          "policy_no": policy_no,
          "product": product,
          "plate": plate,
          "prev_prim": prev_prim,
          "expiry_date": expiry_date,
          "expiry_date_str": expiry_date.strftime("%d.%m.%Y"),
          "days_left": delta
      })

  # Sort by expiration date ascending
  expiring_policies.sort(key=lambda x: x["expiry_date"])
  return expiring_policies


@app.route("/webhook", methods=["GET"])
def verify_webhook():
  """Endpoint used by Meta to verify webhook challenge"""
  mode = request.args.get("hub.mode")
  token = request.args.get("hub.verify_token")
  challenge = request.args.get("hub.challenge")

  if mode and token:
    if mode == "subscribe" and token == VERIFY_TOKEN:
      print("WEBHOOK_VERIFIED")
      return challenge, 200
    else:
      return "Verification failed", 403
  return "Hello World", 200


@app.route("/webhook", methods=["POST"])
def handle_webhook():
  """Endpoint that processes incoming WhatsApp webhook events and messages"""
  data = request.json

  if data.get("object"):
    if (
        data.get("entry")
        and data["entry"][0].get("changes")
        and data["entry"][0]["changes"][0].get("value")
        and data["entry"][0]["changes"][0]["value"].get("messages")
    ):
      
      message_data = data["entry"][0]["changes"][0]["value"]["messages"][0]
      sender_phone = message_data["from"]
      
      print(f"Gelen Mesaj Numarasi: '{sender_phone}'")
      print(f"Izin Verilen Numaralar: {ALLOWED_NUMBERS}")

      # Security: Only respond to messages from authorized whitelisted phone numbers
      if sender_phone not in ALLOWED_NUMBERS:
        print("HATA: Numara eslesmedi, erisim reddedildi (403).")
        return jsonify({"status": "unauthorized"}), 403

      if message_data.get("type") == "text":
        message_text = message_data["text"]["body"].lower().strip()

        if message_text == "1 ay" or message_text == "list":
          if message_text == "1 ay":
            policies = get_expiring_policies(max_days=30)
            header = "📅 *Son 1 Ay İçinde Bitecek Poliçeler:*\n\n"
            empty_msg = "Son 1 ay içinde bitecek poliçe bulunmamaktadır."
          else: # "list"
            policies = get_expiring_policies(exact_days=15)
            header = "📅 *Tam Olarak 15 Günü Kalan Poliçeler (Günlük Kontrol):*\n\n"
            empty_msg = "Bugün tam olarak 15 günü kalan poliçe bulunmamaktadır."
          
          if not policies:
            send_whatsapp_message(sender_phone, empty_msg)
          else:
            response_text = header
            for p in policies:
              plate_info = f"\n🚙 Plaka: {p['plate']}" if p.get('plate') and str(p['plate']).strip() != "" else ""
              prev_prim_info = f"\n💰 Eski Brüt Prim: {p['prev_prim']}" if p.get('prev_prim') and str(p['prev_prim']).strip() != "" else ""
              response_text += (
                  f"👤 İsim: {p['name']}\n"
                  f"📄 Poliçe No: {p['policy_no']}\n"
                  f"🛠 Ürün/Hizmet: {p['product']}{plate_info}{prev_prim_info}\n"
                  f"⏰ Bitiş Tarihi: {p['expiry_date_str']} (Kalan: {p['days_left']} gün)\n"
                  f"-----------------------\n"
              )
            
            # Send message (keeping WhatsApp's 4096 character limit in mind)
            send_whatsapp_message(sender_phone, response_text)

    return jsonify({"status": "success"}), 200
  else:
    return jsonify({"status": "not_found"}), 404


if __name__ == "__main__":
  print("=========================================")
  print("1: Webhook Sunucusunu Başlat (Ngrok için)")
  print("2: Konsoldan Manuel Test (1 Aylık Liste)")
  print("3: Konsoldan Manuel Test (Tam 15 Günlük Liste)")
  print("=========================================")
  secim = input("Ne yapmak istersiniz? (1/2/3): ")
  
  if secim == "2" or secim == "3":
    print("\nGoogle Sheets okunuyor...")
    
    if secim == "2":
      policies = get_expiring_policies(max_days=30)
      header = "📅 *TEST: Son 1 Ay İçinde Bitecek Poliçeler:*\n\n"
    else:
      policies = get_expiring_policies(exact_days=15)
      header = "📅 *TEST: Tam 15 Günü Kalan Poliçeler:*\n\n"

    if not policies:
      print("Kriterlere uygun poliçe bulunamadı.")
    else:
      response_text = header
      for p in policies:
        plate_info = f"\n🚙 Plaka: {p['plate']}" if p.get('plate') and str(p['plate']).strip() != "" else ""
        prev_prim_info = f"\n💰 Eski Brüt Prim: {p['prev_prim']}" if p.get('prev_prim') and str(p['prev_prim']).strip() != "" else ""
        response_text += (
            f"👤 İsim: {p['name']}\n"
            f"📄 Poliçe No: {p['policy_no']}\n"
            f"🛠 Ürün/Hizmet: {p['product']}{plate_info}{prev_prim_info}\n"
            f"⏰ Bitiş Tarihi: {p['expiry_date_str']} (Kalan: {p['days_left']} gün)\n"
            f"-----------------------\n"
        )
      
      print("\n--- GÖNDERILECEK MESAJ ---")
      print(response_text)
      print("--------------------------\n")

      if not ALLOWED_NUMBERS:
        print("HATA: .env dosyasında hiç yetkili numara (RECIPIENT_PHONE_1) bulunamadı!")
      else:
        for phone in ALLOWED_NUMBERS:
          print(f"WhatsApp mesajı gönderiliyor -> {phone} ...")
          success = send_whatsapp_message(phone, response_text)
          if success:
            print(f"✅ Mesaj {phone} numarasına başarıyla iletildi!")
          else:
            print(f"❌ HATA: Mesaj {phone} numarasına GÖNDERİLEMEDİ!")
  else:
    print("Sunucu başlatılıyor...")
    app.run(port=5000, debug=True)
