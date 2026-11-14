<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="家庭環境經理 - 更聰明的空氣質量,舒適性,通風和氣候控制" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="支持希臘 Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <strong>繁體中文</strong>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - 家庭環境經理

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM 標誌" width="420">
</p>

<p align="center"><strong>整個家的環境, Home Assistant 這是一張卡片.</strong></p>

**HEM 幫助你的家了解周圍的環境,** 這會帶來你的 Home Assistant 檢測空氣質量,獲得有用的通風諮詢,管理舒適性和自動化您選擇的設備.

這種情況, HEM 在所有人都不在的時候, 能減少加熱, 在你回來之前準備選定的房間, 在你睡覺時使用不同的湿度目標, **監控和推薦**沒有控制任何裝置.

**請您繼續閱讀更多內容** 每個房間都有自己的設定. 每個支持的儀器都有自己的控制器,操作模式,目標和安全限制. HEM 沒有假設選擇裝置會允許使用該裝置.

[探索這些特點](#what-can-hem-do) · 其他國家 [查看接口](#see-hem-in-action) · 其他國家 [設置 HEM](#installation) · 其他國家 [建立自己的家](#getting-started) · 其他國家 [詳細的指南](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## 什麼可能會 HEM 沒有?

| 你的情況 | 如何? HEM 能幫助 |
| --- | --- |
| **這間房子是空的** | 切換到"離開"目標, 尊重每間房間的存在規則, |
| **你在回家的路上** | 按一下 **準備到來** 能暫時使用符合条件的自動控制器的家庭舒適目標, |
| **有誰睡著?** | 在每個被佔用的房間都睡著的時候, |
| **這間房間有一間很潮湿** | 比較它的湿度和模具表示與目標,建議有用的空氣化,或使用自動或 PID 控制的情況. |
| **這裡很熱,很陽光.** | 在移動選擇的色彩之前, 評估室溫,陽光,天氣和連接的窗口接觸. |
| **室外空氣看起來更好.** | 建議使用室內需求,室外污染,溫度,水分,風力以及可用的花粉或天氣警告進行通風. |
| **暖氣或TRV停止反應** | 顯示其無法使用或待機狀態,保留其配置的控制器,並報告支持的裝置故障,而不假設電池或連接已恢復. |

這些都是例子, HEM 每個家庭都會受到影響. Home Assistant 您的選項設定.

<a id="explore-the-features"></a>
## 探索這些特點

<a id="a-complete-home-dashboard"></a>
### 完整的家庭儀表板

其他國家 HEM 沒有打開多個整合.

- 檢查室外環境,空氣質量以及是否適宜換氣.
- 在一 ⁇ 眼下, 比較所有監控的房間:溫度,相對湿度, AQI, PM2.5,模具表示,光和其他可支持的數據.
- 提供詳細的測量空間,窗口與門口資訊,氣候狀態,活動控制器,等待原因及建築物物理估算.
- 查看歷史和趨勢,查看哪些傳感器為平均數量做出貢獻,
- 按實際數量排名 Home Assistant 或使用一個簡單的房間列表,

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### 每個房間,每個裝置都有不同的設定

HEM 保持共享政策與地方決策分離.

| 設定水平 | 您可以設定的 |
| --- | --- |
| **在家裡** | 室外氣候和污染來源,監控室,全球通風限制,家庭存在,預備抵達和發布通知. |
| **房間** | 室內溫度和水分來源,空氣質量 ⁇ 值,窗戶和門口的接觸,睡眠和居住行為,房間特定的舒適目標,通風和遮蔽選擇. |
| **單個裝置** | 它的可用控制模式,自動/手動/PID 方法,每個配置文件的目標,傳感器,靜音風扇設定,最低運行時間,電源保護,窗口行為和裝置錯誤通知. |

在卡片中,所有三個層面都可以透過組成的搜索可用的設定, 當需要時可提供先进的控制, Home Assistant 設定的變化.

<a id="climate-control-and-pid-device-by-device"></a>
### 氣候控制和 PID裝置別裝置

HEM 可以與相容的 Home Assistant **氣候**, **氣化器** 及其他 **扇風機** 包括加熱,冷卻,除湿,加湿和支持的空氣循環或空氣清潔設備.

每個國家 **支持的物理操作模式**獨立地選擇控制方法:

| 方法 | 這是什麼意思? |
| --- | --- |
| **目前存在的** | 停止使用現有控制器路徑. |
| **自動使用** | 接下來 HEM數據顯示了需求量, 基于情況的目標和許可. |
| **PID** | 使用以反 ⁇ 為基礎的比例,整體和衍生控制,當裝置和測量支持它. |
| **預覽** | 透過明顯支持的要求和目標進行控制. |
| **關閉** | 請將該控制器關閉, |

例如,一台空調機可能使用 **PID 供供暖** 及其他 **自動冷卻**⁇ 除水器可以擁有自己的 PID 能獲得資格的球迷可以使用 PID 當有適當的反 ⁇ 和特定目的控制時.

PID 是的 **沒有** 一種普遍的覆蓋: HEM 只提供特定裝置,操作模式和反 ⁇ 來源可支持的方法.先進的選項包括每模式調節和校準,建議/適應調整,靜音操作和支持的階段風扇設定.除非您明顯選擇限制自动調整,否則您會承認建議的變更.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### 在家裡很舒服, 在外面很經濟.

HEM 能選擇 **舒適,家庭,遠離,睡眠與生態** 根據家庭情況,房間證據以及您的明顯選擇.

- **在家和外國:** 使用不同的加熱,冷卻和潮湿目標,
- **房間的存在:** 只需使用適當的裝置, 只需使用室內或空室.
- **睡眠時間:** 在所有被佔用的房間都睡著時,
- **環保:** 使用經濟目標在設定時. 封閉的室內門可在室內驗證空白和其他條件時參與保護的生態政策; 封閉的門本身並不證明室內隔離.
- **預備醒來:** 使用配置的下一個警報源, 在警報之前自動休眠, 給符合条件的裝置反應時間.

如果使用時間,裝置可用性或其他需要的證據不確定, HEM 不只是認為開啟自動裝置是安全的.

<a id="prepare-your-environment-before-you-arrive"></a>
### 在您抵達之前,準備您的環境

**準備到來** 請從卡片頭頭開始, HEM這是家庭裝置.

HEM 暫時使用設定的 **家庭目標** 適用於自动/PID 控制器,以便在您回來之前,房間可以開始加熱,冷卻或調整湿度. 這也可能會暫時允許控制器通常限制在被佔用的房間, **只有當它已經有必要的物理控制許可證**.

準備並不是將一切啟動的命令. 裝置仍然需要真正的需求,有效的傳感器和授權,并且必須尊重窗戶,最低的開關/關閉時間和自己的保護. Home Assistant 如果重新啟動,

<a id="ventilation-advice-windows-doors-and-shading"></a>
### 換氣,窗戶,門戶和遮 ⁇ 的建議

HEM 比較 **房間需要什麼** 在 **室外空氣是否可以幫助**.

- 建議使用當前室內測量,室外潮湿,污染,溫度,風,天氣警報和可選的花粉背景,開或關閉窗口.
- 使用選定的窗口與門接觸方式來說明房間狀況,
- 請試圖打開窗口,然後繼續正常控制, 如果需要,
- 請使用門的資訊, 了解室內邊界,通風預警和可選保護生態行為.
- 使用適當的窗口,溫度,天氣,太陽升高和可選的照明證據,

HEM 沒有任何可控制的窗口, 它不會單獨打開窗口,

<a id="humidity-mold-indication-and-air-quality"></a>
### 湿度,模具表示和空氣質量

HEM 結合支持的讀數,如 **溫度,湿度,二氧化碳,2颗粒物,VOC, AQI和照明** 您的房間的數量取決於您的房間的數量. Home Assistant 這項方案是:

該組織的 **模具表示** 在室內和室外溫度和校准測量下, 估算冷面的水分狀況.

**模具表示是估計, 而不是模具或斑點探測器.** 缺失或舊式的傳感器數據不能合理化新的基于模具的裝置指令.

<a id="announcements-diagnostics-and-protection"></a>
### 公告,診斷與保護

您可以透過配置的 Home Assistant 通知,TTS/媒體播放器或 **廣告中心**AI可以改變訊息的表達方式; HEM身體控制的決定仍然是決定性的.

HEM 也包括特定裝置的保護和診斷:

- 最低的開關和關閉時間,最大的運作時間設定和支持的外部電源開關處理.
- 窗口和佔用限制,手動轉移操作和本地命令确认檢查.
- 檢測錯誤和無法使用的裝置報告,並選擇每個裝置的通知行為.
- 在停電命令後,可選擇停電後的監控犬,
- 這樣你就可以在更大的控制之前進行調查.

**警報被禁用時,安全界限仍然有效.** HEM 沒有成功的指令發送,

<a id="see-hem-in-action"></a>
## 請看看 HEM 在行動中

這些英文插圖使用了模範室和測量.

<a id="home-at-a-glance"></a>
### 在一 ⁇ 眼中,

請在一張卡上獲得通風,天氣狀況及每間監控室的狀況.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM 在五個房間內提供通風輔導和環境檢測的家庭儀表板" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### 提供更多資訊.

檢查空氣質量,模具表示,存在,窗口狀態,氣候控制器以及每個決定的說明.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="浴室的擴展式儀表板,有讀量和獨立的儀器控制器" width="760">
</p>

<a id="home-settings"></a>
### 家庭設定

管理室外來源,全屋存在,監控室,通風限制,準備和通知.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM 提供可搜索群組及源與房間管理的家庭設定" width="900">
</p>

<a id="room-settings"></a>
### 房間設定

選取各房間的重要因素:自己的傳感器,目標,佔用量,門,窗口,通風,遮蔽和保護措施.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="集成 HEM 感應器,裝置控制,睡眠,窗口和保護的室內設定" width="760">
</p>

<a id="device-settings"></a>
### 裝置設定

沒有更改其他裝置的一個裝置,包括支持的控制方法, PID沒有任何問題,

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="集成 HEM 裝置設定與控制, PID電力保護與通知" width="900">
</p>

<a id="getting-started"></a>
## 開始

1. **整理自己的房間.** 在 Home Assistant建立或檢查您的區域,
2. **選擇要監控什麼.** 加入 HEM請選擇您關心的房間,並檢查建議的溫度,湿度,窗口,空氣質量和裝置來源.
3. **設定共享資訊.** 選擇可用的戶外天氣/空氣質量來源,家庭占用率的證據,以及任何你想要的公告目的地.
4. **加入這個卡片.** 在編輯模式下打開顯示板, **家庭環境管理員** 請從室內監測,檢測和通風諮詢開始.
5. **只有在有用情況下才能啟動控制.** 打開房間,選擇支持的儀器,檢查其控制器, PID 為了你想要的模式 HEM 該如何運作?

你知道的. **沒有** 首先要使用您所擁有的傳感器,

<a id="add-the-card-manually"></a>
### 手動添加卡

如果您更喜歡YAML,請使用:

~~~yaml
type: custom:home-environment-manager-card
~~~

如果您的 Home Assistant 裝置有超過一台 HEM 您可能需要設定適當的 **單位** 明確表示:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

提供各式各樣的房間來源, PID 準備,模具校準,太陽能遮蔽和公告交付,使用 [詳細的配置指南](../../docs/advanced-configuration.md).

<a id="installation"></a>
## 裝置

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant 社區商店

1. 打開 **HACS** 在 Home Assistant.
2. 加入 **沒有任何相關資訊,** 作为一个 **定制資料庫** 在這個國家 **集成** 如果已沒有列出,
3. 找到 **家庭環境管理員** 並安裝它.
4. 重新啟動 **Home Assistant** 必須加載集成.
5. 走到 **設定 → 裝置與服務 → 添加集成**搜尋 **家庭環境管理員** 並完成設定.

<a id="manual-installation"></a>
### 手動安裝

複製資料庫的文件 **網站管理器/環境管理器** 在相匹配的文件 ⁇ 中 **定制_组件** 在您的目錄中 Home Assistant 配置,保持目錄名稱 **環境_管理員**請重新啟動 Home Assistant 並透過 **設定 → 裝置與服務**.

請將您的現有裝置存放在 HEM 如果卡的外觀並不立即更新,

<a id="common-questions"></a>
## 常見的問題

**我可以使用 HEM 沒有讓它控制我的裝置?**

是的. 監測,測量,通風,歷史及許多環境指示都沒有啟動裝置.

**威爾斯 HEM 自動控制它發現的每個裝置?**

您選擇您想要管理的物理裝置,並明顯選擇支持模式的控制方法.

**每個裝置都支持 PID?**

沒有. HEM 提供支持 PID 關於 **有資格使用** 如果裝置和選定的測量提供必要的功能和反 ⁇ ,加熱,冷卻,潮湿或風扇控制路徑. PID 控制的情況.

**我可以給每個房間不同的規則嗎?**

每個物理裝置都有自己的操作和保護設定.

**這樣可能 HEM 在我不在的時候準備我的家?**

沒有任何問題. **準備到來** 暫時允許有資格,已授權的自動控制器使用家庭目標為有限的時間.

**請問有沒有適合通風的推薦,**

沒有. 它說明空氣可能有什麼幫助. 自動移動是符合条件的支持色彩或蓋的獨立選擇功能,

**如果傳感器或裝置無法使用,**

HEM 在可能情況下保留配置的控制器信息,並揭示等待原因和診斷.

<a id="help-and-troubleshooting"></a>
## 幫助與解決問題

如果有些問題, 請查詢相關的房間或控制器. **原因**, **診斷結果**提供源源和目前的控制方法. [詳細的配置指南](../../docs/advanced-configuration.md) 涵蓋常見的等待狀態,存在政策, PID 選項,窗口和裝置反應問題解決.

這種問題可複製, [打開一個 GitHub 這個問題](https://github.com/Chreece/HA-Home-Environment-Manager/issues) 透過預期的行為,實際的行為,相關的空間/裝置設定及可複製的步骤.

歡迎提供貢獻和改善. [提供貢獻](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## 支持和授權

如果 HEM 這對你來說很有用, [支持希臘在 Ko-fi](https://ko-fi.com/chreece).

在該地區分佈 [麻省理工大學授權](../../LICENSE).
