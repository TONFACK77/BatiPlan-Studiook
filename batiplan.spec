# PyInstaller spec -> dist/BatiPlanStudio/BatiPlanStudio.exe  (build on Windows: see build_windows.bat)
from PyInstaller.utils.hooks import collect_data_files
datas = collect_data_files("ezdxf") + collect_data_files("matplotlib") + [("assets/icon.ico", "assets"), ("assets/logo.png", "assets")]
a = Analysis(["run_batiplan.py"], pathex=["."], datas=datas,
             hiddenimports=["matplotlib.backends.backend_agg", "matplotlib.backends.backend_pdf", "PIL._tkinter_finder", "shapely.geometry", "shapely.ops"],
             excludes=["pytest", "IPython", "scipy", "pandas"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="BatiPlanStudio", console=False, icon="assets/icon.ico")
coll = COLLECT(exe, a.binaries, a.datas, name="BatiPlanStudio")
