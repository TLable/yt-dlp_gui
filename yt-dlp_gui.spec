# -*- mode: python ; coding: utf-8 -*-
import sys, os

block_cipher = None

a = Analysis(
    ['yt-dlpGUI.py'],
    pathex=['C:\\Users\\Logan\\Documents\\yt-dlp'],   # <-- your source folder
    binaries=[],
    datas=[
        ('requirements.txt', '.'), 
        ('config.json', '.'), 
        ('cookies.txt','.'),
        ('Readme.txt', '.'), 
        ('Readme.md', '.'), 
        ('yt download err Icons', 'yt download err Icons'),
        ('playmusic', 'playmusic'),
        ('sounds', 'sounds'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libcairo-2.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libfontconfig-1.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libfreetype-6.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libgdk_pixbuf-2.0-0.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libgio-2.0-0.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libglib-2.0-0.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libgobject-2.0-0.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libpango-1.0-0.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libpangocairo-1.0-0.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\libpng16-16.dll', '.'),
        ('C:\\Program Files\\GTK3-Runtime Win64\\bin\\zlib1.dll', '.')
    ],
    hiddenimports=['cairosvg', 'cairocffi', 'tinycss2', 'cssselect2', 'pygame', 'PIL', 'PIL.Image', 'PIL.ImageTk'],          # <-- include pygame here
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
    name='yt-dlpGUI',
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
    name='yt-dlp_gui',
)
# At the bottom of yt-dlpGUI.spec
app = BUNDLE(
    coll,
    name='yt-dlpGUI',
    icon='yt download err Icons\\YouTube2Media1AV 2A.ico',
)
