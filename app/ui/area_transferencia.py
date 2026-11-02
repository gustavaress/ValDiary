"""Copiar texto para a área de transferência do Windows.

Usamos a API do Windows diretamente (via ctypes) em vez do clipboard do
Tkinter: nos testes com Python 3.15, o clipboard_clear() do Tk derrubava o
app com "access violation" em algumas telas. A API nativa é estável e ainda
tenta de novo se outro programa estiver usando a área de transferência.
"""

import ctypes
import sys
import time
from ctypes import wintypes

_CF_UNICODETEXT = 13
_GMEM_MOVEABLE = 0x0002


def _api_windows():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.restype = wintypes.BOOL
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    return user32, kernel32


def copiar_texto(texto: str, janela) -> bool:
    """Copia o texto. `janela` é a janela principal (dona da área de transferência).

    Retorna False se não conseguiu (ex.: outro programa segurando o clipboard).
    """
    if sys.platform != "win32":
        janela.clipboard_clear()
        janela.clipboard_append(texto)
        return True

    user32, kernel32 = _api_windows()
    dono = int(janela.wm_frame(), 16)  # HWND da janela principal
    dados = texto.encode("utf-16-le") + b"\x00\x00"

    for _ in range(10):
        if user32.OpenClipboard(dono):
            break
        time.sleep(0.05)  # outro programa está usando; tenta de novo
    else:
        return False

    try:
        user32.EmptyClipboard()
        memoria = kernel32.GlobalAlloc(_GMEM_MOVEABLE, len(dados))
        if not memoria:
            return False
        ponteiro = kernel32.GlobalLock(memoria)
        ctypes.memmove(ponteiro, dados, len(dados))
        kernel32.GlobalUnlock(memoria)
        if not user32.SetClipboardData(_CF_UNICODETEXT, memoria):
            kernel32.GlobalFree(memoria)  # só liberamos se o Windows não assumiu a memória
            return False
        return True
    finally:
        user32.CloseClipboard()
