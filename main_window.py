import itertools
import os.path
import datetime


from typing import Optional, List, Tuple, Dict


import wx
import wx.grid

import configparser


import basic
import basicclasses
import gui_widgets

from gui_widgets import (BasicWindow, BasicMenu, BasicNotebook, BasicStatusBar, BasicPanel,
                         WxCommand, ProgressWnd, EventProgressObject, message_box,
                         BasicSideNotebook,
                         BasicFileSelect)

from gui_widgets_grid import BTFilterType

from db_data_adapter import DBStorableRow

from basic import EventSubscriber, Logger, EventType
from basicclasses import MainDatabase, app_settings
from grid_panel import TableEditorPanel, TableEditorConfig
from active_training_panel import ActiveTrainingPanel
from action_scripts import ActionScripts


notebook_image_size = wx.Size(16,16)
left_notebook_image_size = wx.Size(20,20)



from gui_widgets import DBInputDialogConfig, InputOutputPanel, ImageList, BasicCombobox, BasicCheckList, BasicPopupMenu, Clipboard
from warining_window import set_io_panel_warnings, show_info_window
from update_manager import UpdateManager, MainWindowStatusBar
from export_module import ExportTrainRequest
from personall_panel import PersonallDocPanel
from required_recommended_panels import RecommendedTrainingsPanel, RequiredTrainingsPanel
from gui_widgets_grid import BasicGrid




class NotebookPanel(BasicNotebook):
    _update_manager: UpdateManager
    def __init__(self, parent, image_size_list, update_manager: UpdateManager):
        BasicNotebook.__init__(self, parent, image_size_list)
        self.register_on_changed(self.nbp_page_changed)
        self._update_manager = update_manager


    def nbp_page_changed(self, old_name: str, new_name: str):
        old_page = self.get_page(old_name)
        new_page = self.get_page(new_name)
        if old_page:
            if issubclass(type(old_page), (TableEditorPanel, NotebookPanel)):
                old_page.on_show_panel(False)
        if new_page:
            if issubclass(type(new_page), (TableEditorPanel, NotebookPanel)):
                new_page.on_show_panel(True)
                self._update_manager.set_active_task_parent(new_page)

    def on_show_panel(self, is_showed: bool):
        selected_page = self.get_selected_page_name()
        panel: TableEditorPanel = self.get_page(selected_page)
        if issubclass(type(panel), TableEditorPanel):
            panel.on_show_panel(is_showed)

