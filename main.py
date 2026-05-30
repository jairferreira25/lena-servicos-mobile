import os, sys, datetime, traceback

_ERROR_LOG = None

def _log_error(msg):
    global _ERROR_LOG
    try:
        if not _ERROR_LOG:
            _ERROR_LOG = '/storage/emulated/0/Lena_Servicos_Error.log'
        with open(_ERROR_LOG, 'a') as f:
            f.write(f'{datetime.datetime.now()}: {msg}\n')
    except:
        pass

def excepthook(tp, val, tb):
    _log_error(f'UNHANDLED: {tp.__name__}: {val}\n{"".join(traceback.format_exception(tp, val, tb))}')

sys.excepthook = excepthook

os.environ['KIVY_NO_ARGS'] = '1'

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.utils import platform

if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

class TestApp(App):
    def build(self):
        from kivy.core.window import Window
        Window.softinput_mode = 'below_target'
        layout = BoxLayout(orientation='vertical', padding=40, spacing=20)
        label = Label(text='[b]LENA SERVICOS[/b]', markup=True, font_size='24sp', color=(0.83, 0.69, 0.22, 1))
        layout.add_widget(label)
        info = Label(text='Teste OK!\nKivy funcionando no Android.', font_size='18sp', color=(1,1,1,1))
        layout.add_widget(info)
        btn = Button(text='OK', size_hint=(0.5, 0.2), pos_hint={'center_x': 0.5})
        layout.add_widget(btn)
        btn.bind(on_press=lambda x: sys.exit(0))
        return layout

if __name__ == '__main__':
    try:
        TestApp().run()
    except Exception as e:
        _log_error(f'FATAL: {e}\n{traceback.format_exc()}')
