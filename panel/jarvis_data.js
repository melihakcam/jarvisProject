/* ============================================================
   JARVIS - Günlük Veri Dosyası
   ------------------------------------------------------------
   Panelin gösterdiği DEĞİŞKEN verileri burada tutulur.
   Hatırlatıcıları / ajandayı / uyarıları güncellemek için
   sadece bu dosyayı düzenle; panel (index.html) her açılışta
   ve her 5 saniyede bir bu dosyayı yeniden okur.

   JARVIS bu dosyayı otomatik güncelleyebilir (ör. sesli
   "bana 15:00'e toplantı hatırlat" komutu bu listeye ekler).
   ============================================================ */

window.JARVIS_DATA = {
  // Üst köşedeki sürüm etiketi
  version: "v9.4",

  // Hava durumu kartı (sol sütun)
  weather: {
    city: "İSTANBUL",
    temp: "28°",
    desc: "Parçalı Bulutlu",
    meta1: "NEM %52 · RÜZGAR 11 km/s",
    meta2: "HİSSEDİLEN 30° · UV 6"
  },

  // BUGÜNÜN AJANDASI / HATIRLATICILAR  (sağ sütun)
  // Yeni hatırlatıcı eklemek için bu listeye bir satır ekle:
  //   { time: "16:30", title: "Diş randevusu", meta: "HATIRLATICI" }
  agenda: [
    { time: "09:30", title: "Ürün senkronizasyonu",          meta: "4 KİŞİ · GÖRÜNTÜLÜ" },
    { time: "11:00", title: "Derin çalışma bloğu",           meta: "BİLDİRİMLER SUSTURULACAK" },
    { time: "14:15", title: "Yatırımcı güncellemesi taslağı", meta: "SON TARİH BUGÜN" },
    { time: "19:00", title: "Antrenman · üst vücut",         meta: "SPOR SALONU" }
  ],

  // DİKKAT GEREKTİREN  (amber uyarı kartı)
  alerts: [
    { text: "Depolama %86 dolu — eski derlemeleri arşivle." },
    { text: "İki abonelik 3 gün içinde yenilenecek." }
  ],

  // BAĞLANTI DURUMLARI
  // dot renkleri: yeşil "#6effc0", camgöbeği "#5fe0ff", amber "#ffb35c"
  links: [
    { name: "UYDU BAĞI",         status: "KİLİTLİ",     dot: "#6effc0", glow: "rgba(110,255,192,.6)" },
    { name: "YEREL AĞ",          status: "12ms",        dot: "#6effc0", glow: "rgba(110,255,192,.6)" },
    { name: "BULUT ÇEKİRDEĞİ",   status: "SENKRON",     dot: "#5fe0ff", glow: "rgba(95,224,255,.6)" },
    { name: "BİYOMETRİK",        status: "DOĞRULANDI",  dot: "#5fe0ff", glow: "rgba(95,224,255,.6)" },
    { name: "DIŞ API AĞ GEÇİDİ", status: "KISITLI",     dot: "#ffb35c", glow: "rgba(255,179,92,.55)" }
  ],
  linkSummary: "4/5 STABİL",

  // Başlangıç sistem kaydı satırları (footer)
  logs: [
    { line: "[08:42:11] biyometrik doğrulama başarılı — hoş geldin.",           color: "rgba(160,215,240,.75)" },
    { line: "[08:42:12] 14 cihaz keşfedildi, 3 tanesi otomatik eşleştirildi.",  color: "rgba(160,215,240,.55)" },
    { line: "[08:42:14] yedekleme tamamlandı — 42.8 GB şifrelendi.",            color: "rgba(110,255,192,.7)" }
  ]
};