class MainWindow(BasicWindow, EventSubscriber):
    # Базовые экземпляры для работы программы
    dataset: Optional[MainDatabase]
    _update_manager: UpdateManager
    app_logger: Logger

    # графические экземпляры для отображения элементов управления
    main_menu: BasicMenu
    main_notebook: BasicNotebook
    main_status: BasicStatusBar
    status_manager: MainWindowStatusBar

    _panels: List[TableEditorPanel]
    _notebooks: Dict[str, NotebookPanel]

    def __init__(self, name: str, icon_path: Optional[str], ini_file: configparser.ConfigParser, l_app_logger: Logger):
        BasicWindow.__init__(self, None, name, icon_path, ini_file, size=wx.DefaultSize)
        self.dataset = None

        self.app_logger = l_app_logger

        self._panels = []
        self._notebooks = {}

        self.main_menu = BasicMenu(self)
        self.main_status = BasicStatusBar(self)
        self.main_status.add_bitmap('update', os.path.join(app_settings.run_path, r'Icons\StatusBar\update.ico'))
        self.main_status.add_bitmap('update_files', os.path.join(app_settings.run_path, r'Icons\StatusBar\update_folder.ico'))
        self.main_status.add_bitmap('update_network', os.path.join(app_settings.run_path, r'Icons\StatusBar\update_net.ico'))


        self.status_manager = MainWindowStatusBar(self.main_status)
        self.SetStatusBar(self.main_status)
        self._update_manager = UpdateManager(l_app_logger, self.status_manager)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.main_panel = BasicPanel(self)


        main_sizer.Add(self.main_panel, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(main_sizer)

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_panel.SetSizer(self.main_sizer)

        self.Freeze()
        self.Layout()
        self.Update()
        self.Thaw()
        file_menu = BasicPopupMenu()
        create_command = WxCommand(1001, "Создать", os.path.join(app_settings.run_path, r'Icons\database_create.ico'), acc_control_key=wx.ACCEL_CTRL, acc_main_key=wx.WXK_CONTROL_N, execute_func=self.wxcommand_create_db, can_execute_func=self.wxcommand_can_create_db)
        file_menu.add_item(create_command)
        self.add_wxcommand(create_command)

        open_command = WxCommand(1002, "Открыть", os.path.join(app_settings.run_path, r'Icons\database_open.ico'), execute_func=self.wxcommand_open_db, can_execute_func=self.wxcommand_can_open_db)
        file_menu.add_item(open_command)
        self.add_wxcommand(open_command)
        if app_settings.use_history:
            save_command = WxCommand(1003, "Сохранить", os.path.join(app_settings.run_path, r'Icons\database_save.ico'), execute_func=self.wxcommand_save_db, can_execute_func=self.wxcommand_can_save_db)
            file_menu.add_item(save_command)
            self.add_wxcommand(save_command)

        close_command = WxCommand(1004, "Закрыть", os.path.join(app_settings.run_path, r'Icons\database_close.ico'), execute_func=self.wxcommand_close_db, can_execute_func=self.wxcommand_can_close_db)
        file_menu.add_item(close_command)
        self.add_wxcommand(close_command)

        file_menu.add_separator()

        settings_command = WxCommand(1010, "Настроить", os.path.join(app_settings.run_path, r'Icons\settings.ico'), execute_func=self.wxcommand_app_settings, can_execute_func=self.wxcommand_can_app_settings)
        file_menu.add_item(settings_command)
        self.add_wxcommand(settings_command)
        self.main_menu.add_menu(file_menu, 'Файл', 1000)
        self.dataset = None
        self.update_wxcommands()
        self.bind_wxcommands()
        self.main_menu.update_wxcommand_states()
        self.Bind(wx.EVT_IDLE, self._on_idle)
        wx.CallAfter(self._on_load_window)

    # region действия GUI

    def wxcommand_create_db(self, _evt: wx.CommandEvent):
        file_dialog = wx.FileDialog(self, "Создать файл", defaultDir=app_settings.last_workspace_path, wildcard="MSAccess (*.accdb)|*.accdb|SQLite (*.db)|*.db", style=wx.FD_SAVE)  # | wx.FD_FILE_MUST_EXIST, name="Выбрать")
        r = file_dialog.ShowModal()
        if r == wx.ID_OK:
            wc_index = file_dialog.GetFilterIndex()
            filename = file_dialog.GetPath()
            if wc_index == 0:
                selected_fileext = '.accdb'
            elif wc_index == 1:
                selected_fileext = '.db'
            else:
                selected_fileext = None
            if selected_fileext is None:
                message_box(self, 'Ошибка', 'Неверный тип файла', wx.ICON_ERROR)
                return
            if os.path.splitext(filename)[1] != selected_fileext:
                filename = filename + selected_fileext
            if not os.path.exists(os.path.dirname(filename)):
                message_box(self, 'Ошибка', 'Путь к выбранному файлу не существует', wx.ICON_ERROR)

            progress = ProgressWnd(self.GetTopLevelParent(), 'Создание БД', wx.Size(300, 100))
            notifier = progress.get_notifier()
            self._update_manager.set_notifier(notifier)

            notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Создание таблиц'))
            progress.Show()
            self.dataset = MainDatabase(self.app_logger, selected_fileext[1:])
            if not self.dataset.create(filename):
                self.dataset.disconnect()

            notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Создание таблиц завершено'))


            app_settings.last_file_name = filename
            app_settings.last_workspace_path = os.path.dirname(filename)

            if not self.dataset.inited or not self.dataset.connected:
                message_box(self, 'Ошибка', 'Ошибка при создании БД', wx.ICON_ERROR)
                self.dataset = None
            else:
                self._init_window_workspace()
            self._update_manager.set_notifier(None)
            progress.Close()
    def wxcommand_can_create_db(self):
        if self.dataset:
            if self.dataset.connected:
                return False
        return True

    def wxcommand_open_db(self, _evt: wx.CommandEvent):
        file_dialog = wx.FileDialog(self, "Создать файл", defaultDir=app_settings.last_workspace_path, wildcard="MSAccess (*.accdb)|*.accdb|SQLite (*.db)|*.db", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)  # , name="Выбрать")
        r = file_dialog.ShowModal()
        if r == wx.ID_OK:
            if os.path.exists(file_dialog.GetPath()):
                self._open_dataset(file_dialog.GetPath())
        self.update_wxcommands()
        self.main_menu.update_wxcommand_states()

    def wxcommand_can_open_db(self):
        if self.dataset:
            if self.dataset.connected:
                return False
        return True

    def wxcommand_close_db(self, _evt: wx.CommandEvent):
        self._close_dataset()
        self.update_wxcommands()
        self.main_menu.update_wxcommand_states()

    def wxcommand_can_close_db(self):
        if self.dataset:
            if self.dataset.connected:
                return True
        return False

    def wxcommand_save_db(self, _evt: wx.CommandEvent):
        self._save_dataset()
        self.update_wxcommands()
        self.main_menu.update_wxcommand_states()
        for panel in self._panels:
            panel.toolbar.update_wxcommand_states()
            panel.update_wxcommands()

    def wxcommand_can_save_db(self):
        if self.dataset:
            if self.dataset.connected:
                return self.dataset.have_changes()
        return False

    def check_fs_folders(self):
        found_paths = []
        if not os.path.exists(self.dataset.workspace_settings.db_files_path) or not os.path.exists(self.dataset.workspace_settings.train_request_path):
            path_values = []
            for d_name in gui_widgets.get_avaliable_drive_names():
                p1_drive, p1_without_drive = os.path.splitdrive(self.dataset.workspace_settings.db_files_path)
                p2_drive, p2_without_drive = os.path.splitdrive(self.dataset.workspace_settings.train_request_path)

                new_path1 = os.path.join(d_name, p1_without_drive)
                new_path2 = os.path.join(d_name, p2_without_drive)
                if p1_without_drive and p2_without_drive:
                    if os.path.exists(new_path1) and os.path.exists(new_path2):
                        found_paths.append((d_name, new_path1, new_path2))
                        path_values.append((f'{d_name}', (d_name, new_path1, new_path2)))
            if len(found_paths) > 0:
                input_box = gui_widgets.InputBox(self.main_panel, 'Выбор диска', None, None, size=wx.Size(500, 300), scrollable=False, sizeable=False, ignore_enter_key=False)
                input_box.input_panel.add_property('info_msg', 'Найдено несколько дисков с присутствующей\nфайловой системой программы\nвыберите диск с файлами', None, False)
                input_box.input_panel.add_property('selected_items', '', gui_widgets.BasicCombobox, False)
                input_box.input_panel.set_property('selected_items', found_paths, path_values)
                # input_box.input_panel.set_property_size('selected_items', 600, 150)
                # input_box.input_panel.set_property('selected_items', )
                # input_box.input_panel.add_property('complete_date', '', datetime.date, False)
                input_box.input_panel.update_view()
                input_box.Fit()
                input_box.Layout()
                input_box.CenterOnParent()
                input_box.input_panel.set_focus()

                r = input_box.ShowModal()

                if r == wx.ID_OK:
                    cur_val: Tuple[str, str, str] = input_box.input_panel.get_property('selected_items', False)
                    if cur_val:
                        self.dataset.workspace_settings.db_files_path = cur_val[1]
                        self.dataset.workspace_settings.train_request_path = cur_val[2]

        while not os.path.exists(self.dataset.workspace_settings.db_files_path) or not os.path.exists(self.dataset.workspace_settings.train_request_path) or not os.path.exists(self.dataset.workspace_settings.config_path):
            message_box(self, 'Ошибка', 'Рабочие папки должны быть заданы и должны существовать', wx.ICON_WARNING)
            self.wxcommand_app_settings(None)

    def wxcommand_app_settings(self, _evt: Optional[wx.CommandEvent]):
        input_box = gui_widgets.InputBox(self, 'Настройки', None, self.ini_file, scrollable=True, sizeable=True, ignore_enter_key=False)
        input_box.input_panel.add_property('path_to_files', 'Путь к файлам документов:', BasicFileSelect, False)
        input_box.input_panel.set_property_param('path_to_files', 'folder_select', True)
        input_box.input_panel.set_property_size('path_to_files', 250, -1)

        input_box.input_panel.add_property('path_to_train_requests', 'Путь к файлам заявок:', BasicFileSelect, False)
        input_box.input_panel.set_property_param('path_to_train_requests', 'folder_select', True)
        input_box.input_panel.set_property_size('path_to_train_requests', 250, -1)

        input_box.input_panel.add_property('path_to_configs', 'Путь к файлам конфигурации:', BasicFileSelect, False)
        input_box.input_panel.set_property_param('path_to_configs', 'folder_select', True)
        input_box.input_panel.set_property_size('path_to_configs', 250, -1)

        # input_box.input_panel._control_sizer.SetItemSpan(input_box.input_panel._control_labels['test'], (0,2))
        input_box.input_panel.update_view()
        input_box.Fit()
        input_box.Layout()
        input_box.load_state()
        input_box.CenterOnParent()
        input_box.input_panel.set_focus()

        input_box.input_panel.set_property('path_to_files', self.dataset.workspace_settings.db_files_path, None)
        input_box.input_panel.set_property('path_to_train_requests', self.dataset.workspace_settings.train_request_path, None)
        input_box.input_panel.set_property('path_to_configs', self.dataset.workspace_settings.config_path, None)

        result = input_box.ShowModal()
        wx.LaunchDefaultBrowser(gui_widgets.get_app_settings_folder())
        if result == wx.ID_OK:
            db_dir = input_box.input_panel.get_property('path_to_files', False)
            if db_dir:
                if os.path.exists(db_dir):
                    self.dataset.workspace_settings.db_files_path = db_dir
                else:
                    message_box(self, 'Ошибка', f'Директория не найдена {db_dir}', wx.ICON_ERROR)
            tr_request_dir = input_box.input_panel.get_property('path_to_train_requests', False)
            if tr_request_dir:
                if os.path.exists(tr_request_dir):
                    self.dataset.workspace_settings.train_request_path = tr_request_dir
                else:
                    message_box(self, 'Ошибка', f'Директория не найдена {tr_request_dir}', wx.ICON_ERROR)
            cfg_dir = input_box.input_panel.get_property('path_to_configs', False)
            if cfg_dir:
                if os.path.exists(cfg_dir):
                    self.dataset.workspace_settings.config_path = cfg_dir
                else:
                    message_box(self, 'Ошибка', f'Директория не найдена {cfg_dir}', wx.ICON_ERROR)

        input_box.save_state()

    def wxcommand_can_app_settings(self):
        if self.dataset:
            if self.dataset.connected:
                return True
        return False


    # endregion

    def _on_load_window(self):
        frozen = self.IsFrozen()
        if not frozen:
            self.Freeze()

        if app_settings.last_file_name:
            if os.path.exists(app_settings.last_file_name):
                self._open_dataset(app_settings.last_file_name)

        if not frozen:
            self.Thaw()

    def _on_idle(self, evt: wx.IdleEvent):
        if self._update_manager.need_update:
            self._update_manager.update()
            evt.RequestMore(self._update_manager.need_update)

    def on_close(self, event: wx.CloseEvent):

        if self.dataset:
            # noinspection PyTypeChecker
            if not self._close_dataset():
                event.Veto()
        if not event.GetVeto():
            self._update_manager.clear()
        # event.Skip()
        BasicWindow.on_close(self, event)

    def _open_dataset(self, main_db_filename: str):

        # try:
        frozen = self.IsFrozen()
        if not frozen:
            self.Freeze()
        # self.main_notebook.Freeze()

        if os.path.exists(main_db_filename):
            fileext = os.path.splitext(main_db_filename)[1][1:]
            if fileext not in ['accdb', 'db']:
                message_box(self, 'Ошибка', f'Тип файла {fileext} не поддерживается', wx.ICON_ERROR)
                if frozen:
                    self.Thaw()
                return

            progress = ProgressWnd(self.GetTopLevelParent(), 'Открытие БД', wx.Size(300, 100), True)
            notifier = progress.get_notifier()
            #notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Чтение таблиц'))
            self._update_manager.set_notifier(notifier)
            progress.Show()

            self.dataset = MainDatabase(self.app_logger, fileext)
            if not self.dataset.inited:
                progress.Close()
                message_box(self, 'Ошибка', f'Открытия инициализации БД', wx.ICON_ERROR)
                if not frozen:
                    self.Thaw()
                return

            if not self.dataset.connect(main_db_filename):
                progress.Close()
                message_box(self, 'Ошибка', f'Открытия базы данных {os.path.split(main_db_filename)[1]}. БД повреждена', wx.ICON_ERROR)
                if not frozen:
                    self.Thaw()
                self.dataset = None
                return
            self.dataset.read_tables_from_db(notifier)
            app_settings.last_file_name = main_db_filename
            app_settings.last_workspace_path = os.path.dirname(main_db_filename)
            #notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Чтение таблиц завершено'))
            self._init_window_workspace()
            self._update_manager.set_notifier(None)
            progress.Close()

        if not frozen:
            self.Thaw()

    def _close_dataset(self):
        if self.dataset:
            if self.dataset.connected:
                if self.dataset.have_changes():
                    r = wx.MessageDialog(self, f"В базе данных есть изменения. Сохранить?", "Подтверждение", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION).ShowModal()
                    if r == wx.ID_YES:
                        self._save_dataset()
                    else:
                        self._undo_changes_dataset()

            self._deinit_window_workspace()
            self.dataset.disconnect()
            self.dataset = None
            self.update_wxcommands()
            self.main_menu.update_wxcommand_states()
        return True

    def _save_dataset(self):
        level_val = basic.default_notify_level
        progress = ProgressWnd(self.GetTopLevelParent(), 'Сохранение', wx.Size(300, 100))

        notifier = progress.get_notifier()
        notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject(msg=f'Сохранение данных', cur_val=0, max_val=len(self.dataset.predefined_table_types), level=level_val))
        self._update_manager.set_notifier(notifier)
        progress.Show()
        progress.Update()

        for i, t_type in enumerate(self.dataset.predefined_table_types):
            table = self.dataset.get_table(t_type)
            table.history_commit(notifier)
            notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Сохранение данных {table.name}', cur_val=i + 1, max_val=len(self.dataset.predefined_table_types), level=level_val))

        notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject(msg=f'Сохранение данных завершено', cur_val=len(self.dataset.predefined_table_types), max_val=len(self.dataset.predefined_table_types), level=level_val))
        self._update_manager.set_notifier(None)
        progress.Close()
        self.main_menu.update_wxcommand_states()
        self.update_wxcommands()

    def _undo_changes_dataset(self):
        level_val = basic.default_notify_level
        progress = ProgressWnd(self.GetTopLevelParent(), 'Отмена изменений', wx.Size(300, 100))

        notifier = progress.get_notifier()
        notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject(msg=f'Отмена изменений', cur_val=0, max_val=len(self.dataset.predefined_table_types), level=level_val))
        self._update_manager.set_notifier(notifier)
        progress.Show()
        progress.Update()

        for i, t_type in enumerate(self.dataset.predefined_table_types):
            table = self.dataset.get_table(t_type)
            while table.history_can_undo():
                table.history_undo()
            notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Отмена изменений {table.name}', cur_val=i + 1, max_val=len(self.dataset.predefined_table_types), level=level_val))

        notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject(msg=f'Отмена изменений завершенf', cur_val=len(self.dataset.predefined_table_types), max_val=len(self.dataset.predefined_table_types), level=level_val))
        self._update_manager.set_notifier(None)
        progress.Close()
        self.main_menu.update_wxcommand_states()
        self.update_wxcommands()


    def _init_window_workspace(self):
        self.action_scripts = ActionScripts(self, self.dataset, self.app_logger, self.ini_file)

        actions_menu = BasicPopupMenu()


        sub_service_menu = BasicPopupMenu()

        #service_dialog_cmd = WxCommand(3101, 'Обслуживание БД', None, wx.ACCEL_NORMAL, wx.WXK_NONE, self.action_scripts.show_action_scripts_dialog)
        #sub_service_menu.add_item(service_dialog_cmd)



        import_employees_execute = WxCommand(3102, 'Выполнить проверку', None, wx.ACCEL_NORMAL, wx.WXK_NONE, self.action_scripts.wxcommand_check_employees)
        sub_service_menu.add_item(import_employees_execute)

        sub_service_menu.add_separator()

        import_employees_cmd = WxCommand(3103, 'Настройка проверки', None, wx.ACCEL_NORMAL, wx.WXK_NONE, self.action_scripts.wxcommand_edit_import_employees_config)
        sub_service_menu.add_item(import_employees_cmd)

        actions_menu.add_submenu('Проверка сотрудников',sub_service_menu, 3100)

        copy_trainings_cmd = WxCommand(3104, 'Скопировать обучения', None, wx.ACCEL_NORMAL, wx.WXK_NONE, self.action_scripts.wxcommand_copy_trainings)
        actions_menu.add_item(copy_trainings_cmd)

        check_files = WxCommand(3105, 'Проверить файлы', None, wx.ACCEL_NORMAL, wx.WXK_NONE, self.action_scripts.wxcommand_file_structure)
        actions_menu.add_item(check_files)



        self.main_menu.add_menu(actions_menu,'Действия', 3000)




        self.check_fs_folders()
        self.status_manager.init()
        self.status_manager.show_current_file_name(self.dataset.name)
        notifier = self._update_manager.get_notifier()
        notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject(msg=f'Загрузка интерфейса'))

        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()


        self.book = BasicSideNotebook(self.main_panel, left_notebook_image_size)
        self.book.register_on_changed(self.on_side_notebook_page_changed)
        self.book.set_colour(1, wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE))  # active tab background color
        self.book.set_colour(0, wx.ColourDatabase().FindColour("SKY BLUE"))  # label book background color
        self.book.set_colour(2, wx.ColourDatabase().FindColour("NAVY"))  # label book tab border color

        self.main_sizer.Add(self.book, 1, wx.EXPAND | wx.ALL, 0)

        act_training_panel = self._create_active_training_panel(self.book)
        self._panels.append(act_training_panel)
        self.book.add_page('Обучения', act_training_panel)
        self.book.add_image('trainings', os.path.join(app_settings.run_path, r'Icons\MainNotebook\trainings.ico'))
        self.book.set_page_image('Обучения', 'trainings')

        train_request = self._create_train_request_panel(self.book)
        self._panels.append(train_request)
        self.book.add_page('Заявки', train_request)
        self.book.add_image('tasks', os.path.join(app_settings.run_path, r'Icons\MainNotebook\tasks.ico'))
        self.book.set_page_image('Заявки', 'tasks')

        #
        #structure_panel = self._create_structure_panel(self.book, act_training_panel)
        #self.book.add_page('Структура', structure_panel)
        #self._panels.append(structure_panel)
        #self.book.add_image('structure', os.path.join(app_settings.run_path, r'Icons\MainNotebook\structure.ico'))
        #self.book.set_page_image('Структура', 'structure')

        personnel_doc_panel = self._create_personnel_doc_panel(self.book)
        self.book.add_page('Документы', personnel_doc_panel)
        self._panels.append(personnel_doc_panel)
        self.book.add_image('documents', os.path.join(app_settings.run_path, r'Icons\MainNotebook\personnel_info.ico'))
        self.book.set_page_image('Документы', 'documents')


        rt_notebook = NotebookPanel(self.book, notebook_image_size, self._update_manager)
        self._notebooks['rt_notebook'] = rt_notebook

        train_type_panel = self._create_train_type_panel(rt_notebook)
        self._panels.append(train_type_panel)
        rt_notebook.add_page('Виды обучений', train_type_panel)

        required_train_type_panel = self._create_required_train_type_panel(rt_notebook)
        self._panels.append(required_train_type_panel)
        rt_notebook.add_page('Требуемые обучения', required_train_type_panel)



        recommended_train_type_panel = self._create_recommended_train_type_panel(rt_notebook)
        self._panels.append(recommended_train_type_panel)
        rt_notebook.add_page('Рекомендуемые обучения', recommended_train_type_panel)


        self.book.add_page('Требуемые обучения', rt_notebook)
        self.book.add_image('required_trainings', os.path.join(app_settings.run_path, r'Icons\MainNotebook\required.ico'))
        self.book.set_page_image('Требуемые обучения', 'required_trainings')

        ref_notebook = NotebookPanel(self.book, notebook_image_size, self._update_manager)
        self._notebooks['ref_notebook'] = ref_notebook
        persons_panel = self._create_persons_panel(ref_notebook)
        self._panels.append(persons_panel)
        ref_notebook.add_page('Личности', persons_panel)

        employees_panel = self._create_employees_panel(ref_notebook)
        self._panels.append(employees_panel)
        ref_notebook.add_page('Сотрудники', employees_panel)

        positions_panel = self._create_positions_panel(ref_notebook)
        self._panels.append(positions_panel)
        ref_notebook.add_page('Должности', positions_panel)

        department_panel = self._create_deparment_panel(ref_notebook)
        self._panels.append(department_panel)
        ref_notebook.add_page('Подразделения', department_panel)

        company_panel = self._create_company_panel(ref_notebook)
        self._panels.append(company_panel)
        ref_notebook.add_page('Организации', company_panel)

        self.book.add_page('Справочники', ref_notebook)
        self.book.add_image('references', os.path.join(app_settings.run_path, r'Icons\MainNotebook\references.ico'))
        self.book.set_page_image('Справочники', 'references')



        for panel in self._panels:
            panel_ini = self.dataset.get_config(panel.name)
            panel.init_panel(panel_ini)

        global_ini = self.dataset.get_config('global_cfg')
        if global_ini:
            if global_ini.has_section('global'):
                if global_ini.has_option('global', 'notebook_page'):
                    page_name = global_ini['global']['notebook_page']
                    if self.book.have_page(page_name):
                        self.book.select_page(page_name)
                    #self.on_side_notebook_page_changed(None, page_name)
            if global_ini.has_section('notebooks'):
                for notebook_name, notebook_item in self._notebooks.items():
                    if global_ini.has_option('notebooks',notebook_name):
                        page_name = global_ini['notebooks'][notebook_name]
                        if notebook_item.have_page(page_name):
                            notebook_item.select_page(page_name)
                            notebook_item.on_show_panel(True)
        self.Layout()
        self.update_wxcommands()
        self.main_menu.update_wxcommand_states()
        if not busy:
            wx.EndBusyCursor()
        notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject(msg=f'Загрузка интерфейса'))


    def _deinit_window_workspace(self):
        self._update_manager.stop()
        self.main_menu.delete_menu(3000)



        progress = ProgressWnd(self.main_panel.GetTopLevelParent(), 'Сохранение', wx.Size(300, 100))
        progress.CenterOnParent()
        progress.Show()
        notifier = progress.get_notifier()
        notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Сохранение конфигурации'))


        for panel in self._panels:
            panel_ini = panel.deinit_panel()
            self.dataset.write_config(panel.name, panel_ini,False,None)
        self._panels.clear()

        global_ini = configparser.ConfigParser()
        global_ini.add_section('global')
        global_ini['global']['notebook_page'] = self.book.get_selected_page_name() or ""

        global_ini.add_section('notebooks')

        for notebook_name, notebook_item in self._notebooks.items():
            global_ini['notebooks'][f'{notebook_name}'] = notebook_item.get_selected_page_name()

        self.dataset.write_config('global_cfg', global_ini, False, None)
        self._notebooks.clear()



        self.book.Destroy()
        self.book = None
        notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Сохранение конфигурации завершено'))
        progress.Close()
        self.status_manager.show_current_file_name('')

    def on_side_notebook_page_changed(self, old_page_name: Optional[str], new_page_name: str):
        old_page = self.book.get_page(old_page_name)
        new_page = self.book.get_page(new_page_name)
        if old_page:
            if issubclass(type(old_page), (TableEditorPanel, NotebookPanel)):
                old_page.on_show_panel(False)
        if new_page:
            if issubclass(type(new_page), (TableEditorPanel, NotebookPanel)):
                new_page.on_show_panel(True)


    def _create_persons_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.Person)
        config.grid_table = config.table
        config.columns = [  ('Фамилия Имя Отчество', str, True, BTFilterType.STRING, None, None),
                            ('Дата\nрождения', datetime.date, True, BTFilterType.DATE, None, None),
                            ('Место\nрождения', str, True, BTFilterType.STRING,  None, None),
                            ('Паспорт', str, True, BTFilterType.STRING, None, None),
                            ('СНИЛС', str, True, BTFilterType.STRING, None, None),
                            ('ИНН', str, True, BTFilterType.STRING, None, None),
                            ('e-mail', List[str], True, BTFilterType.STRING, None, None),
                            ('телефоны', List[str], True, BTFilterType.STRING, None, None),
                            ('Имя\nпользователя', str, True, BTFilterType.STRING, None, None, None),
                            ('Задействован', bool, True, BTFilterType.BOOL, None, None)]
        config.can_edit_multiple = False
        config.can_use_history = True
        def convert_row(person: basicclasses.Person):
            answ = [f'{person.last_name or ""} {person.first_name or ""} {person.middle_name or ""}',
                    person.birth_date,
                    person.birth_place or "",
                    f'{person.passport_series or ""} {person.passport_number or ""} выдан: {person.passport_issued or ""} {person.passport_issued_date.strftime(app_settings.date_format) + " г." if person.passport_issued_date else ""}, код: {person.passport_issued_code or ""}',
                    person.ssn_number or "",
                    person.taxnumber_number or "",
                    person.emails or "",
                    person.phones or "",
                    person.user_name or "",
                    person.active or False
                    ]
            return answ
        config.convert_row = convert_row

        config.dialog_cfg = [   DBInputDialogConfig('last_name', str, 'Фамилия', False, 150, -1, None, None),
                                DBInputDialogConfig('first_name', str, 'Имя', False,150, -1, None, None),
                                DBInputDialogConfig('middle_name', str, 'Отчество', False,150, -1, None, None),
                                DBInputDialogConfig('birth_date', datetime.date, 'Дата рождения', False,120, -1, None, None),
                                DBInputDialogConfig('birth_place', str, 'Место рождения', False,-1, -1, None, None),
                                DBInputDialogConfig('passport_series', str, 'Паспорт: серия', False,120, -1, None, None),
                                DBInputDialogConfig('passport_number', str, 'Паспорт: номер', False,180, -1, None, None),
                                DBInputDialogConfig('passport_issued', str, 'Паспорт: выдан', False,-1, -1, None, None),
                                DBInputDialogConfig('passport_issued_date', datetime.date, 'Паспорт: дата выдачи',False, 120, -1, None, None),
                                DBInputDialogConfig('passport_valid_till_date', datetime.date, 'Паспорт: действует до', False,120, -1, None, None),
                                DBInputDialogConfig('passport_issued_code', str, 'Паспорт: код подразделения', False,150, -1, None, None),
                                DBInputDialogConfig('living_place', str, 'Место жительства',False, -1, -1, None, None),
                                DBInputDialogConfig('ssn_number', str, 'СНИЛС: номер', False,150, -1, None, None),
                                DBInputDialogConfig('ssn_issued_date', datetime.date, 'СНИЛС: дата выдачи', False,120, -1, None, None),
                                DBInputDialogConfig('taxnumber_number', str, 'ИНН: номер',False, 150, -1, None, None),
                                DBInputDialogConfig('taxnumber_issued_date', datetime.date, 'ИНН: дата выдачи',False, 120, -1, None, None),
                                DBInputDialogConfig('phones', List[str], 'Телефоны', False,150, -1, None, None),
                                DBInputDialogConfig('emails', List[str], 'e-mail-ы', False, 150, -1, None, None),
                                DBInputDialogConfig('user_name', str, 'Имя пользователя', False,150, -1, None, None)
                                ]

        def dialog_val_changed(io_panel: InputOutputPanel, _name: str, db_row: DBStorableRow):
            required_fields = {'last_name': 'фамилия',
                               'first_name': 'имя',
                               'middle_name': 'отчество',
                               'birth_date': 'дата рождения'
                   }
            warning_list = []
            for n, descr in required_fields.items():
                val = io_panel.get_property(n, False)
                if not val:
                    warning_list.append(required_fields[n])
            last_name = io_panel.get_property('last_name', False)
            first_name = io_panel.get_property('first_name', False)
            middle_name = io_panel.get_property('middle_name', False)
            birth_date: datetime.date = io_panel.get_property('birth_date', False)
            item: basicclasses.Person

            info_items: List[Tuple[ImageList.BuiltInImage, str]] = []
            for item in self.dataset.get_table(basicclasses.Person).get_items():
                if db_row is not None:
                    if type(db_row) == list:
                        if item in db_row:
                            continue
                    else:
                        if item == db_row:
                            continue
                if item.first_name == first_name and item.last_name == last_name and item.middle_name == middle_name and item.birth_date == birth_date:
                    info_msg = f'Для элемента {last_name} {first_name} {middle_name} {birth_date.strftime(app_settings.date_format) if birth_date else ""} найден такой-же элемент:{item.guid}'
                    info_items.append((ImageList.BuiltInImage.WARNING, info_msg))
            set_io_panel_warnings(self.app_logger, io_panel, info_items, warning_list)

        config.on_dialog_val_delayed_changed = dialog_val_changed


        def dialog_can_add_or_insert(_person: basicclasses.Person, _add: bool)->Tuple[bool, str]:
            return True, ''





        config.can_add_or_insert_data = dialog_can_add_or_insert


        panel = TableEditorPanel(parent, 'Личности', self.app_logger, self.status_manager, self.main_menu,config, self._update_manager)

        return panel

    def _create_employees_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.Employee)
        config.grid_table = config.table
        config.columns = [              ('Фамилия Имя Отчество', str, True, BTFilterType.STRING,None, None),
                                        ('Должность', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                                        ('Подразделение', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                                        ('Организация', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                                        ('Табельный №', str, True, BTFilterType.STRING, None, None),
                                        ('Дата\nтрудоустройства', datetime.date, True, BTFilterType.DATE, None, None),
                                        ('Дата\nувольнения', datetime.date, True, BTFilterType.DATE, None, None),
                                        ('Причина увольнения', str, True, BTFilterType.STRING, None, None)
                                        ]
        config.can_edit_multiple = False
        config.can_use_history = True


        def convert_row(employee: basicclasses.Employee):
            answ = [f'{employee.person.full_name or ""}',
                    f'{employee.position.name or ""}',
                    f'{employee.department.name or ""}',
                    f'{employee.company.company_short_name or ""}',
                    f'{employee.payroll_number or ""}',
                    employee.hire_date,
                    employee.fire_date,
                    f'{employee.fire_reason or ""}'
                    ]
            return answ
        config.convert_row = convert_row

        config.dialog_cfg = [       DBInputDialogConfig('person', BasicCombobox, 'Личность', False,-1, -1, None, self.dataset.person_cb_values),
                                    DBInputDialogConfig('position', BasicCombobox, 'Должность', False,-1, -1, None, self.dataset.position_cb_values),
                                    DBInputDialogConfig('department', BasicCombobox, 'Подразделение', False,-1, -1, None, self.dataset.department_cb_values),
                                    DBInputDialogConfig('company', BasicCombobox, 'Организация',False, -1, -1, None, self.dataset.company_cb_values),
                                    DBInputDialogConfig('payroll_number', str, 'Табельный номер', False,100, -1, None, None),
                                    DBInputDialogConfig('hire_date', datetime.date, 'Дата приёма', False,120, -1, None, None),
                                    DBInputDialogConfig('fire_date', datetime.date, 'Дата увольнения',False, 120, -1, None, None),
                                    DBInputDialogConfig('fire_reason', str, 'Причина увольнения',False, -1, -1, None, None)
                                ]
        def dialog_val_changed(io_panel: InputOutputPanel, _name: str, db_row: DBStorableRow):
            required_fields = {'person': 'личность',
                               'position': 'должность',
                               'department': 'подразделение',
                               'company': 'организация',
                               'hire_date': 'дата приёма'
                               }
            warning_list = []
            for n, descr in required_fields.items():
                val = io_panel.get_property(n, False)
                if not val:
                    warning_list.append(required_fields[n])
            person = io_panel.get_property('person', False)
            position = io_panel.get_property('position', False)
            department = io_panel.get_property('department', False)
            company: datetime.date = io_panel.get_property('company', False)
            item: basicclasses.Employee

            info_items: List[Tuple[ImageList.BuiltInImage, str]] = []
            for item in self.dataset.get_table(basicclasses.Employee).get_items():
                if db_row is not None:
                    if type(db_row) == list:
                        if item in db_row:
                            continue
                    else:
                        if item == db_row:
                            continue
                if item.person == person and item.position == position and item.department == department and item.company == company:
                    info_msg = f'Для элемента {person.full_name_with_date} {position.name} {department.name} найден такой-же элемент:{item.guid}'
                    info_items.append((ImageList.BuiltInImage.WARNING, info_msg))
            set_io_panel_warnings(self.app_logger, io_panel, info_items, warning_list)

        config.on_dialog_val_delayed_changed = dialog_val_changed


        def before_show_dialog(io_panel: InputOutputPanel, _row: basicclasses.Employee, add: bool, _multiple: bool):
            if not add:
                io_panel.enable_property('person', False)
                #io_panel.enable_property('position', False)
                io_panel.enable_property('department', False)
                io_panel.enable_property('company', False)

        config.before_show_dialog = before_show_dialog

        def dialog_can_add_or_insert(employee: basicclasses.Employee, _add: bool)->Tuple[bool, str]:
            item: basicclasses.Employee
            if not employee.person:
                return False, 'Должен быть указан сотрудник'
            if not employee.position:
                return False, 'Должна быть указана должность'
            if not employee.department:
                return False, 'Должно быть указано подразделение'
            if not employee.company:
                return False, 'Должна быть указана организация'
            if not employee.hire_date:
                return False, 'Должна быть указана дата приёма'

            for item in self.dataset.get_table(basicclasses.Employee).get_items():
                if item.guid == employee.guid:
                    continue
                if item.person == employee.person and item.position == employee.position and item.department == employee.department:
                    return False, 'Такой сотрудник с такой же должностью в данном подразделении уже существует'
            return True, ''

        config.can_add_or_insert_data = dialog_can_add_or_insert

        def on_control_c(grid: BasicGrid):
            selected_items: List[basicclasses.Employee] = grid.table.get_selected_objects()
            clipboard: Clipboard = Clipboard()
            output_text = ''
            for item in selected_items:
                output_text += f'{item.person.full_name}\t{item.position.name}\t{item.department.name}\n'
            clipboard.write_text(output_text)

        config.on_control_c = on_control_c

        panel = TableEditorPanel(parent, 'Сотрудники', self.app_logger, self.status_manager, self.main_menu,config, self._update_manager)



        def wxcommand_show_number_trainings(_evt: wx.CommandEvent):
            busy = wx.IsBusy()
            if not busy:
                wx.BeginBusyCursor()
            sel_employees: List[basicclasses.Employee] = panel.grid.table.get_selected_objects()
            found_list = []
            item: basicclasses.Training
            for item in self.dataset.get_table(basicclasses.Training).get_items():
                if item.employee == sel_employees[0]:
                    found_list.append(f'{item.employee.person.full_name_with_date} {item.training_name}')
            if not busy:
                wx.EndBusyCursor()

            show_info_window(self.app_logger, self, 'Обучения',found_list)

        def wxcommand_can_show_trainings():
            return panel._selected_rows==1

        show_trainings = WxCommand(2001, "Показать обучения", os.path.join(app_settings.run_path, r'Icons\MainNotebook\trainings.ico'), acc_control_key=wx.ACCEL_NORMAL, acc_main_key=wx.WXK_NONE, execute_func=wxcommand_show_number_trainings, can_execute_func=wxcommand_can_show_trainings)
        panel.toolbar.add_tool_item(show_trainings)
        panel.add_wxcommand(show_trainings)
        panel.toolbar.update_wxcommand_states()
        panel.update_wxcommands()

        return panel

    def _create_deparment_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.Department)
        config.grid_table = config.table
        config.columns = [  ('Название', str, True, BTFilterType.STRING, None, None),
                            ('Код', str, True, BTFilterType.STRING, None, None),
                            ('Город', str, True, BTFilterType.STRING, None, None)]
        config.can_edit_multiple = False
        config.can_use_history = True
        def convert_row(department: basicclasses.Department):
            answ = [f'{department.name or ""}',
                    f'{department.code or ""}',
                    f'{department.city or ""}'
                    ]
            return answ
        config.convert_row = convert_row

        config.dialog_cfg = [   DBInputDialogConfig('name', str, 'Наименование', False,-1, -1, None, None),
                                DBInputDialogConfig('code', str, 'Код', False, 100, -1, None, None),
                                DBInputDialogConfig('city', str, 'Город', False,-1, -1, None, None)
                                ]
        def dialog_val_changed(io_panel: InputOutputPanel, _name: str, db_row: DBStorableRow):
            required_fields = {'name': 'наименование',
                               'code': 'код подразделения',
                               'city': 'город'
                               }
            warning_list = []
            for n, descr in required_fields.items():
                val = io_panel.get_property(n, False)
                if not val:
                    warning_list.append(required_fields[n])
            name = io_panel.get_property('name', False)
            code = io_panel.get_property('code', False)
            city = io_panel.get_property('city', False)

            item: basicclasses.Department

            info_items: List[Tuple[ImageList.BuiltInImage, str]] = []
            for item in self.dataset.get_table(basicclasses.Department).get_items():
                if db_row is not None:
                    if type(db_row) == list:
                        if item in db_row:
                            continue
                    else:
                        if item == db_row:
                            continue
                if item.name == name or item.city == city or item.code == code and db_row.guid != item.guid:
                    info_msg = f'Для элемента {item.name} найден такой-же элемент:{item.guid} {item.name} {item.city} {item.code}'
                    info_items.append((ImageList.BuiltInImage.WARNING, info_msg))
            set_io_panel_warnings(self.app_logger, io_panel, info_items, warning_list)

        config.on_dialog_val_delayed_changed = dialog_val_changed


        def dialog_can_add_or_insert(department: basicclasses.Department, _add: bool)->Tuple[bool, str]:
            item: basicclasses.Department
            if not department.name or len(department.name) == 0:
                return False, 'Подразделение должно иметь наименование'
            for item in self.dataset.get_table(basicclasses.Department).get_items():
                if item.guid == department.guid:
                    continue
                if item.name == department.name:
                    return False, 'Подразделение с таким наименованием уже существует'
                #if item.code and item.code == department.code and item.guid != department.guid:
                #    return False, 'Подразделение с таким кодом уже существует'
                #if item.city and item.city == department.city and item.guid != department.guid:
                #    return False, 'Подразделение в таком городе уже существует'
            return True, ''

        config.can_add_or_insert_data = dialog_can_add_or_insert

        panel = TableEditorPanel(parent, 'Подразделения', self.app_logger, self.status_manager, self.main_menu,config, self._update_manager)
        return panel

    def _create_positions_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.Position)
        config.grid_table = config.table
        config.columns = [  ('Название', str, True, BTFilterType.STRING, None, None),
                            ('Краткое название', str, True, BTFilterType.STRING, None, None),
                            ('Комментарий', str, True, BTFilterType.STRING, None, None)
                            ]
        config.can_edit_multiple = False
        config.can_use_history = True
        def convert_row(position: basicclasses.Position):
            answ = [f'{position.name or ""}',
                    f'{position.short_name or ""}',
                    f'{position.description or ""}',
                    ]
            return answ
        config.convert_row = convert_row

        config.dialog_cfg = [   DBInputDialogConfig('name', str, 'Название', False,-1, -1, None, None),
                                DBInputDialogConfig('short_name', str, 'Краткое название', False,150, -1, None, None),
                                DBInputDialogConfig('description', str, 'Комментарий', False, 150, -1, None, None)
                                ]
        def dialog_val_changed(io_panel: InputOutputPanel, _name: str, db_row: DBStorableRow):
            required_fields = {'name': 'название',
                               'short_name': 'краткое название'
                               }
            warning_list = []
            for n, descr in required_fields.items():
                val = io_panel.get_property(n, False)
                if not val:
                    warning_list.append(required_fields[n])

            name = io_panel.get_property('name', False)
            short_name = io_panel.get_property('short_name', False)

            item: basicclasses.Position

            info_items: List[Tuple[ImageList.BuiltInImage, str]] = []
            for item in self.dataset.get_table(basicclasses.Position).get_items():
                if db_row is not None:
                    if type(db_row) == list:
                        if item in db_row:
                            continue
                    else:
                        if item == db_row:
                            continue
                if item.name == name or item.short_name == short_name:
                    info_msg = f'Для элемента {item.name} найден такой-же элемент:{item.guid}'
                    info_items.append((ImageList.BuiltInImage.WARNING, info_msg))
            set_io_panel_warnings(self.app_logger, io_panel, info_items, warning_list)

        config.on_dialog_val_delayed_changed = dialog_val_changed


        def dialog_can_add_or_insert(position: basicclasses.Position, _add: bool)->Tuple[bool, str]:
            item1: basicclasses.Position
            for item1 in self.dataset.get_table(basicclasses.Position).get_items():
                if item1.guid == position.guid:
                    continue
                if item1.name == position.name or item1.short_name == position.short_name:
                    return False, 'Должность с таким наименованием уже существует'
            return True, ''

        config.can_add_or_insert_data = dialog_can_add_or_insert

        panel = TableEditorPanel(parent, 'Должности', self.app_logger, self.status_manager, self.main_menu,config, self._update_manager)
        return panel

    def _create_company_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.Company)
        config.grid_table = config.table
        config.columns = [  ('Вид', str, True, BTFilterType.LIST, None, None),
                            ('Краткое\nнаименование', str, True, BTFilterType.STRING, None, None),
                            ('Полное\nНаименование', str, True, BTFilterType.STRING, None, None)]
        config.can_edit_multiple = False
        config.can_use_history = True
        def convert_row(company: basicclasses.Company):
            answ = [f'{company.prefix.short_name or ""}',
                    f'{company.short_name or ""}',
                    f'{company.name or ""}'
                    ]
            return answ
        config.convert_row = convert_row

        config.dialog_cfg = [   DBInputDialogConfig('prefix', BasicCombobox, 'Вид организации', False,100, -1, None, self.dataset.company_prefixes_cb_values),
                                DBInputDialogConfig('short_name', str, 'Краткое наименование', False,200, -1, None, None),
                                DBInputDialogConfig('name', str, 'Полное Наименование', False,-1, -1, None, None)
                                ]

        def dialog_val_changed(io_panel: InputOutputPanel, _name: str, db_row: DBStorableRow):
            required_fields = {'prefix': 'вид организации',
                               'short_name': 'корокое наименование',
                               'name': 'наименование'
                               }
            warning_list = []
            for n, descr in required_fields.items():
                val = io_panel.get_property(n, False)
                if not val:
                    warning_list.append(required_fields[n])

            prefix = io_panel.get_property('prefix', False)
            short_name = io_panel.get_property('short_name', False)
            name = io_panel.get_property('name', False)

            item: basicclasses.Company

            info_items: List[Tuple[ImageList.BuiltInImage, str]] = []
            for item in self.dataset.get_table(basicclasses.Company).get_items():
                if db_row is not None:
                    if type(db_row) == list:
                        if item in db_row:
                            continue
                    else:
                        if item == db_row:
                            continue
                if (item.prefix == prefix and item.short_name == short_name) or (item.prefix == prefix and item.name == name):
                    info_msg = f'Для элемента {item.company_short_name} найден такой-же элемент:{item.guid}'
                    info_items.append((ImageList.BuiltInImage.WARNING, info_msg))
            set_io_panel_warnings(self.app_logger, io_panel, info_items, warning_list)

        config.on_dialog_val_delayed_changed = dialog_val_changed


        def dialog_can_add_or_insert(company: basicclasses.Company, _add: bool)->Tuple[bool, str]:
            item: basicclasses.Company
            if not company.name or len(company.name) == 0:
                return False, 'Организация должна иметь краткое наименование'
            if not company.short_name or len(company.short_name) == 0:
                return False, 'Организация должна иметь полное наименование'
            if not company.name[0].isalnum() or not company.name[len(company.name) - 1].isalnum():
                return False, 'Наименование организации должно начинаться с буквы или цифры'
            if not company.short_name[0].isalnum() or not company.short_name[len(company.short_name) - 1].isalnum():
                return False, 'Краткое наименование организации должно начинаться с буквы или цифры'

            for item in self.dataset.get_table(basicclasses.Company).get_items():
                if item.guid == company.guid:
                    continue

                if ((item.name == company.name or
                     item.short_name == company.short_name) and item.prefix == company.prefix):
                    return False, 'Организация с таким наименованием уже существует'
            return True, ''

        config.can_add_or_insert_data = dialog_can_add_or_insert

        panel = TableEditorPanel(parent, 'Организации', self.app_logger, self.status_manager, self.main_menu,config, self._update_manager)
        return panel

    def _create_train_type_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.TrainType)
        config.grid_table = config.table
        config.columns = [  ('Короткое\nназвание', str, True, BTFilterType.STRING, None, None),
                            ('Полное\nназвание', str, True, BTFilterType.STRING, None, None),
                            ('Срок\nдействия, лет', str, True, BTFilterType.STRING, None, None),
                            ('Длительность\nобучения, час', str, True, BTFilterType.STRING, None, None),
                            ('Виды документов', str, True, BTFilterType.STRING, None, None) ]
        config.can_edit_multiple = False
        config.can_use_history = True
        def convert_row(train_type: basicclasses.TrainType):
            doc_names = []
            for d in train_type.doc_types:
                doc_names.append(d.full_name)
            answ = [f'{train_type.short_name or ""}',
                    f'{train_type.name or ""}',
                    train_type.valid_period_year,
                    train_type.train_period_hours,
                    ','.join(doc_names)
                    ]
            return answ
        config.convert_row = convert_row

        config.dialog_cfg = [   DBInputDialogConfig('short_name', str, 'Короткое наименование', False,200, -1, None, None),
                                DBInputDialogConfig('name', str, 'Полное наименование', False,-1, -1, None, None),
                                DBInputDialogConfig('valid_period_year', float, 'Срок действия, лет', False,50, -1, None, None),
                                DBInputDialogConfig('train_period_hours', int, 'Время обучения, час', False,50, -1, None, None),
                                DBInputDialogConfig('doc_types', BasicCheckList, 'Виды документов', False, -1, -1, None, self.dataset.doc_types_cb_values)
                                ]

        def dialog_val_changed(io_panel: InputOutputPanel, _name: str, db_row: DBStorableRow):
            required_fields = {'name': 'наименование',
                               'short_name': 'короткое наименование',
                               'doc_types': 'вид документа'}
            warning_list = []
            for n, descr in required_fields.items():
                val = io_panel.get_property(n, False)
                if not val:
                    warning_list.append(required_fields[n])

            name = io_panel.get_property('name', False)
            short_name = io_panel.get_property('short_name', False)

            item: basicclasses.TrainType

            info_items: List[Tuple[ImageList.BuiltInImage, str]] = []
            for item in self.dataset.get_table(basicclasses.TrainType).get_items():
                if db_row is not None:
                    if type(db_row) == list:
                        if item in db_row:
                            continue
                    else:
                        if item == db_row:
                            continue
                if item.name == name or item.short_name == short_name:
                    info_msg = f'Для элемента {item.name} найден такой-же элемент:{item.guid}'
                    info_items.append((ImageList.BuiltInImage.WARNING, info_msg))
            set_io_panel_warnings(self.app_logger, io_panel, info_items, warning_list)

        config.on_dialog_val_delayed_changed = dialog_val_changed


        def dialog_can_add_or_insert(train_type: basicclasses.TrainType, _add: bool)->Tuple[bool, str]:
            item: basicclasses.TrainType
            if not train_type.name or len(train_type.name) == 0:
                return False, 'Тип обучения должен иметь полное наименование'

            if not train_type.short_name or len(train_type.short_name) == 0:
                return False, 'Тип обучения должен иметь короткое наименование'

            for item in self.dataset.get_table(basicclasses.TrainType).get_items():
                if item.guid == train_type.guid:
                    continue
                if item.name == train_type.name:
                    return False, 'Тип обучения с таким длинным наименованием уже существует'
                if item.short_name == train_type.short_name:
                    return False, 'Тип обучения с таким коротким наименованием уже существует'
            return True, ''

        config.can_add_or_insert_data = dialog_can_add_or_insert

        panel = TableEditorPanel(parent, 'Виды обучений', self.app_logger, self.status_manager, self.main_menu,config, self._update_manager)
        return panel

    def _create_required_train_type_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.TrainingRequired)
        config.grid_table = config.table
        config.columns = [  ('Фамилия Имя Отчество', str, True, BTFilterType.STRING, None, None),
                            ('Должность', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                            ('Подразделение', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                            ('Тип обучения', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                            ('Требуется', bool, True, BTFilterType.BOOL, None, None),
                            ('Начало', datetime.date, True, BTFilterType.DATE, None, None),
                            ('Окончание', datetime.date, True, BTFilterType.DATE, None, None),
                            ('Рекомен-\nдуется', bool, True, BTFilterType.BOOL, None, None),
                            ('Уволен', bool, True, BTFilterType.BOOL, None, None),
                            ('Организация', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None)]

        config.can_edit_multiple = True
        config.can_edit = True
        config.can_add = True
        config.can_delete = True
        config.can_use_history = False

        def get_recommended(employee: basicclasses.Employee, train_type: basicclasses.TrainType):
            return self.dataset.is_recommended(employee, train_type)

        def convert_row(train_type_required: basicclasses.TrainingRequired):
            answ = [f'{train_type_required.employee.person.full_name or ""}',
                    f'{train_type_required.employee.position.name or ""}',
                    f'{train_type_required.employee.department.name or ""}',
                    f'{train_type_required.train_type.short_name or ""}',
                    train_type_required.required,
                    train_type_required.start_date,
                    train_type_required.stop_date,
                    get_recommended(train_type_required.employee, train_type_required.train_type),
                    train_type_required.employee.fire_date is not None,
                    f'{train_type_required.employee.company.company_short_name or ""}'
                    ]
            return answ
        config.convert_row = convert_row

        config.dialog_cfg = [   DBInputDialogConfig('start_date', datetime.date, 'Дата начала',True, 120, -1, None, None),
                                DBInputDialogConfig('stop_date', datetime.date, 'Дата окончания', True, 120, -1, None, 'Игнорировать'),
                                DBInputDialogConfig('required', bool, 'Требуется', True, 50, -1, None, None)]

        def before_show_dialog(io_panel: InputOutputPanel, _row: basicclasses.Employee, add: bool, multiple: bool):
            if not add and not multiple:
                io_panel.set_property_param('required','third_state', False)

        config.before_show_dialog = before_show_dialog

        def dialog_val_changed(io_panel: InputOutputPanel, _name: str, _db_row: DBStorableRow):
            required_fields = {'employees': 'сотрудник',
                               'train_type': 'тип обучения'}
            warning_list = []
            for n, descr in required_fields.items():
                if io_panel.have_property(n):
                    val = io_panel.get_property(n, False)
                    if not val:
                        warning_list.append(required_fields[n])

            #prefix = io_panel.get_property('prefix', False)
            #short_name = io_panel.get_property('short_name', False)
            #name = io_panel.get_property('name', False)

            item: basicclasses.TrainingRequired

            info_items: List[Tuple[ImageList.BuiltInImage, str]] = []

            set_io_panel_warnings(self.app_logger, io_panel, info_items, warning_list)

        config.on_dialog_val_delayed_changed = dialog_val_changed


        def dialog_can_add_or_insert(tt_required: basicclasses.TrainingRequired, _add: bool)->Tuple[bool, str]:
            item: basicclasses.TrainingRequired
            if hasattr(tt_required, 'train_type') and hasattr(tt_required, 'employee'):
                if not tt_required.train_type:
                    return False, 'Требуемое обучение должно иметь выбранный тип обучения'
                if not tt_required.employee:
                    return False, 'Требуемое обучение должно иметь выбранный тип сотрудника'


                for item in self.dataset.get_table(basicclasses.TrainingRequired).get_items():
                    if item.guid == tt_required.guid:
                        continue

                    if item.train_type == tt_required.train_type and \
                        item.employee == tt_required.employee:
                        return False, 'Требуемое обучение с таким сотрудником и типом обучения уже существует'
            return True, ''

        config.can_add_or_insert_data = dialog_can_add_or_insert

        panel = RequiredTrainingsPanel(parent, 'Требуемые обучения', self.app_logger, self.status_manager, self.main_menu, config, self._update_manager)
        return panel

    def _create_recommended_train_type_panel(self, parent):

        panel = RecommendedTrainingsPanel(parent, 'Рекомендуемые обучения', self.dataset)
        return panel

    def _create_train_request_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.TrainingRequest)
        config.grid_table = config.table
        config.columns = [  ('Сотрудник', str, True, BTFilterType.STRING, None, None),
                            ('Тип обучения', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                            ('Вид документа', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                            ('Дата\nзаявки', datetime.date, True, BTFilterType.DATE, None, None),
                            ('Дата\nзавершения', datetime.date, True, BTFilterType.DATE, None, None),
                            ('Заяв-\nлено', bool, True, BTFilterType.BOOL, None, None),
                            ('Завер-\nшено', bool, True, BTFilterType.BOOL, None, None)]

        config.can_edit_multiple = True
        config.can_edit = True
        config.can_add = True
        config.can_delete = True
        config.can_use_history = True



        def convert_row(train_request: basicclasses.TrainingRequest):
            employee_str = train_request.employee.person.full_name if train_request.employee else ""
            if employee_str:
                employee_str += " " + train_request.employee.position.short_name if train_request.employee.position else ""
            if employee_str:
                employee_str += " (" + train_request.employee.department.code + ")" if train_request.employee.department else ""

            answ = [f'{employee_str}',
                    f'{train_request.train_type.short_name or ""}',
                    f'{train_request.doc_type.full_name or ""}',
                    train_request.request_date,
                    train_request.complete_date,
                    train_request.requested,
                    train_request.completed
                    ]
            return answ
        config.convert_row = convert_row

        config.dialog_cfg = [   DBInputDialogConfig('employee', BasicCombobox, 'Сотрудник', False, -1, -1, None, self.dataset.employees_cb_values),
                                DBInputDialogConfig('train_type', BasicCombobox, 'Тип обучения', False, -1, -1, None, self.dataset.train_types_cb_values),
                                DBInputDialogConfig('doc_type', BasicCombobox, 'Вид документа', False, -1, -1, None, self.dataset.doc_types_cb_values),
                                DBInputDialogConfig('request_date', datetime.date, 'Дата заявки', True, 120, -1, None, 'Игнорировать'),
                                DBInputDialogConfig('complete_date', datetime.date, 'Дата завершения', True, 120, -1, None, 'Игнорировать')]

        def before_show_dialog(io_panel: InputOutputPanel, _row: basicclasses.TrainingRequest, add: bool, multiple: bool):
            if not add and not multiple:
                io_panel.enable_property('employee', False)
                io_panel.enable_property('train_type', False)
                io_panel.enable_property('doc_type', False)
            if multiple:
                io_panel.show_property('employee', False)
                io_panel.show_property('train_type', False)
                io_panel.show_property('doc_type', False)

            if add or not multiple:
                io_panel.set_property_param('request_date', 'third_state', False)
                io_panel.set_property_param('complete_date', 'third_state', False)


        config.before_show_dialog = before_show_dialog

        def dialog_val_changed(io_panel: InputOutputPanel, name: str, _db_row: basicclasses.TrainingRequest):
            if name == 'train_type':
                train_type: basicclasses.TrainType = io_panel.get_property('train_type',False)
                avail_doc_types = []
                old_doc_type = io_panel.get_property('doc_type', False)
                if old_doc_type not in train_type.doc_types:
                    old_doc_type = None
                for val in train_type.doc_types:
                    avail_doc_types.append((val.full_name, val))


                io_panel.set_property('doc_type', old_doc_type,avail_doc_types)
                if len(avail_doc_types) == 1:
                    io_panel.set_property('doc_type', avail_doc_types[0][1], None)

        def dialog_val_delayed_changed(io_panel: InputOutputPanel, _name: str, db_row: basicclasses.TrainingRequest):
            required_fields = {}
            warning_list = []
            for n, descr in required_fields.items():
                val = io_panel.get_property(n, False)
                if not val:
                    warning_list.append(required_fields[n])

            employee = io_panel.get_property('employee', False)
            train_type = io_panel.get_property('train_type', False)
            doc_type = io_panel.get_property('doc_type', False)
            item: basicclasses.TrainingRequest

            info_items: List[Tuple[ImageList.BuiltInImage, str]] = []
            for item in self.dataset.get_table(basicclasses.TrainingRequest).get_items():
                if db_row is not None:
                    if type(db_row) == list:
                        if item in db_row:
                            continue
                    else:
                        if item == db_row:
                            continue

                if item.employee == employee and item.train_type == train_type and item.doc_type == doc_type and not item.completed:
                    info_msg = f'Для элемента {item.employee.person.full_name} {item.train_type.short_name} {item.doc_type.full_name} {item.request_date.strftime(app_settings.date_format) if item.request_date else "без даты заявки"} найден такой-же элемент:{item.guid}'
                    info_items.append((ImageList.BuiltInImage.WARNING, info_msg))
            set_io_panel_warnings(self.app_logger, io_panel, info_items, warning_list)

        config.on_dialog_val_changed = dialog_val_changed
        config.on_dialog_val_delayed_changed = dialog_val_delayed_changed


        def dialog_can_add_or_insert(train_request: basicclasses.TrainingRequest, _add: bool)->Tuple[bool, str]:
            item: basicclasses.TrainingRequest
            for item in self.dataset.get_table(basicclasses.TrainingRequest).get_items():
                if item.guid == train_request.guid:
                    continue
                if item.employee == train_request.employee and item.train_type == train_request.train_type and item.doc_type == train_request.doc_type and not item.completed:
                    return False, 'Заявка с такими параметрами уже существует'
            return True, ''

        config.can_add_or_insert_data = dialog_can_add_or_insert

        panel = TableEditorPanel(parent, 'Заявки', self.app_logger, self.status_manager, self.main_menu,config, self._update_manager)
        ExportTrainRequest(panel, self._update_manager, self.app_logger)
        return panel

    def _create_personnel_doc_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.PersonallDocument)
        config.grid_table = config.table
        config.columns = [  ('Фамилия Имя Отчество', str, True, BTFilterType.STRING, None, None),
                            ('Вид документа', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                            ('Наименование\nдокумента', str, True, BTFilterType.STRING, None, None),
                            ('Информация о\nдокументе', str, True, BTFilterType.STRING, None, None),
                            ('Дата\nвыдачи', datetime.date, True, BTFilterType.DATE, None, None),
                            ('Наличие\nфайла', bool, True, BTFilterType.BOOL, None, None)]

        config.can_edit_multiple = False
        config.can_edit = True
        config.can_add = True
        config.can_delete = True
        config.can_use_history = True

        def convert_row(personal_doc: basicclasses.PersonallDocument):
            answ = [f'{personal_doc.person.full_name_with_date or ""}',
                    f'{personal_doc.doc_type.full_name or ""}',
                    f'{personal_doc.doc_name or ""}',
                    f'{personal_doc.doc_info or ""}',
                    personal_doc.issued_date,
                    personal_doc.doc_file_exists
                    ]
            return answ
        config.convert_row = convert_row

        config.dialog_cfg = [   DBInputDialogConfig('person', BasicCombobox, 'Фамилия Имя Отчество', False, -1, -1, None, self.dataset.person_cb_values),
                                DBInputDialogConfig('doc_type', BasicCombobox, 'Вид документа', False, -1, -1, None, self.dataset.personall_doc_types_cb_values),
                                DBInputDialogConfig('doc_name', str, 'Наименование\nдокумента', False, -1, -1, None, None),
                                DBInputDialogConfig('doc_info', str, 'Информация о документе', False, -1, -1, None, None),
                                DBInputDialogConfig('issued_date', datetime.date, 'Дата выдачи', False, 120, -1, None, None)]
        panel: TableEditorPanel = PersonallDocPanel(parent, 'Документы', self.app_logger, self.status_manager, self.main_menu,config, self._update_manager)
        return panel

    def _create_active_training_panel(self, parent):
        config = TableEditorConfig()
        config.table = self.dataset.get_table(basicclasses.Training)
        config.grid_table = self.dataset.get_table(basicclasses.ActiveTraining)
        config.columns = [  ('Сотрудник', str, True, BTFilterType.STRING, None, None),
                            ('Тип обучения', str, True, [BTFilterType.STRING, BTFilterType.LIST], None, None),
                            ('Дата\nначала', datetime.date, True, BTFilterType.DATE, None, None),
                            ('Дата\nокончания', datetime.date, True, BTFilterType.DATE, None, None),
                            ('До\nокончания', int, True, BTFilterType.INT, None, None),
                            ('Документы', str, True, [BTFilterType.LIST, BTFilterType.STRING], None, None),
                            ('Требуется', bool, True, BTFilterType.BOOL, None, None),
                            ('Заявка', bool, True, BTFilterType.BOOL, None, None)]

        config.can_edit_multiple = False
        config.can_edit = True
        config.can_add = True
        config.can_delete = True
        config.can_use_history = True

        def convert_row(act_training: basicclasses.ActiveTraining):
            def documents_str(tr_list: List[basicclasses.Training]):
                answ1 = []
                used_doc_types = []
                required_doc_types = []
                for tr in tr_list:
                    used_doc_types.append(tr.doc_type)
                    for dt in tr.train_type.doc_types:
                        if dt not in required_doc_types:
                            required_doc_types.append(dt)
                    answ1.append(f'{tr.doc_type.short_name:<7}: {tr.number if tr.number else "б/н"}{" от "+tr.issued_date.strftime(app_settings.date_format) if tr.issued_date else " б/даты"} {"(есть файл)" if tr.doc_file_exists else "(без файла)"}')
                for rdt in required_doc_types:
                    if rdt not in used_doc_types:
                        answ1.append(f'{rdt.short_name:<7}: отсутствует')
                return '\n'.join(answ1)


            employee_str = act_training.employee.person.full_name if act_training.employee else ""
            if employee_str:
                employee_str +=" "+act_training.employee.position.short_name if act_training.employee.position else ""
            if employee_str:
                employee_str += " (" + act_training.employee.department.code+")" if act_training.employee.department else ""
            days_remain = (act_training.stop_date - datetime.date.today()).days if act_training.stop_date else 0
            answ = [employee_str,
                    f'{act_training.train_type.short_name or ""}',
                    act_training.start_date,
                    act_training.stop_date,
                    days_remain,
                    documents_str(act_training.trainings),
                    act_training.required,
                    act_training.requested
                    ]
            return answ
        config.convert_row = convert_row

        panel = ActiveTrainingPanel(parent, 'Обучения', self.app_logger, self.status_manager, self.main_menu,config, self._update_manager, self.action_scripts)
        return panel



    #def _create_structure_panel(self, parent, act_training_panel: ActiveTrainingPanel):
    #    structure_panel = StructurePanel(parent, self.app_logger, self.status_manager, self.main_menu, self.dataset, self._update_manager, act_training_panel)
    #    return structure_panel



