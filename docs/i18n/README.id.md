<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Home Pengelola Lingkungan - kualitas udara yang lebih cerdas, kenyamanan, ventilasi dan kontrol iklim" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Dukungan untuk Chreece Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <strong>Bahasa Indonesia</strong> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Home Pengelola Lingkungan

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Seluruh lingkungan rumah Anda, dalam satu Home Assistant kartu.</strong></p>

**HEM membantu rumah Anda memahami lingkungan dan bereaksi terhadap apa yang sebenarnya dibutuhkan setiap kamar.** Ini membawa Anda Home Assistant sensor, data cuaca, informasi penghuni dan perangkat iklim yang kompatibel bersama sehingga Anda dapat memantau kualitas udara, menerima saran ventilasi yang berguna, mengelola kenyamanan dan mengotomatisasi peralatan yang Anda pilih.

Sebagai contoh, HEM dapat mengurangi pemanasan saat semua orang pergi, mempersiapkan kamar yang dipilih sebelum Anda kembali, menggunakan target kelembaban yang berbeda saat Anda tidur, atau meminta Anda membuka jendela sebelum menjalankan desumidifier. **memantau dan merekomendasikan**, tanpa mengontrol perangkat apapun.

**Kau tetap bertanggung jawab.** Setiap kamar memiliki pengaturan sendiri. Setiap perangkat yang didukung memiliki pengontrol, mode operasi, target dan batas keamanan sendiri. HEM tidak pernah menganggap bahwa memilih perangkat memberikan izin untuk mengoperasikan perangkat itu.

