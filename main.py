
import wx
import configparser
import os
import sys
import locale

import basic
from gui_widgets import get_app_settings_folder
from basic import Logger, LogLevel, LogMessage

import gui_widgets

#sys.setrecursionlimit(10000)

app = wx.App()

def log_out_msg(log_msg: LogMessage):
    print(f'{log_msg.logger.logger_name} {log_msg.log_level.name} {log_msg.msg}')


APPLICATION_NAME = 'SAH'
app_cfg_path = get_app_settings_folder()
main_wnd_cfg = configparser.ConfigParser()

main_wnd_cfg_filename = os.path.join(os.path.normpath(os.path.join(app_cfg_path, APPLICATION_NAME)), 'main.ini')

gui_debug_level = LogLevel.INFO
basic_debug_level = LogLevel.INFO
app_debug_level = LogLevel.INFO

app_logger = Logger(basic_debug_level)
app_logger.add_message_callback(log_out_msg)
app_logger.log_level = app_debug_level

gui_widgets.mlogger.log_level = gui_debug_level
gui_widgets.mlogger.add_message_callback(log_out_msg)

basic.mlogger.log_level = basic_debug_level
basic.mlogger.add_message_callback(log_out_msg)



app_settings_filename = os.path.join(os.path.normpath(os.path.join(app_cfg_path, APPLICATION_NAME)) , 'mainsettings.xml')

if not os.path.exists(os.path.dirname(app_settings_filename)):
    try:
        os.makedirs(os.path.dirname(app_settings_filename))
    except Exception as ex:
        print(f'{ex}')
        sys.exit(-1)

if not os.path.exists(os.path.dirname(main_wnd_cfg_filename)):
    try:
        os.makedirs(os.path.dirname(main_wnd_cfg_filename))
    except Exception as ex:
        print(f'{ex}')
        sys.exit(-1)



import basicclasses


basicclasses.app_settings.load_from_file(app_settings_filename)

#basicclasses.app_settings.use_history = True
#basicclasses.app_settings.init_paths(__file__, APPLICATION_NAME, app_logger)

if os.path.exists(main_wnd_cfg_filename):
    main_wnd_cfg.read(main_wnd_cfg_filename)

app.locale = wx.Locale(wx.LANGUAGE_RUSSIAN_RUSSIA)
locale.setlocale(locale.LC_ALL, 'ru_RU')
gui_widgets.GuiWidgetSettings.date_format_str = basicclasses.app_settings.date_format

import main_window
basicclasses.display_size = wx.DisplaySize()

app_main_wnd = main_window.MainWindow('Охрана труда', None, main_wnd_cfg, app_logger)
app_main_wnd.Show()

app.MainLoop()
basicclasses.app_settings.save_to_file(app_settings_filename)
try:
    f = open(main_wnd_cfg_filename,'w')
    main_wnd_cfg.write(f)
    f.close()
except Exception as ex:
    print(f'{ex}')
    sys.exit(-1)
app.Destroy()
