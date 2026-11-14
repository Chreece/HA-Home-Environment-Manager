<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="首页环境经理 - 智能化空气质量,舒适性,通风和气候控制" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="支持希腊 Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <strong>简体中文</strong> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - 家庭环境经理

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM 标志" width="420">
</p>

<p align="center"><strong>您的整个家庭环境,在一个 Home Assistant 卡片.</strong></p>

**HEM 帮助你的房子了解周围的环境并对每个房间的实际需求作出反应.** 它带来了你的 Home Assistant 传感器,天气数据,占用率信息和兼容的气候设备一起来监测空气质量,获得有用的通风建议,管理舒适性和自动化您选择的设备.

例如, HEM 在所有人不在的时候,可以减少加热,在返回之前准备选择的房间,在睡觉时使用不同的湿度目标,或者要求你在运行除湿器之前打开窗户. **监督和推 ⁇**没有控制任何设备.

**你继续负责.** 每个房间都有自己的设置. 每个支持的设备都有自己的控制器,操作模式,目标和安全限制. HEM 从来不认为选择设备允许操作该设备.

[探索这些特征](#what-can-hem-do) · [查看接口](#see-hem-in-action) · [安装 HEM](#installation) · [设置你的家](#getting-started) · [详细的指南](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## 什么可以 HEM 是不是?

| 你的情况 | 如何? HEM 可以帮助 |
| --- | --- |
| **房子是空的.** | 切换到"远离"目标,尊重每个房间的存在规则,避免不必要运行选定的设备. |
| **你正在回家的路上** | 压力 **准备到达** 对于符合条件的自动控制器,暂时使用家庭舒适目标,即使每个人都在外面. |
| **有人睡着了.** | 使用睡眠目标,减少风扇噪音,或者在每个被占用的房间都在睡觉时,关闭选择设备. |
| **一间房间很湿** | 与目标进行湿度和模具指标的比较,建议有用的空气化,或使用自动或 PID 控制. |
| **这里太阳很热.** | 在移动选择的阴影之前,评估室温,阳光,天气和连接的窗口接触. |
| **室外的空气看起来更好.** | 建议使用室内需求,室外污染,温度,湿度,风力和可用的花粉或天气警告进行通风. |
| **热器或TRV停止响应** | 显示其不可用或等待状态,保留其配置控制器,并报告支持设备故障,而不假设电池或继电器已恢复. |

这些都是例子,而不是行动 HEM 结果取决于你选择的传感器, Home Assistant 您的选择设置.

<a id="explore-the-features"></a>
## 探索这些特征

<a id="a-complete-home-dashboard"></a>
### 一个完整的家庭仪表板

其他 HEM 没有打开多个集成.

- 查看室外条件,空气质量以及是否建议进行通风.
- 一眼就比较所有监测室:温度,相对湿度, AQI,PM2.5,模具表示,光和其他支持的读数.
- 扩大任何空间详细测量,窗户和门信息,气候状况,活动控制器,等待原因和建筑物物理估计.
- 查看历史和趋势,查看哪些传感器为平均水平做出了贡献,并区分缺失的读数与测量值.
- 按实际的团体房间 Home Assistant 在没有楼层时,使用简单的房间列表.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### 家庭,每个房间和每个设备的不同设置

HEM 保持共享政策与地方决策分开.

| 设置级别 | 您可以设置什么 |
| --- | --- |
| **家庭** | 室外天气和污染来源,监测室,全球通风限制,家庭存在,准备抵达和发送公告. |
| **房间** | 室内温度和湿度来源,空气质量门 ⁇ ,窗户和门接触,睡眠和居住行为,房间特定的舒适目标,通风和阴影选择. |
| **单个设备** | 它的可用控制模式,自动/手动/PID 方法,每个配置文件的目标,传感器,静音风扇设置,最低运行时间,电源保护,窗口行为和设备错误通知. |

所有三个级别都可以通过卡片中的集成,可搜索的设置访问.需要时可提供高级控制,而不需要拥挤日常设置. Home Assistant 设置变化.

<a id="climate-control-and-pid-device-by-device"></a>
### 气候控制和 PID设备对设备

HEM 可以使用兼容的 Home Assistant **气候**, **⁇ 化器** 其他 **风扇** 包括加热,冷却,脱湿,加湿和支持的空气循环或空气清洁设备.

每个 **支持的物理操作模式**独立选择控制方法:

| 方法 | 这意味着什么 |
| --- | --- |
| **现有** | 停止使用现有控制器路径. |
| **自动** | 追随 HEM根据情况的测量需求,目标和许可. |
| **PID** | 使用基于反 ⁇ 的比例,整体和衍生控制,设备和测量支持它. |
| **手册** | 通过明确支持的请求和目标进行控制. |
| **关闭** | 保持控制器关闭, 遵守物理保护和反 ⁇ 要求. |

例如,一个空调可能使用 **PID 用于加热** 其他 **自动冷却**一个脱湿器可以有自己的 PID 符合条件的风扇可以使用 PID 当有适当的反 ⁇ 和特定目的控制时.

PID 是 **没有** 一个通用过关: HEM 只提供特定设备,操作模式和反 ⁇ 源可支持的方法.高级选项包括每模式调节和校准,建议/适应调整,安静操作和支持的阶段风扇设置.除非您明确选择限制自动适应,否则您会批准建议的变化.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### 在家里很舒服,在外面很经济.

HEM 可以选择 **舒适,家庭,远离,睡眠和环境** 根据家庭情况,房间证据以及您的明确选择.

- **在家和外面:** 根据经验证的家居存在,使用不同的加热,冷却和湿度目标.
- **房间存在:** 只需需要,只需其房间被占用,或者只有房间空.
- **睡眠:** 在所有被占用的房间都睡着的时候,选择的设备可以停下来.
- **环境:** 在设置时使用经济目标.当房间被验证为空时,一个封闭的室内门可以参与一个受保护的生态政策;如果房间满足其他条件,一个封闭的门本身并不证明房间是隔离的.
- **预备起床:** 使用设置的下一个报警源,在报警之前将自动睡眠放弃,并给符合条件的设备时间响应.

如果使用量,设备可用性或其他需要的证据不确定, HEM 不仅仅认为启动自动设备是安全的.

<a id="prepare-your-environment-before-you-arrive"></a>
### 在你到达之前,准备你的环境

**准备到达** 是一个已确认的远离家庭的定时行动. HEM这是家庭设备.

HEM 暂时应用配置 **家庭目标** 符合条件的自动/PID 控制器,以便在返回之前,房间可以开始加热,冷却或调节湿度. 这也可能暂时允许控制器通常仅限于被占领的房间, **只有在已有必要的物理控制许可时**.

准备并不是一个命令来启动一切.设备仍然需要真正的需求,有效的传感器和授权,并且必须尊重窗户,最低的关闭/关闭时间和自己的保护. 当有人到来时,操作结束,你取消它,或者配置的计时器到期. Home Assistant 重新启动不会重新启动全计时器.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### 风气建议,窗户,门和遮 ⁇

HEM 相比较 **一个房间需要什么** 在 **室外空气是否可以帮助**.

- 建议使用当前的室内测量,室外湿度,污染,温度,风,天气警报和可选花粉环境打开或关闭窗户.
- 使用选定的窗户和门接口来解释房间状况,避免把未知接触者视为已关闭.
- 选项请您在启动支持自动设备之前尝试打开窗口,然后在必要时,设置响应等待后继续正常控制.
- 使用门的信息来了解房间边界,通风预警和可选保护的环保行为.
- 使用适当的窗户,温度,天气,太阳升高和可选的照明证据来管理选中的窗户,窗 ⁇ 和阴影.

HEM 它不能自行打开窗户,仅仅是因为空气可以帮助.

<a id="humidity-mold-indication-and-air-quality"></a>
### 湿度,模具标志和空气质量

HEM 结合支持的读数,如 **温度,湿度,CO2,颗粒物,VOC, AQI和照明** 您可以使用的尺寸取决于您的房间的尺寸. Home Assistant 设置提供.

它的 **模具标示** 根据室内和室外温度和校准测量,在冷面上估计湿度条件.当正确配置时,它可以影响支持的自动湿度控制器的有效目标.

**模具标志是估计,而不是模具或 ⁇ 体检测器.** 缺失或过时的传感器数据不能证明基于模具的新设备命令是合理的.

<a id="announcements-diagnostics-and-protection"></a>
### 公告,诊断和保护

你可以通过配置 Home Assistant 通知,TTS/媒体播放器或 **广告中心**人工智能可以改变信息的表达方式; HEM物理控制的决定仍然是决定性的.

HEM 也包括设备特定的保护和诊断:

- 最低的 ON和 OFF 时间,最大的操作时间设置和支持的外部电源开关操作.
- 窗口和占用限制,手动转换操作和本地命令确认检查.
- 错误和不可用设备报告,每个设备可选择通知行为.
- 关闭后可选的监视犬,可在关闭命令后继续加热,监控和恢复尝试有限.
- 需要明确的等待原因,目前的运营状态和源源可用性,

**警报被禁时,安全界限仍然有效.** HEM 一个成功的指令发射,从来没有被视为证明设备的物理响应.

<a id="see-hem-in-action"></a>
## 看看 HEM 在行动中

这些英语插图使用了样本室和测量,它们展示了接口,而不是显示了特定房屋的实体数据.

<a id="home-at-a-glance"></a>
### 在一眼,回家

在一个卡片中获取通风建议,天气条件和每个监控室的状态.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM 在五间房间内提供通风咨询和环境检测仪表板" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### 扩大一个房间.

检查空气质量,模具标志,存在,窗户状态,气候控制器以及每个决定的解释.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="扩展式浴室仪表板,具有读数和独立设备控制器" width="760">
</p>

<a id="home-settings"></a>
### 家庭设置

管理户外来源,全屋存在,监控室,通风限制,准备和通知.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM 家庭设置与可搜索的组和源和房间管理" width="900">
</p>

<a id="room-settings"></a>
### 房间设置

选择对每个房间有什么重要:自己的传感器,目标,占用量,门,窗户,通风,阴影和保护措施.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="集成 HEM 感应器,设备控制,睡眠,窗户和保护的室内设置" width="760">
</p>

<a id="device-settings"></a>
### 设备设置

调整一个设备而不改变其他设备,包括支持的控制方法, PID,安静运行,时间和故障报告.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="集成 HEM 设备设置与控制, PID电力保护和通知" width="900">
</p>

<a id="getting-started"></a>
## 开始

1. **整理自己的房间.** 在 Home Assistant建立或检查您的区域,并分配适当的传感器和设备.
2. **选择什么要监控.** 添加 HEM您可以选择您关心的房间,并查看建议的温度,湿度,窗口,空气质量和设备来源.
3. **配置共享信息.** 选择可用的户外天气/空气质量来源,家庭占用率的证据以及您想要的任何公告目的地.
4. **加入卡片.** 在编辑模式下打开仪表板,然后添加 **家庭环境经理** 首先要进行室内监测,读数和通风建议.
5. **只有在有用的地方才能启用控制.** 打开一个房间,选择一个支持的设备,查看其控制器,并明确选择自动或 PID 对于你想要的模式 HEM 运作.

你知道. **没有** 在每个房间都需要一个智能设备. 首先要使用你拥有的传感器,然后一次推出一个自动控制设备.

<a id="add-the-card-manually"></a>
### 手动添加卡

如果您更喜欢YAML,请使用:

~~~yaml
type: custom:home-environment-manager-card
~~~

如果你的 Home Assistant 设备有多个 HEM 建议传感器,您可能需要设置适当的 **实体** 显而易见:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

关于房间源,配置文件的步骤说明 PID 设置,窗口政策,准备,模具校准,太阳能遮阳和公告交付,使用 [详细的配置指南](../../docs/advanced-configuration.md).

<a id="installation"></a>
## 装备

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant 社区商店

1. 开放 **HACS** 在 Home Assistant.
2. 添加 **希腊/希腊/HA-Home-Environment-Manager** 作为 **定制存储库** 在 **整合** 如果尚未列出类别.
3. 找到 **家庭环境经理** 然后安装它.
4. 重启 **Home Assistant** 为了加载集成.
5. 走去 **设置 → 设备和服务 → 添加集成**搜索 **家庭环境经理** 然后完成设置.

<a id="manual-installation"></a>
### 手动安装

复制库的文件 **客户端_组件/环境_管理器** 在匹配文件 ⁇ 中 **定制_组件** 在您的目录中 Home Assistant 配置,保持目录名称 **环境_管理器**重新启动 Home Assistant 并通过 **设置 → 设备和服务**.

对于随后的安装更改,请保留现有的 HEM 如果卡的外观不立即更新,请重新加载浏览器中的仪表板.

<a id="common-questions"></a>
## 常见问题

**我可以用吗? HEM 没有给它控制我的设备?**

监测,测量,通风建议,历史和许多环境指示都没有启动设备的操作.

**威尔 HEM 它会自动控制它发现的每一个设备?**

您选择您想要管理的物理设备,并明确选择支持模式的控制方法.传感器资格和本地设备功能仍然决定了什么是可能的.

**每个设备都支持 PID?**

没有. HEM 支持 PID 对于 **有资格** 如果设备和选定的测量提供了必要的功能和反 ⁇ ,加热,冷却,湿度或风扇控制路径. PID 控制.

**我可以给每个房间不同的规则吗?**

是的. 居住条件,睡眠行为,来源,目标和一些安全偏好可以因房间而不同,而每个物理设备都有自己的操作和保护设置.

**可以 HEM 在我不在的时候准备我的家?**

是的. **准备到达** 暂时允许有资格的,已经授权的自动控制器使用限期的家庭目标.它不会绕过物理保护或保证目标将被达到.

**⁇ 通风的好建议能否打开我的窗户?**

无.它解释了空气化可能有什么帮助.自动运动是有资格的支持色调或盖子的单独选择功能,

**如果传感器或设备无法使用呢?**

HEM 系统可以将未知数据与实际数据区分开来,尽可能保留配置的控制器信息,并揭示等待原因和诊断.

<a id="help-and-troubleshooting"></a>
## 帮助和故障解决

如果有些问题,请检查相关的房间或控制器. **原因**, **诊断**,源可用性和当前控制方法. [详细的配置指南](../../docs/advanced-configuration.md) 涵盖常见等待状态,存在政策, PID 资格,窗户和设备响应故障解决.

对于可复制的问题, [打开一个 GitHub 问题](https://github.com/Chreece/HA-Home-Environment-Manager/issues) 通过预期的行为,实际行为,相关的房间/设备设置和复制的步骤. 从日志和图像中删除私人信息.

贡献和改进是受欢迎的. [贡献](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## 支持和许可证

如果 HEM 这对你有用,你可以 [支持希腊在Ko-fi](https://ko-fi.com/chreece).

在 [麻省理工学院许可证](../../LICENSE).
