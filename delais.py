"""Échéance réelle sur les runners Linux, y compris pendant une lecture réseau."""
from contextlib import contextmanager
import signal
import threading


class DelaiDepasse(BaseException):
    # Ne pas être absorbé par les replis réseau `except Exception`.
    pass


@contextmanager
def delai_reel(secondes):
    if secondes <= 0:
        raise DelaiDepasse('Budget épuisé')
    if not hasattr(signal, 'setitimer') or threading.current_thread() is not threading.main_thread():
        raise RuntimeError('Une échéance réelle nécessite le thread principal POSIX')
    ancien = signal.getsignal(signal.SIGALRM)
    def interrompre(*_):
        raise DelaiDepasse('Budget épuisé')
    signal.signal(signal.SIGALRM, interrompre)
    signal.setitimer(signal.ITIMER_REAL, secondes)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, ancien)