[Menjelajahi fiturnya](#what-can-hem-do) · [Lihat antarmuka](#see-hem-in-action) · [Instal HEM](#installation) · [Buatlah rumahmu](#getting-started) · [Panduan terperinci](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Apa yang bisa HEM - Apa?

| Situasi Anda | Bagaimana? HEM dapat membantu |
| --- | --- |
| **Rumahnya kosong.** | Pindah ke Away target, menghormati aturan keberadaan setiap ruangan dan menghindari menjalankan peralatan yang dipilih tanpa perlu. |
| **Kau sedang dalam perjalanan pulang.** | Pencet **Bersiaplah untuk kedatangan** untuk sementara menggunakan target kenyamanan rumah untuk pengendali otomatis yang memenuhi syarat, meskipun semua orang masih jauh. |
| **Seseorang sedang tidur.** | Gunakan target tidur, kurangi kebisingan kipas, atau matikan perangkat yang dipilih saat setiap kamar yang sibuk tidur. |
| **Satu kamar basah** | Bandingkan indikasi kelembaban dan cetakan dengan target, sarankan udara yang berguna, atau mengoperasikan deshumidifier yang sah menggunakan Otomatis atau PID kontrol. |
| **Ini panas dan cerah** | Evaluasi suhu ruangan, sinar matahari, cuaca dan kontak jendela yang terhubung sebelum pindah warna yang dipilih. |
| **Udara luar terlihat lebih baik** | Rekomendasi ventilasi menggunakan permintaan dalam ruangan, polusi di luar ruangan, suhu, kelembaban, angin dan serbuk sari yang tersedia atau peringatan cuaca. |
| **Pemanas atau TRV berhenti merespon** | Tampilkan keadaan tidak tersedia atau menunggu, simpan kontroler yang dikonfigurasi dan laporkan kesalahan perangkat yang didukung tanpa berasumsi baterai atau rel telah pulih. |

Ini adalah contoh, bukan tindakan yang HEM Hasilnya tergantung pada sensor yang Anda pilih, setiap perangkat Home Assistant kemampuan dan pengaturan opt-in Anda.

<a id="explore-the-features"></a>
## Menjelajahi fiturnya

<a id="a-complete-home-dashboard"></a>
### Sebuah dashboard rumah lengkap

Pemberantasan HEM kartu memberikan gambaran umum yang berguna tanpa membuka beberapa integrasi.

- Lihat kondisi luar ruangan, kualitas udara dan apakah ventilasi disarankan.
- Bandingkan semua ruangan yang dipantau dengan sekilas: suhu, kelembaban relatif, AQI, PM2,5, indikasi jamur, cahaya dan bacaan pendukung lainnya.
- Perluas ruang untuk pengukuran rinci, informasi jendela dan pintu, status iklim, pengendali aktif, alasan menunggu dan perkiraan fisika bangunan.
- Lihat sejarah dan tren, lihat sensor mana yang berkontribusi pada rata-rata dan membedakan bacaan yang hilang dari nilai yang diukur.
- Ruang kelompok berdasarkan aktual Home Assistant lantai, atau menggunakan daftar kamar sederhana ketika Anda tidak memiliki lantai.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Setelan yang berbeda untuk rumah, setiap kamar dan setiap perangkat

HEM menjaga kebijakan bersama terpisah dari keputusan lokal.

| Tingkat pengaturan | Apa yang dapat Anda konfigurasi |
| --- | --- |
| **Rumah** | Cuaca di luar ruangan dan sumber polusi, kamar yang dipantau, batas ventilasi global, kehadiran rumah tangga, persiapan kedatangan dan pengiriman pengumuman. |
| **Kamar** | Sumber suhu dan kelembaban dalam ruangan, ambang-ambang kualitas udara, kontak jendela dan pintu, perilaku tidur dan tempat tinggal, target kenyamanan khusus ruangan, pilihan ventilasi dan bayangan. |
| **Perangkat individual** | Mode kontrol yang tersedia, Otomatis/Manual/PID metode, target per profil, sensor, pengaturan kipas yang tenang, waktu operasi minimum, perlindungan daya, perilaku jendela dan pemberitahuan kesalahan perangkat. |

Semua tiga tingkat dapat diakses melalui pengaturan yang dikelompokkan dan dapat dicari di kartu. Kontrol lanjutan tersedia ketika diperlukan, tanpa menggenangi pengaturan sehari-hari. Anda dapat menyegarkan pilihan sumber sebagai pilihan Anda Home Assistant perubahan pengaturan.

<a id="climate-control-and-pid-device-by-device"></a>
### Pengendalian iklim dan PID, perangkat demi perangkat

HEM dapat bekerja dengan kompatibel Home Assistant **iklim**, **humidifier** dan **kipas angin** peralatan, termasuk peralatan pemanasan, pendinginan, desumidifikasi, humidifikasi dan dukungan sirkulasi udara atau pembersihan udara.

Untuk setiap **modus operasi fisik yang didukung**, memilih metode kontrol secara independen:

| Metode | Apa artinya |
| --- | --- |
| **Yang ada** | Tinggalkan operasi dengan jalur controller yang ada. |
| **Otomatis** | Ikuti HEMPermintaan yang diukur, sasaran dan izin berdasarkan situasi. |
| **PID** | Gunakan kontrol proporsional, integral dan turunan berbasis umpan balik di mana perangkat dan pengukuran mendukungnya. |
| **Manual** | Kontrol melalui permintaan dan target yang didukung secara eksplisit. |
| **Berhenti** | Jauhkan pengontrol itu mati, tertakluk pada perlindungan fisik dan persyaratan umpan balik. |

Misalnya, satu AC dapat menggunakan **PID Untuk Pemanasan** dan **Otomatis untuk pendingin**Dehumidifier bisa memiliki sendiri PID kalibrasi, target dan waktu siklus. penggemar yang memenuhi syarat dapat menggunakan PID ketika ada umpan balik dan kontrol khusus yang tepat.

PID adalah **Tidak** sebuah override universal: HEM hanya menawarkan metode yang dapat didukung oleh perangkat tertentu, mode operasi dan sumber umpan balik. opsi lanjutan termasuk penyesuaian dan kalibrasi per-modus, penyesuaian yang disarankan / adaptif, operasi tenang dan pengaturan kipas panggung yang didukung. Anda menyetujui perubahan yang disarankan kecuali Anda secara eksplisit memilih adaptasi otomatis terbatas.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Nyaman saat di rumah, ekonomis saat di luar

HEM dapat memilih di antara **Kenyamanan, Rumah, Perjalanan, Tidur dan Lingkungan** sasaran berdasarkan situasi rumah tangga, bukti kamar dan pilihan eksplisit Anda.

- **Home dan Away:** Gunakan tujuan pemanasan, pendinginan dan kelembaban yang berbeda tergantung pada kehadiran rumah yang diverifikasi.
- **Kehadiran kamar:** Gunakan perangkat yang memenuhi syarat setiap kali ada permintaan, hanya saat kamarnya ditempati, atau hanya ketika kamarnya kosong.
- **Tidur:** Pergunakan target di malam hari dan perilaku kipas yang lebih tenang.
- **Ekologi:** Gunakan tujuan ekonomi di mana dikonfigurasi. Pintu interior tertutup dapat berpartisipasi dalam kebijakan Eco yang dilindungi ketika kamar diverifikasi kosong dan kondisi lain dipenuhi; pintu tertutup saja tidak membuktikan ruangan terisolasi.
- **Persiapan untuk bangun tidur:** Gunakan sumber alarm berikutnya yang dikonfigurasi untuk meninggalkan Sleep otomatis sebelum alarm dan berikan waktu pada perangkat yang memenuhi syarat untuk merespon.

Jika penghuni, ketersediaan perangkat atau bukti lain yang diperlukan tidak pasti, HEM tidak hanya berasumsi itu aman untuk memulai perangkat otomatis.

<a id="prepare-your-environment-before-you-arrive"></a>
### Persiapkan lingkungan Anda sebelum Anda tiba

**Bersiaplah untuk kedatangan** Ini adalah tindakan yang dijadwalkan untuk sebuah rumah jauh yang dikonfirmasi. HEMIni perangkat rumah.

HEM secara sementara menerapkan konfigurasi **Target rumah tangga** untuk memenuhi syarat Automatic/PID kontroler sehingga ruangan dapat mulai pemanasan, pendinginan atau penyesuaian kelembaban sebelum Anda kembali. Ini juga dapat sementara memungkinkan kontroler yang biasanya terbatas pada ruangan yang dipekerjakan, **hanya jika ia sudah memiliki izin kontrol fisik yang diperlukan**.

Persiapan bukanlah perintah untuk mengaktifkan semuanya. Perangkat masih membutuhkan permintaan yang nyata, sensor dan otorisasi yang valid, dan harus menghormati jendela, waktu ON / OFF minimum dan perlindungan mereka sendiri. Tindakan berakhir ketika seseorang tiba, Anda membatalkannya, atau timer yang dikonfigurasi berakhir. Home Assistant restart tidak memulai timer penuh kembali.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Konseling ventilasi, jendela, pintu dan penyinaran

HEM membandingkan **apa yang dibutuhkan sebuah kamar** dengan **apakah udara di luar ruangan dapat membantu**.

- Rekomendasi membuka atau menutup jendela menggunakan pengukuran dalam ruangan saat ini, kelembaban di luar ruangan, polusi, suhu, angin, peringatan cuaca dan konteks serbuk sari opsional.
- Gunakan kontak jendela dan pintu yang dipilih untuk menjelaskan kondisi ruangan dan hindari memperlakukan kontak yang tidak diketahui sebagai tertutup.
- Opsional meminta Anda untuk mencoba membuka jendela sebelum memulai perangkat otomatis yang didukung, kemudian melanjutkan kontrol normal setelah respon yang dikonfigurasi menunggu jika diperlukan.
- Gunakan informasi pintu untuk kesadaran batas ruangan, peringatan ventilasi dan perilaku Eco yang terjaga secara opsional.
- Mengelola persilatan, blinds dan shades yang dipilih dengan menggunakan jendela, suhu, cuaca, ketinggian matahari dan bukti pencahayaan opsional yang sesuai.

HEM bisa memberikan saran ventilasi tanpa jendela yang dapat dikendalikan.

<a id="humidity-mold-indication-and-air-quality"></a>
### Kelembaban, indikasi jamur dan kualitas udara

HEM menggabungkan pembacaan yang didukung seperti **suhu, kelembaban, CO2, partikel, VOC, AQI dan pencahayaan** Untuk membantu Anda memahami setiap ruangan. Home Assistant pengaturan menyediakan.

Itu **indikasi cetakan** estimasi kondisi kelembaban pada permukaan dingin dari suhu ruangan dan luar dan pengukuran kalibrasi. Jika dikonfigurasi dengan benar, dapat mempengaruhi target efektif pengontrol kelembaban otomatis yang didukung.

**Indikasi jamur adalah perkiraan, bukan detektor jamur atau spora.** Data sensor yang hilang atau usang tidak dapat membenarkan perintah perangkat berbasis cetakan baru.

<a id="announcements-diagnostics-and-protection"></a>
### Pengumuman, diagnostik dan perlindungan

Anda dapat mengirim rekomendasi dan peringatan yang relevan melalui konfigurasi Home Assistant pemberitahuan, pemutar media TTS atau **Hub Pengumuman**AI dapat mengubah cara pesan difrase; HEMKeputusan kontrol fisik tetap deterministik.

HEM juga mencakup perlindungan dan diagnostik khusus perangkat:

- Minimal ON dan OFF durasi, pengaturan waktu operasi maksimum dan dukungan pengendalian switch listrik eksternal.
- Pembatasan jendela dan tempat tinggal, penanganan manual dan pemeriksaan konfirmasi perintah asli.
- Pelaporan kesalahan dan perangkat tidak tersedia, dengan pilihan perilaku pemberitahuan untuk setiap perangkat.
- Opt-on penjaga pasca penutupan untuk dugaan pemanasan berkelanjutan setelah perintah OFF, dengan pemantauan yang terjaga dan upaya pemulihan terbatas.
- Alasan menunggu yang jelas, status operasi saat ini dan ketersediaan sumber, sehingga Anda dapat menyelidiki sebelum memungkinkan lebih banyak kontrol.

**Batas keamanan tetap berlaku bahkan ketika peringatan tidak aktif.** HEM tidak pernah memperlakukan pengiriman perintah yang berhasil sebagai bukti bahwa perangkat secara fisik menanggapi.

<a id="see-hem-in-action"></a>
## Lihatlah HEM dalam tindakan

Ilustrasi berbahasa Inggris ini menggunakan sampel kamar dan pengukuran. Mereka menunjukkan antarmuka daripada menunjukkan data langsung dari rumah tertentu.

<a id="home-at-a-glance"></a>
### Rumah dalam sekejap

Dapatkan saran ventilasi, kondisi cuaca dan status setiap ruangan yang dipantau dalam satu kartu.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM home dashboard dengan nasihat ventilasi dan pembacaan lingkungan di lima kamar" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Perluas ruang untuk detail lengkap

Periksa kualitas udara, indikasi jamur, keberadaan, keadaan jendela, pengendali iklim dan penjelasan untuk setiap keputusan.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Dashboard kamar mandi yang diperluas dengan pembacaan dan pengontrol perangkat independen" width="760">
</p>

<a id="home-settings"></a>
### Home Settings

Mengelola sumber di luar ruangan, kehadiran di seluruh rumah, ruangan yang dipantau, batas ventilasi, persiapan dan pemberitahuan.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Pengaturan rumah dengan kelompok yang dapat dicari dan manajemen sumber dan kamar" width="900">
</p>

<a id="room-settings"></a>
### Setelan kamar

Pilih apa yang penting untuk setiap ruangan: sensor sendiri, target, tempat tinggal, pintu, jendela, ventilasi, bayangan dan perlindungan.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Kelompok HEM pengaturan ruangan untuk sensor, kontrol perangkat, tidur, jendela dan perlindungan" width="760">
</p>

<a id="device-settings"></a>
### Pengaturan perangkat

Penyesuaian halus satu perangkat tanpa mengubah yang lain, termasuk metode kontrol yang didukung, PID, operasi diam, waktu dan laporan kesalahan.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Kelompok HEM pengaturan perangkat dengan kontrol, PID, perlindungan listrik dan pemberitahuan" width="900">
</p>

<a id="getting-started"></a>
## Memulai

1. **Perbaiki kamarmu.** Dalam Home Assistant, membuat atau memeriksa Area Anda dan menetapkan sensor dan perangkat yang tepat untuk setiap.
2. **Pilih apa yang akan dipantau.** Tambahkan HEM, pilih kamar yang Anda sukai dan meninjau suhu, kelembaban, jendela, kualitas udara dan sumber perangkat yang disarankan.
3. **Mengkonfigurasi informasi bersama.** Pilih sumber cuaca luar ruangan / kualitas udara yang tersedia, bukti pekerjaan rumah tangga dan tujuan pengumuman apa pun yang Anda inginkan.
4. **Tambahkan kartu.** Buka dashboard dalam mode edit dan tambahkan **Home Pengelola Lingkungan** Mulailah dengan pemantauan kamar, pembacaan dan saran ventilasi.
5. **Mengaktifkan kontrol hanya di mana berguna.** Buka ruangan, pilih perangkat yang didukung, meninjau pengontrolnya dan secara eksplisit pilih Otomatis atau PID untuk mode yang Anda inginkan HEM untuk beroperasi.

Kau tahu. **Tidak** mulai dengan sensor yang Anda miliki, dan memperkenalkan kontrol otomatis satu perangkat pada satu waktu.

<a id="add-the-card-manually"></a>
### Tambahkan kartu secara manual

Integrasi biasanya mendaftarkan kartu Lovelace sendiri. jika Anda lebih memilih YAML, gunakan:

~~~yaml
type: custom:home-environment-manager-card
~~~

Jika Anda Home Assistant instalasi memiliki lebih dari satu HEM sensor rekomendasi, Anda mungkin perlu mengatur sensor yang tepat **entitas** dengan jelas:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Untuk instruksi langkah demi langkah tentang sumber kamar, profil, PID pengaturan, kebijakan jendela, persiapan, kalibrasi cetakan, solar shading dan pengumuman pengiriman, menggunakan [panduan konfigurasi terperinci](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Instalasi

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Toko Komunitas

1. Terbuka **HACS** di Home Assistant.
2. Tambahkan **https://github.com/Chreece/HA-Home-Environment-Manager** sebagai **repositori khusus** dalam **Integrasi** kategori jika belum terdaftar.
3. Temukan **Home Pengelola Lingkungan** dan menginstalnya.
4. Mulai ulang **Home Assistant** untuk memuat integrasi.
5. Pergilah ke **Pengaturan → Perangkat & Layanan → Tambahkan integrasi**, mencari untuk **Home Pengelola Lingkungan** dan menyelesaikan pengaturan.

<a id="manual-installation"></a>
### Instalasi manual

Salin dari repositori **custom_components/environment_manager** folder ke dalam matching **custom_components** direktori dalam Home Assistant konfigurasi, menjaga nama direktori **environment_manager**Mulai ulang . Home Assistant dan menambahkan integrasi melalui **Pengaturan → Perangkat & Layanan**.

Untuk perubahan instalasi berikutnya, simpan HEM input dan pengaturan integrasi. Cari ulang dashboard di browser Anda jika tampilan kartu tidak segera diperbarui.

<a id="common-questions"></a>
## Pertanyaan umum

**Bisakah aku menggunakannya? HEM tanpa memberikannya kendali perangkatku?**

Pemantauan, pengukuran, saran ventilasi, sejarah dan banyak indikasi lingkungan bekerja tanpa memungkinkan penggerak perangkat.

**Will. HEM mengontrol setiap perangkat yang ditemukan?**

Tidak. Anda memilih perangkat fisik yang ingin Anda mengelola dan secara eksplisit memilih metode kontrol untuk mode yang didukung. Kelayakan sensor dan kemampuan perangkat asli masih menentukan apa yang mungkin.

**Apakah setiap peralatan mendukung PID?**

Tidak, tidak. HEM dukungan PID untuk **yang layak** jalur pemanasan, pendinginan, kelembaban atau kontrol kipas ketika peralatan dan pengukuran yang dipilih memberikan kemampuan dan umpan balik yang diperlukan. PID kontrol.

**Bisakah aku memberi setiap kamar aturan yang berbeda?**

Ya. Kondisi penghunian, perilaku tidur, sumber, target dan beberapa preferensi keamanan dapat berbeda menurut ruangan, sementara setiap perangkat fisik memiliki pengaturan operasi dan perlindungan tersendiri.

**Bisa HEM mempersiapkan rumahku saat aku pergi?**

Ya, aku tahu. **Bersiaplah untuk kedatangan** sementara memungkinkan pengendali otomatis yang layak, yang sudah diberi wewenang untuk menggunakan target rumah untuk jangka waktu terbatas.

**Apakah rekomendasi untuk ventilasi membuka jendela saya?**

Tidak. Ini menjelaskan kapan ventilasi dapat membantu. Pergerakan otomatis adalah fitur terpisah, opt-in untuk shades atau penutup yang mendukung yang memenuhi syarat, tertakluk pada pemeriksaan keselamatan mereka sendiri.

**Bagaimana jika sensor atau perangkat tidak tersedia?**

HEM memisahkan data yang tidak diketahui dari pembacaan nyata, menyimpan informasi pengontrol yang dikonfigurasi jika memungkinkan dan mengekspos alasan menunggu dan diagnostik. Kontrol otomatis masih membutuhkan otoritas dan bukti yang valid saat ini.

<a id="help-and-troubleshooting"></a>
## Bantuan dan pemecahan masalah

Jika sesuatu tampak salah, periksa kamar yang relevan atau controller **Alasan**, **Diagnosis**, ketersediaan sumber dan metode kontrol saat ini. [panduan konfigurasi terperinci](../../docs/advanced-configuration.md) mencakup keadaan menunggu umum, kebijakan kehadiran, PID eligibility, windows dan pemecahan masalah respon perangkat.

Untuk masalah yang dapat direproduksi, [membuka a GitHub isu](https://github.com/Chreece/HA-Home-Environment-Manager/issues) dengan perilaku yang diharapkan, perilaku sebenarnya, pengaturan ruangan/perangkat yang relevan dan langkah untuk direproduksi. Hapus informasi pribadi dari log dan gambar.

Kontribusi dan perbaikan dapat diterima. [Kontributing.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Dukungan dan lisensi

Jika HEM berguna bagi Anda, Anda bisa [dukungan untuk Kroasia pada Ko-fi](https://ko-fi.com/chreece).

Didistribusikan dalam [Lisensi MIT](../../LICENSE).
