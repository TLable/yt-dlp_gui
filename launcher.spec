# -*- mode: python ; coding: utf-8 -*-
import sys, os

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=['C:\\Users\\Logan\\Documents\\yt-dlp'],   # <-- your source folder
    binaries=[],
    datas=[
        ('config.json', '.'), 
        ('cookies.txt','.'),
        ('yt download err Icons', 'yt download err Icons'),
        ('playsound', 'playsound'),
        ('sounds', 'sounds'),
    ],
    hiddenimports=['pygame', 'PIL', 'PIL.Image', 'PIL.ImageTk'],          # <-- include pygame here
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=False,          # embed binaries correctly
    name='launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='yt download err Icons\\YouTube2Media1AV 2A.ico', # embed icon
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='launcher',                 # folder output: dist\launcher\
)
# At the bottom of launcher.spec
app = BUNDLE(
    coll,
    name='launcher',
    icon='yt download err Icons\\YouTube2Media1AV 2A.ico',
)