# -*- mode: python -*-

block_cipher = None


a = Analysis(['permuit_name_recursion.py'],
             pathex=['C:\\Users\\Shilpa & Shubhankar\\Desktop\\py_oracl_hdf_codes\\py_oracl_hdf_codes'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='permuit_name_recursion',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
