import configparser
from typing import List, Union, Optional, Tuple, Any

import wx
from gui_widgets import BasicDialog, InputOutputPanel, ImageList, Clipboard
from gui_widgets_list import BasicListCtrl
from basic import Logger


class InfoWindow(BasicDialog):
    def __init__(self, parent: Union[wx.Window, wx.Frame, wx.Control], name: str, icon_path: Optional[str], ini_file: Optional[configparser.ConfigParser], size: wx.Size, app_logger: Logger, copy_button: bool = False):
        BasicDialog.__init__(self, parent, name, icon_path, wx.DefaultPosition, size, ini_file, True)
        self.logger = app_logger
        self.ini_file = ini_file
        self.info_list = BasicListCtrl(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        if copy_button:
            cb = wx.Button(self,label="Копировать в буфер")
            cb.Bind(wx.EVT_BUTTON, self.on_copy_to_buffer_click)
            sizer.Add(cb, 0, wx.ALL, 5)
        sizer.Add(self.info_list, 1, wx.EXPAND | wx.ALL, 1)
        self.SetSizer(sizer)
        self.Layout()
        self.info_list.set_header([('', 32, wx.Bitmap), ('Сообщение', 1000, str), ])

    def add_messages(self, info_data_list: List[Tuple[ImageList.BuiltInImage, str]]):
        for i, idata in enumerate(info_data_list):
            self.info_list.add_row(idata, i)

    def on_copy_to_buffer_click(self, _evt: wx.CommandEvent):
        clipboard_text = ''
        for i in range(self.info_list.get_count()):
            data = self.info_list.get_data(i)
            if data[0] == ImageList.BuiltInImage.ERROR:
                clipboard_text += f'[Ошибка]'
            elif data[0] == ImageList.BuiltInImage.WARNING:
                clipboard_text += f'[Предупреждение]'
            elif data[0] == ImageList.BuiltInImage.INFO:
                clipboard_text += f'[Информация]'
            clipboard_text += f' {data[1]}\n'
        clipboard_text = clipboard_text.rstrip('\n')
        Clipboard.write_text(clipboard_text)


def show_info_window(logger: Logger, parent: Any, title: str, str_items: List[Union[str, Tuple[ImageList.BuiltInImage, str]]], size: wx.Size = wx.DefaultSize, modal: bool = True):
    info_wnd = InfoWindow(parent, title, None, None, size, logger,True)
    info_wnd.CenterOnParent()
    info_items = []
    for src_str in str_items:
        if type(src_str) == str:
            info_items.append((ImageList.BuiltInImage.INFO, src_str))
        elif type(src_str) == tuple:
            info_items.append((src_str[0], src_str[1]))
    info_wnd.add_messages(info_items)
    if modal:
        info_wnd.ShowModal()
        info_wnd.Close()
    else:
        info_wnd.Show()

def set_iopanel_popup_messages(logger: Logger, io_panel: InputOutputPanel, main_message: Optional[str], main_icon: Optional[int], info_items: Optional[List[Tuple[ImageList.BuiltInImage, str]]] = None):
    input_box = io_panel.parent

    def on_button_click():
        nonlocal info_items
        info_wnd = InfoWindow(io_panel.GetTopLevelParent(), 'Предупреждения', None, None, wx.Size(800, 300), logger)
        info_wnd.CenterOnParent()
        info_wnd.add_messages(info_items)
        info_wnd.ShowModal()


    if info_items:
        if not input_box.have_button('Показать'):
            input_box.add_button_info_message('Показать', on_button_click)
    else:
        if input_box.have_button('Показать'):
            input_box.clear_buttons_info_message()

    if main_message:
        if not main_icon in [wx.ICON_INFORMATION, wx.ICON_WARNING, wx.ICON_ERROR]:
            main_icon = wx.ICON_NONE
        input_box.show_info_message(main_message, main_icon, False)
    else:
        input_box.hide_info_message()



def set_io_panel_warnings(logger: Logger, io_panel: InputOutputPanel, info_items: List[Tuple[ImageList.BuiltInImage, str]], required_fields_list: List[str]):

    input_box = io_panel.parent
    def on_button_click():
        nonlocal info_items
        info_wnd = InfoWindow(io_panel.GetTopLevelParent(), 'Предупреждения', None, None, wx.Size(800, 300), logger)
        info_wnd.CenterOnParent()
        info_wnd.add_messages(info_items)
        info_wnd.ShowModal()

    if len(required_fields_list) > 0:
        io_panel.parent.show_info_message(f'Необходимо ввести: {", ".join(required_fields_list)}', wx.ICON_WARNING, False)
    else:
        io_panel.parent.hide_info_message()

    if len(info_items) > 0 and not required_fields_list:
        input_box.show_info_message(f'Найдены предупреждения', wx.ICON_INFORMATION, False)
        if input_box.have_button('Показать'):
            input_box.clear_buttons_info_message()
        if not input_box.have_button('Показать'):
            input_box.add_button_info_message('Показать', on_button_click)
        input_box.Layout()
    elif len(info_items) == 0 and not required_fields_list:
        if input_box.have_button('Показать'):
            input_box.clear_buttons_info_message()
        input_box.hide_info_message()
        input_box.Layout()