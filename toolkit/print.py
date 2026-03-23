import sys
import os
from toolkit.accelerator import get_accelerator


def print_acc(*args, **kwargs):
    if get_accelerator().is_local_main_process:
        print(*args, **kwargs)


def _safe_write(target, message):
    try:
        target.write(message)
    except UnicodeEncodeError:
        encoding = getattr(target, 'encoding', None) or 'utf-8'
        safe = message.encode(encoding, errors='replace').decode(encoding, errors='replace')
        try:
            target.write(safe)
        except UnicodeEncodeError:
            target.write(message.encode('ascii', errors='replace').decode('ascii'))


class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'a', encoding='utf-8')

    def write(self, message):
        _safe_write(self.terminal, message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()


def setup_log_to_file(filename):
    if get_accelerator().is_local_main_process:
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
    sys.stdout = Logger(filename)
    sys.stderr = Logger(filename)
