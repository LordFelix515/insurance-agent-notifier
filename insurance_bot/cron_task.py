# -*- coding: utf-8 -*-
import os
import sys

# Windows terminal UTF-8 character support (emojis and Turkish characters)
if hasattr(sys.stdout, "reconfigure"):
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
  sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from bot import get_expiring_policies, send_whatsapp_message, ALLOWED_NUMBERS

def run_daily_cron():
    print("Google Sheets okunuyor (CRON)...")
    policies = get_expiring_policies(exact_days=15)
    
    if not policies:
        print("Bugün tam 15 günü kalan poliçe bulunamadı.")
        return

    header = "📅 *OTOMATİK BİLDİRİM: Tam 15 Günü Kalan Poliçeler:*\n\n"
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
    
    if not ALLOWED_NUMBERS:
        print("HATA: .env dosyasında hiç yetkili numara bulunamadı!")
        return

    import time
    for phone in ALLOWED_NUMBERS:
        print(f"WhatsApp mesajı gönderiliyor -> {phone} ...")
        success = send_whatsapp_message(phone, response_text)
        if success:
            print(f"✅ Mesaj {phone} numarasına başarıyla iletildi!")
        else:
            print(f"❌ HATA: Mesaj {phone} numarasına GÖNDERİLEMEDİ!")
        time.sleep(1)

if __name__ == "__main__":
    run_daily_cron()
