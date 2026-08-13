# -*- coding: utf-8 -*-
"""BytePet 电子宠物程序包。

模块组成：
    config         - 全局配置、路径、默认值、用户设置读写
    database       - SQLite 数据访问层（基础信息 / 代办事务 / 运行日志）
    single_instance - 同名宠物单实例互斥锁（支持多开不同名）
    name_dialog    - 启动取名对话框（骰子随机名 / 性别）
    pet_window     - 透明置顶无边框宠物主窗口
    bubble         - 聊天气泡提醒组件
    animator       - 动作动画系统（文静 / 调皮 / 综合）
    activity       - 办公 / 游戏场景智能检测
    desktop_icons  - 桌面图标采集（去背景保存）
    reminders      - 提醒系统（代办事项 + 久坐温馨提醒）
    info_window    - 宠物基础信息窗口
    todo_dialog    - 代办事项录入对话框
    tray           - 系统托盘与设置菜单
    main           - 程序入口
"""

__version__ = "1.0.0"
__app_name__ = "BytePet"
