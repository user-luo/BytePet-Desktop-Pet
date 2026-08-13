# -*- coding: utf-8 -*-
"""同名宠物单实例互斥锁。

需求：程序可多开（不同名字的宠物可同时运行），但同名宠物只能开一个。
实现：Windows 命名互斥量（Named Mutex）。每个宠物名对应一个全局命名互斥量，
      第二次以同名启动时 CreateMutex 返回 ERROR_ALREADY_EXISTS，据此拒绝。
"""

import threading

try:
    import win32event
    import win32api
    import winerror
    _HAS_WIN32 = True
except Exception:  # 非 Windows 或缺 pywin32 时退化为文件锁
    _HAS_WIN32 = False


class PetInstanceLock:
    """管理本进程持有的多个宠物命名互斥量。"""

    def __init__(self):
        self._handles = {}  # name -> mutex handle
        self._lock = threading.Lock()

    def acquire(self, name: str) -> bool:
        """尝试为指定宠物名加锁。成功返回 True；已被其他实例占用返回 False。"""
        with self._lock:
            if name in self._handles:
                return True  # 本进程已持有
            if _HAS_WIN32:
                mutex_name = "Local\\BytePet_Pet_" + name
                try:
                    handle = win32event.CreateMutex(None, False, mutex_name)
                    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                        try:
                            win32api.CloseHandle(handle)
                        except Exception:
                            pass
                        return False
                    self._handles[name] = handle
                    return True
                except Exception:
                    return False
            else:
                # 退化：进程内已持有即视为占用（无法跨进程，仅作占位）
                self._handles[name] = True
                return True

    def release(self, name: str = None) -> None:
        """释放指定名（或全部）的互斥量。"""
        with self._lock:
            names = list(self._handles.keys()) if name is None else [name]
            for n in names:
                h = self._handles.pop(n, None)
                if h is None:
                    continue
                if _HAS_WIN32 and h is not True:
                    try:
                        win32api.CloseHandle(h)
                    except Exception:
                        pass


# 全局单例
pet_lock = PetInstanceLock()
