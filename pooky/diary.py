import os
import requests

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import appdirs

from pooky.ui.main import Ui_MainWindow


RESOURCES = os.path.join(os.path.dirname(__file__))
USER_DATA = appdirs.user_data_dir('pookys-diary')


class Strip:
    REMOTE_URL = 'https://d1ejxu6vysztl5.cloudfront.net/comics/garfield/{year:04d}/{year:04d}-{month:02d}-{day:02d}.gif'
    LOCAL_DIR = os.path.join(USER_DATA, 'strips')

    def __init__(self, date):
        self.date = date
        self.path = os.path.join(self.LOCAL_DIR, f'{date.year()}/{date.toString(Qt.ISODate)}.gif')

    def is_available(self):
        return os.path.isfile(self.path)

    def previous(self):
        return Strip(self.date.addDays(-1))

    def next(self):
        return Strip(self.date.addDays(1))

    def download(self):
        if self.is_available():
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        url = self.REMOTE_URL.format(year=self.date.year(), month=self.date.month(), day=self.date.day())
        req = requests.get(url)
        if req.status_code != 200:
            raise Exception('fuck')  # FIXME
        with open(self.path + '.tmp', 'wb') as f:
            f.write(req.content)
        os.rename(self.path + '.tmp', self.path)

    @classmethod
    def todays(cls):
        return cls(QDate.currentDate())

    @classmethod
    def first(cls):
        return cls(QDate(1978, 6, 19))

    @classmethod
    def find_last(cls):
        if not os.path.isdir(cls.LOCAL_DIR):
            return None
        for year in sorted(os.listdir(cls.LOCAL_DIR), reverse=True):
            for gif in sorted(os.listdir(os.path.join(cls.LOCAL_DIR, year)), reverse=True):
                date, ext = os.path.splitext(gif)
                if ext == '.gif':
                    return cls(QDate.fromString(date, Qt.ISODate))
        return None


class Downloader(QRunnable):
    class Signals(QObject):
        error = pyqtSignal(Exception, Strip)
        done = pyqtSignal(Strip)
        progress = pyqtSignal(int, int, Strip)

    def __init__(self, main):
        super(Downloader, self).__init__()
        self.main = main
        self.signals = self.Signals()
        self.stop = False
        self.main.abort.connect(self._abort)

    def run(self):
        last = Strip.todays()
        total = Strip.first().date.daysTo(last.date) + 1

        curr = last
        self.signals.progress.emit(0, total, last)  # FIXME last doesn't match done=0
        for i in range(0, total):
            if self.stop:
                continue
            try:
                curr.download()
            except Exception as err:
                if curr == last:
                    curr = curr.previous()
                    continue
                else:
                    self.signals.error.emit(err, curr)
                    return
            self.signals.progress.emit(i + 1, total, curr)
            curr = curr.previous()
        self.signals.done.emit(last)

    def _abort(self):
        self.stop = True


class MainWindow(QMainWindow, Ui_MainWindow):
    abort = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon(os.path.join(RESOURCES, 'icons/app.png')))

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(lambda x: self.abort.emit())
        self.cancel_button.hide()

        self.statusBar.addWidget(self.progress_bar)
        self.statusBar.addWidget(self.cancel_button)
        self.statusBar.addPermanentWidget(QLabel('v0.0.2'))

        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowSystemMenuHint |
            Qt.WindowTitleHint |
            0
        )
        self.prev_strip_button.clicked.connect(self.prev_strip)
        self.next_strip_button.clicked.connect(self.next_strip)
        self.sync_button.clicked.connect(self.download)

        self.selected_strip = Strip.find_last()
        self.drawn_strip = None
        self.update()

        self.download()

    def update(self):
        if self.drawn_strip != self.selected_strip:
            self.strip_content.setPixmap(QPixmap(self.selected_strip.path))
            self.strip_caption.setText(self.selected_strip.date.toString(Qt.DefaultLocaleLongDate))
            self.drawn_strip = self.selected_strip

        if self.drawn_strip:
            self.prev_strip_button.setEnabled(self.drawn_strip.previous().is_available())
            self.next_strip_button.setEnabled(self.drawn_strip.next().is_available())

    def prev_strip(self):
        self.selected_strip = self.selected_strip.previous()
        self.update()

    def next_strip(self):
        self.selected_strip = self.selected_strip.next()
        self.update()

    def download(self):
        button_text = self.sync_button.text()
        self.sync_button.setEnabled(False)
        self.sync_button.setText('Sync in progress')
        worker = Downloader(self)

        def reset():
            self.progress_bar.hide()
            self.cancel_button.hide()
            self.sync_button.setEnabled(True)
            self.sync_button.setText(button_text)

        def on_error(err, strip):
            strip_date = strip.date.toString(Qt.DefaultLocaleLongDate)
            self.statusBar.showMessage(f'Download error')
            print('Failed to download', strip.date, err)
            reset()

        def on_done(last):
            last_date = last.date.toString(Qt.DefaultLocaleLongDate)
            reset()

        def on_progress(done, total, strip):
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(done)
            self.progress_bar.show()
            self.cancel_button.show()
            self.update()  # TODO use strip to update next/prev buttons more efficiently

        worker.signals.error.connect(on_error)
        worker.signals.progress.connect(on_progress)
        worker.signals.done.connect(on_done)
        QThreadPool.globalInstance().start(worker)

    def closeEvent(self, event):
        self.abort.emit()
        QThreadPool.globalInstance().waitForDone()
        super().closeEvent(event)


def main():
    app = QApplication([])
    main = MainWindow()
    main.show()
    app.exec_()


if __name__ == '__main__':
    main()
