# main.py

import sys

print("[DEBUG] Starting main.py...")

try:
    from PyQt6.QtWidgets import QApplication
    print("[DEBUG] Imported QApplication from PyQt6")
except Exception as e:
    print("[DEBUG] Exception importing PyQt6:", e)
    raise

try:
    from spectrogram import SpectrogramWindow
    print("[DEBUG] Imported SpectrogramWindow")
except Exception as e:
    print("[DEBUG] Exception importing SpectrogramWindow:", e)
    raise

def main():
    print("[DEBUG] Entering main()")
    app = QApplication(sys.argv)
    print("[DEBUG] Created QApplication object")

    window = SpectrogramWindow()
    print("[DEBUG] Created SpectrogramWindow object")

    window.show()
    print("[DEBUG] Showed window, now calling app.exec()")

    retcode = app.exec()
    print(f"[DEBUG] App exited with code {retcode}")
    sys.exit(retcode)

if __name__ == "__main__":
    print("[DEBUG] __name__ == '__main__' => calling main()")
    main()
    print("[DEBUG] main() returned -- end of file")
