# TP-Link EX530v Configuration Tool

Bu araç, **TP-Link EX530v (Volcano Platformu)** model router cihazlarının yedekleme dosyalarını (`.bin`) deşifre etmek, sıkıştırmasını açmak ve düzenlendikten sonra tekrar paketlemek için geliştirilmiştir.

## 🚀 Özellikler

* **Çift Yönlü İşlem:** `.bin` -> `.xml` (Ayrıştırma) ve `.xml` -> `.bin` (Şifreleme).
* **Otomatik Bağımlılık Yönetimi:** Gerekli olan `pycryptodome` kütüphanesi yüklü değilse otomatik olarak kurar.
* **Gerçek LZ77 Sıkıştırma:** Dosya boyutunu orijinal seviyesinde tutmak için gelişmiş "match-finding" algoritması kullanır.
* **Windows Entegrasyonu:** İşlem başarıyla tamamlandığında Windows kullanıcıları için görsel bildirim kutusu açar.
* **Hız ve Güvenlik:** MD5 bütünlük kontrolü ve DES şifreleme katmanlarını eksiksiz uygular.

## 🛠️ Kurulum

Bilgisayarınızda Python 3 yüklü olması yeterlidir. Script, ilk çalıştırmada eksik kütüphaneleri kendisi tamamlayacaktır.

Bulunan Şifre: u8hBWA7x9L
