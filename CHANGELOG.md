# BytePet 电子宠物 — 开发更新日志

> 版本：V1.3.20260725 | 日期：2026-07-25

---

## 一、项目初始化

- 基于 `BytePet.txt` 需求文档启动项目
- 技术栈：Python 3.8 + PyQt5 (5.15.11) + pywin32 + Pillow + rembg (AI抠图)
- 项目结构：`src/`（15个模块）、`assets/`（素材）、`data/`（运行时数据）

---

## 二、核心功能开发

### 2.1 基础框架
- **config.py** — 全局配置、路径管理、默认设置、用户配置读写
- **database.py** — SQLite 数据访问层（基础信息表 / 代办事务表 / 运行日志表）
- **single_instance.py** — 同名宠物单实例互斥锁（支持多开不同名）

### 2.2 界面与交互
- **name_dialog.py** — 启动对话框（取名 / 骰子随机名 / 性别 / 多开互斥）
- **pet_window.py** — 透明置顶无边框宠物窗口（拖动移动 / 滚轮缩放 / 右键菜单）
- **bubble.py** — 聊天气泡组件（圆角白底 + 小尾巴 / 淡入淡出 / 消息排队）
- **tray.py** — 系统托盘与右键功能菜单

### 2.3 动画与智能
- **animator.py** — 动作动画系统（素材加载 / 动作映射 / 帧驱动 / 模式切换）
- **activity.py** — 办公 / 游戏场景智能检测（前台窗口进程名识别）
- **desktop_icons.py** — 桌面图标采集（HICON → 透明 PNG）
- **reminders.py** — 提醒系统（久坐 45 分钟 + 代办定时）

### 2.4 辅助功能
- **todo_dialog.py** — 代办事项对话框
- **info_window.py** — 宠物基础信息窗口
- **about_dialog.py** — 关于对话框（版本 / 作者 / 联系方式）
- **version_badge.py** — 版本徽章（后移除，改为选择窗口显示）
- **autostart.py** — 开机自启动（注册表 HKCU\...\Run）

---

## 三、版本迭代记录

### V1.3 — 核心功能完善

#### 新增功能
| 日期 | 功能 | 说明 |
|------|------|------|
| 07-24 | 取名启动 | 输入名字（汉字/数字/字母）/ 骰子随机名（大白/一一/苗苗/小花花）/ 性别 MM/DD |
| 07-24 | 多开互斥 | 同名宠物只能开一个（Windows 命名互斥锁） |
| 07-24 | 透明置顶 | 无边框透明窗口 / 左键拖动 / 右下角手柄+滚轮缩放 |
| 07-24 | 聊天气泡 | 圆角白底+小尾巴 / 淡入淡出 / 自动定位宠物头顶 |
| 07-24 | 温馨提醒 | 每 45 分钟气泡提醒（伸懒腰/喝水/放松眼睛） |
| 07-24 | 代办事项 | 日期+时间+自定义内容 / 到点气泡提醒 |
| 07-24 | 三种模式 | 综合（默认）/ 文静 / 调皮 |
| 07-24 | 办公检测 | 游戏/全屏/WPS/Word/Excel/企业微信等不打扰 |
| 07-24 | 桌面图标采集 | 获取桌面图标 → 透明 PNG 本地保存 |
| 07-25 | 选择已有宠物 | 启动时若本地有数据，可勾选已有宠物进入或新建 |
| 07-25 | 版本显示 | 选择窗口右下角显示版本号 |
| 07-25 | 关于对话框 | 版本 / 作者 / 联系方式 |

#### Bug 修复
| 日期 | Bug | 修复 |
|------|-----|------|
| 07-24 | `VersionBadge(parent=app)` 崩溃 | QWidget 的 parent 不能是 QApplication，改为 `parent=None` |
| 07-24 | 气泡 QWidget paintEvent 不渲染 | 改用 QLabel + stylesheet 自绘背景 |
| 07-24 | 桌面图标 HICON 无效句柄 | pywin32 `SHGetFileInfo` 返回不可靠，改用 ctypes 直接调 `SHGetFileInfoW` |

---

### V1.3.20260725 — 功能增强

#### 新增功能
| 功能 | 说明 |
|------|------|
| 动作随机化 | 打乱队列算法，动作不按固定顺序、不短期重复 |
| 按模式时长 | 调皮 10-20s / 文静 60-90s / 综合按动作类别 |
| 选择下一个动作 | 右键菜单新增，点击后立即切换到不同随机动作 |
| 玩耍桌面图标 | 调皮模式：叼着跑 / 抱着跑 / 踢着跑（随机图标+路径） |
| 推动窗口 | 调皮模式：出现在窗口四周 → 变大 → 推走 → 变小 |
| 允许移动窗口 | 右键菜单开关（默认开），关闭后不能拖动+推动窗口不触发 |
| 变大变小渐变 | 推动窗口动作中，变大/变小各 0.5-1 秒平滑过渡 |

#### Bug 修复
| Bug | 修复 |
|-----|------|
| 关于对话框点击后程序退出 | `AboutDialog(self)` 传了 TrayController(QObject) 作 parent，改为 `AboutDialog()` |
| 随机名字可能=当前名字 | `_on_dice()` 排除输入框当前名字 |
| 下一个动作可能=当前动作 | `next_action()` 从池中排除当前动作 |
| 测试时素材为空导致 _tick return | 测试脚本补充 `ensure_assets_in_data()` |

---

## 四、素材处理

- **原始素材**：`cat/` 下 9 张写实猫咪照片（室内场景，非透明）
- **抠图处理**：rembg (u2net) AI 去背景，保留毛发/眼睛/爪子细节
- **输出**：`assets/pet/` 9 张透明 PNG（启动时解压到 `BytePet_data/assets/pet/`）
- **图标**：由第一张猫图生成 `assets/icon.ico`（多尺寸）

---

## 五、数据库表结构

### pets（基础信息）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK AUTOINCREMENT | 编号 |
| name | TEXT UNIQUE | 宠物名 |
| gender | TEXT | MM/DD |
| created_date | TEXT | 创建日期 |
| created_at | TEXT | 创建时间 |
| created_version | TEXT | 创建时的版本号 |

### todos（代办事务）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 编号 |
| pet_id | INTEGER FK | 关联宠物 |
| todo_uid | TEXT | 事务UUID |
| exec_date | TEXT | 执行日期 |
| exec_time | TEXT | 执行时间 |
| content | TEXT | 提醒内容 |
| fired | INTEGER | 是否已触发 |
| done | INTEGER | 是否已完成 |

### run_logs（运行日志）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 编号 |
| pet_id | INTEGER FK | 关联宠物 |
| action | TEXT | 动作名 |
| mode | TEXT | 当时模式 |
| start_time | TEXT | 开始时间 |
| duration_sec | REAL | 持续秒数 |
| note | TEXT | 备注 |
| version | TEXT | 版本号 |

---

## 六、项目统计

- **源码模块**：15 个（src/）
- **总代码行数**：约 2500+ 行
- **支持动作**：18 个（8 文静 + 7 调皮 + 3 通用）
- **生成产物**：`dist/BytePet.exe`（58MB 单文件）
