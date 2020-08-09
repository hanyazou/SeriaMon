import sys
import seriamon
from PyQt5.QtWidgets import QApplication

def main():
    app = QApplication([])
    window = seriamon.mainWindow()
    window.setWindowTitle('Serial Monitor')
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
