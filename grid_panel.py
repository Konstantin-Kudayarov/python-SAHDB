import configparser
import os
import wx
import wx.grid


from typing import Optional, List, Tuple, Type, Any, Callable, Union, Dict

import basic
import gui_widgets
from basic import (Logger, EventSubscriber, EventType, EventProgressObject,
                   EventObject, config_parser_from_string, config_parser_to_string, normalize_words)

from gui_widgets import (BasicPanel, BasicMenu,
                         BasicToolBar, WxCommand, BasicNotebook, DBInputDialog,
                         DBInputDialogConfig, ProgressWnd, message_box, InputOutputPanel, PropertyType)


from gui_widgets_grid import BTFilterType, BasicGrid, BasicTable, BasicTableConfig
from update_manager import MainWindowStatusBar, UpdateManager
from basicclasses import MainDatabase, app_settings, MainDBStorableTable
from db_data_adapter import DBStorableTable, DBStorableRow
import basicclasses





class TableEditorConfig:
    columns: List[Tuple[str, Type, bool, Optional[BTFilterType], Any, Any]]
    table: Optional[DBStorableTable]
    grid_table: Optional[DBStorableTable]
    can_add: bool
    can_edit: bool
    can_edit_multiple: bool
    can_delete: bool
    can_use_history: bool

    convert_row: Optional[Callable[[DBStorableRow], List]]
    dialog_cfg: List[DBInputDialogConfig]

    on_dialog_val_changed: Optional[Callable[[InputOutputPanel, Optional[str], DBStorableRow],None]]
    on_dialog_val_delayed_changed: Optional[Callable[[InputOutputPanel, Optional[str], DBStorableRow],None]]

    before_show_dialog: Optional[Callable[[InputOutputPanel, Optional[DBStorableRow | List[DBStorableRow]], bool, bool],None]]
    after_show_dialog: Optional[Callable[[InputOutputPanel, Optional[DBStorableRow], bool, bool], None]]
    can_add_or_insert_data: Optional[Callable[[DBStorableRow, bool], Tuple[bool, str]]]
    on_control_c: Optional[Callable[[None], None]]
    def __init__(self):
        self.columns = []
        self.table = None
        self.can_add = True
        self.can_edit = True
        self.can_edit_multiple = True
        self.can_delete = True
        self.can_use_history = False
        self.convert_row = None
        self.dialog_cfg = []
        self.on_dialog_val_changed = None
        self.on_dialog_val_delayed_changed = None
        self.can_add_or_insert_data = None
        self.before_show_dialog = None
        self.after_show_dialog = None
        self.on_control_c = None


class TableEditorPanel(BasicPanel, EventSubscriber):
    _logger: Logger
    _dialogs_ini: configparser.ConfigParser
    name: str
    _status_bar: MainWindowStatusBar
    _main_menu: BasicMenu

    _ini_file: Optional[configparser.ConfigParser]

    config: TableEditorConfig
    _update_manager: UpdateManager
    _cur_item: Optional[Union[DBStorableRow, List[DBStorableRow]]]

    _selected_rows: int
    _updated_objects: Dict[EventType, Union[List[DBStorableRow], List[Tuple[DBStorableRow, DBStorableRow]]]]

    grid: BasicGrid
    toolbar: BasicToolBar




    def __init__(self, parent: wx.Window, name: str, logger: Logger, status_bar: MainWindowStatusBar, main_menu: BasicMenu, config: TableEditorConfig, update_manager: UpdateManager):
        EventSubscriber.__init__(self)
        BasicPanel.__init__(self, parent)
        self._logger = logger
        self._dialogs_ini = configparser.ConfigParser()
        self.name = name
        self._status_bar = status_bar
        self._main_menu = main_menu

        self._ini_file = configparser.ConfigParser()
        self.config = config
        self._update_manager = update_manager

        self._cur_item = None
        self._selected_rows = 0
        self._updated_objects = {}


        sizer = wx.BoxSizer(wx.VERTICAL)

        self.toolbar = BasicToolBar(self)
        table = BasicTable()


        self.grid = BasicGrid(self, table)
        self.grid.EnableEditing(False)
        def on_cell_click(_pos: wx.Point, _selected_cells: List[wx.grid.GridCellCoords], _lclick: bool, _rclick: bool, _dclick: bool, _inside_selected: bool, _grid: 'BasicGrid'):
            pass

        def on_col_order_changed():
            pass

        def on_row_order_changed():
            pass


        self.grid.table.on_col_order_changed = on_col_order_changed
        self.grid.table.on_row_order_changed = on_row_order_changed

        table.set_grid(self.grid)
        table.set_columns(config.columns)


        self.grid.on_click_cell = on_cell_click

        self.grid.on_selection_changed = self.on_selection_changed
        self.grid.on_filters_changed = self.on_grid_filters_changed
        self.grid.on_control_c_callback = config.on_control_c

        self.grid.SetSelectionMode(wx.grid.Grid.GridSelectRows)
        if issubclass(type(self._parent),  BasicNotebook):
            name_label = wx.StaticText(self,label=self.name)
            f: wx.Font = name_label.GetFont()
            f.SetPointSize(app_settings.header_size)
            name_label.SetFont(f)
            sizer.Add(name_label, 0, wx.ALL, 5)

        sizer.Add(self.toolbar, 0, wx.EXPAND | wx.ALL, 0)
        sizer.Add(self.grid, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(sizer)
        if self.config.can_add:
            add_command = WxCommand(100, 'Добавить', os.path.join(app_settings.run_path, r'Icons\Common\add.ico'), execute_func=self.wxcommand_add, can_execute_func=self.wxcommand_can_add)
            self.toolbar.add_tool_item(add_command)
        if self.config.can_edit:
            edit_command = WxCommand(101, 'Редактировать', os.path.join(app_settings.run_path, r'Icons\Common\edit.ico'), execute_func=self.wxcommand_edit, can_execute_func=self.wxcommand_can_edit)
            self.toolbar.add_tool_item(edit_command)
        if self.config.can_edit_multiple:
            edit_multiple_command = WxCommand(102, 'Редактировать несколько', os.path.join(app_settings.run_path, r'Icons\Common\table_edit.ico'), execute_func=self.wxcommand_edit_multiple, can_execute_func=self.wxcommand_can_edit_multiple)
            self.toolbar.add_tool_item(edit_multiple_command)
        if self.config.can_delete:
            delete_command = WxCommand(103, 'Удалить', os.path.join(app_settings.run_path, r'Icons\Common\delete.ico'), execute_func=self.wxcommand_delete, can_execute_func=self.wxcommand_can_delete)
            self.toolbar.add_tool_item(delete_command)

        if app_settings.use_history and not self.config.table.instant_save:
            if self.config.can_use_history:
                self.toolbar.add_separator_item()
                undo_command = WxCommand(200, 'Отменить', os.path.join(app_settings.run_path, r'Icons\Common\undo.ico'), execute_func=self.wxcommand_undo, can_execute_func=self.wxcommand_can_undo)
                redo_command = WxCommand(201, 'Вернуть', os.path.join(app_settings.run_path, r'Icons\Common\redo.ico'), execute_func=self.wxcommand_redo, can_execute_func=self.wxcommand_can_redo)
                self.toolbar.add_tool_item(undo_command)
                self.toolbar.add_tool_item(redo_command)


        clear_filers_command = WxCommand(301, 'Очистить фильтры', os.path.join(app_settings.run_path, r'Icons\Common\filter_clear.ico'), execute_func=self.wxcommand_clear_filters, can_execute_func=self.wxcommand_can_clear_filters)
        self.toolbar.add_separator_item()
        self.toolbar.add_tool_item(clear_filers_command)


        show_relations = WxCommand(302, 'Показать зависимости', os.path.join(app_settings.run_path, r'Icons\MainNotebook\relationships.ico'), execute_func=self.wxcommand_show_relations, can_execute_func=self.wxcommand_can_show_relations)
        self.toolbar.add_separator_item()
        self.toolbar.add_tool_check(show_relations)


        self.toolbar.update_wxcommand_states()


    def _load_table(self, ini_file: configparser.ConfigParser):
        rows = []
        for t_row in self.config.grid_table.get_items():
            new_row_data = self.config.convert_row(t_row)
            rows.append((t_row, new_row_data))
        self.grid.table.add_multiple_rows(rows)
        btcfg: BasicTableConfig = BasicTableConfig()

        if ini_file:
            self._ini_file = ini_file
            if self._ini_file.has_section(self.name):
                if self._ini_file.has_option(self.name,'table_config'):
                    btcfg.load_from_str(self._ini_file[self.name]['table_config'], True)
                if self._ini_file.has_option(self.name, 'dialogs_ini'):
                    self._dialogs_ini = config_parser_from_string(self._ini_file[self.name]['dialogs_ini'], True)
        self.grid.table.load_config(btcfg)
        self.toolbar.update_wxcommand_states()


    def init_panel(self, ini_file: configparser.ConfigParser()):
        self.config.grid_table.register_listener(self)
        #self._load_table(ini_file)
        self._update_manager.add_task(self, 0, self._load_table, ini_file)


    def deinit_panel(self):
        self.config.grid_table.unregister_listener(self)
        self.clear_wxcommands()

        # noinspection PyTypeChecker
        if self._ini_file and not self._update_manager.need_update:
            if not self._ini_file.has_section(self.name):
                self._ini_file.add_section(self.name)
            btcfg = self.grid.table.save_config()
            btcfg_ini_str = btcfg.save_to_str(True)
            self._ini_file[self.name]['table_config'] = btcfg_ini_str
            self._ini_file[self.name]['dialogs_ini'] = config_parser_to_string(self._dialogs_ini, True)
        return self._ini_file

    def on_selection_changed(self):
        self._selected_rows = len(self.grid.table.get_selected_objects())
        self._status_bar.show_selected_rows(self._selected_rows)
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()



    def on_grid_filters_changed(self):
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()

    def on_show_panel(self, is_showed: bool):
        if is_showed:
            self._update_manager.set_active_task_parent(self)
            self._status_bar.show_selected_rows(self._selected_rows)
        else:
            self._status_bar.show_selected_rows(0)

    def wxcommand_add(self, _evt: wx.CommandEvent):
        db_input_dialog = DBInputDialog(self, 'Добавить', self._dialogs_ini, self.config.dialog_cfg, wx.Size(300, 200), True, True, self._logger)
        db_input_dialog.create_items()
        db_input_dialog.input_panel.set_focus()
        db_input_dialog.input_panel.property_value_changed_callback = self._on_dialog_val_changed
        #db_input_dialog.load_from_item(new_justification)
        #db_input_dialog.input_panel.property_value_changed_callback = self.input_box_val_changed
        if self.config.before_show_dialog:
            self.config.before_show_dialog(db_input_dialog.input_panel, self.grid.table.get_selected_objects(), True, False)
        db_input_dialog.CenterOnParent()
        db_input_dialog.load_state()
        db_input_dialog.input_panel.set_focus()
        # noinspection PyTypeChecker
        self._on_dialog_val_changed(db_input_dialog.input_panel, None)
        self._cur_item = None


        if db_input_dialog.ShowModal() == wx.ID_OK:
            # noinspection PyTypeChecker
            new_row: DBStorableRow = self.config.table.table_type(self.config.table)
            db_input_dialog.save_to_item(new_row)
            new_row.active = True

            busy = wx.IsBusy()
            if not busy:
                wx.BeginBusyCursor()
            can_add, error_str = self.config.can_add_or_insert_data(new_row, True)
            if not busy:
                wx.EndBusyCursor()

            if can_add:
                busy = wx.IsBusy()
                if not busy:
                    wx.BeginBusyCursor()
                if self.config.after_show_dialog:
                    self.config.after_show_dialog(db_input_dialog.input_panel, new_row, True, False)
                # noinspection PyTypeChecker
                table: MainDBStorableTable = self.config.table
                if not table.undelete_mark(new_row, app_settings.use_history, True):
                    self.config.table.add(new_row,app_settings.use_history,True)
                self.grid.ClearSelection()

                if not busy:
                    wx.EndBusyCursor()
            else:
                message_box(self, 'Ошибка', f'Данные введены неверно.\n{error_str}', wx.ICON_WARNING)

        db_input_dialog.save_state()
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()

    def wxcommand_can_add(self):
        return self.config.can_add

    def wxcommand_edit(self, _evt: wx.CommandEvent):
        db_input_dialog = DBInputDialog(self, 'Редактировать', self._dialogs_ini, self.config.dialog_cfg, wx.Size(300, 200), True, True, self._logger)
        db_input_dialog.create_items()
        db_input_dialog.input_panel.set_focus()
        db_input_dialog.input_panel.property_value_changed_callback = self._on_dialog_val_changed
        items = self.grid.table.get_selected_objects()

        if len(items)==1:
            item: DBStorableRow = items[0]

            db_input_dialog.CenterOnParent()
            db_input_dialog.load_state()
            # noinspection PyTypeChecker

            self._cur_item = item
            self._on_dialog_val_changed(db_input_dialog.input_panel, None)
            if self.config.before_show_dialog:
                self.config.before_show_dialog(db_input_dialog.input_panel, item, False, False)

            db_input_dialog.load_from_item(item)
            db_input_dialog.input_panel.set_focus()
            if db_input_dialog.ShowModal() == wx.ID_OK:
                tmp_item: DBStorableRow = self.config.table.table_type(self.config.table)
                tmp_item.set_guid(item.guid)
                db_input_dialog.save_to_item(tmp_item)
                busy = wx.IsBusy()
                if not busy:
                    wx.BeginBusyCursor()
                can_edit, error_str = self.config.can_add_or_insert_data(tmp_item, False)
                if not busy:
                    wx.EndBusyCursor()
                if can_edit:
                    tmp_item.save(item,False, True)
                    if self.config.after_show_dialog:
                        self.config.after_show_dialog(db_input_dialog.input_panel, item, False, False)
                    self.config.table.write(item, app_settings.use_history, True)
                    self.grid.ClearSelection()

                else:
                    message_box(self, 'Ошибка', f'Данные введены неверно.\n{error_str}', wx.ICON_WARNING)
            db_input_dialog.save_state()

        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()

    def wxcommand_can_edit(self):
        return self.config.can_edit and self._selected_rows==1


    def wxcommand_edit_multiple(self, _evt: wx.CommandEvent):
        db_input_dialog = DBInputDialog(self, 'Редактировать несколько', self._dialogs_ini, self.config.dialog_cfg, wx.Size(300, 200), True, True, self._logger)
        db_input_dialog.create_items()
        db_input_dialog.input_panel.set_focus()
        db_input_dialog.input_panel.property_value_changed_callback = self._on_dialog_val_changed
        items: List[DBStorableRow] = self.grid.table.get_selected_objects()

        if len(items)>0:
            tmp_item: DBStorableRow = items[0].copy()
            for item in items:
                if item == items[0]:
                    continue
                for prop_name, (prop_type, sub_type) in item.get_properties().items():
                    if not hasattr(tmp_item, prop_name) or not hasattr(item, prop_name):
                        continue
                    tmp_item_val = getattr(tmp_item,prop_name)
                    item_val = getattr(item, prop_name)

                    if prop_type in [PropertyType.GENERIC, PropertyType.ENUM, PropertyType.CLASS_INSTANCE]:
                        if tmp_item_val != item_val:
                            delattr(tmp_item, prop_name)
                    elif prop_type == PropertyType.LIST_SPLITTED:
                        set1 = None
                        set2 = None
                        tmp_list_val = getattr(tmp_item, prop_name)
                        if type(tmp_list_val) == list:
                            set1 = set(tmp_list_val)
                        if type(item_val) == list:
                            set2 = set(item_val)
                        if set1 != set2:
                            delattr(tmp_item, prop_name)

            self._cur_item = list(items)
            db_input_dialog.load_from_item(tmp_item)
            if self.config.before_show_dialog:
                self.config.before_show_dialog(db_input_dialog.input_panel, tmp_item, False, True)
            # db_input_dialog.input_panel.property_value_changed_callback = self.input_box_val_changed
            db_input_dialog.CenterOnParent()
            db_input_dialog.load_state()
            db_input_dialog.input_panel.set_focus()

            if db_input_dialog.ShowModal() == wx.ID_OK:
                # noinspection PyTypeChecker
                tmp_item: Union[basicclasses.TrainType, basicclasses.Person] = self.config.table.table_type(self.config.table)
                db_input_dialog.save_to_item(tmp_item)
                progress = ProgressWnd(self.grid, 'Редактирование', wx.Size(300,100))
                notifier = progress.get_notifier()
                notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject(msg=f'Внесение изменений', cur_val=0, max_val=len(items), level=basic.default_notify_level))
                progress.Show()
                for i, item in enumerate(items):
                    tmp_item.save(item, False, True, True)

                    if self.config.after_show_dialog:
                        self.config.after_show_dialog(db_input_dialog.input_panel, item, False, True)
                    self.config.table.write(item, app_settings.use_history, True)
                    notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Внесение изменений', cur_val=i+1, max_val=len(items), level=basic.default_notify_level))
                notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject(msg=f'Внесение изменений завершено',cur_val=len(items), max_val=len(items), level=basic.default_notify_level))
                self.grid.SetFocus()
                progress.Close()
            db_input_dialog.save_state()
        self.grid.SetFocus()
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()

    def wxcommand_can_edit_multiple(self):
        return self.config.can_edit_multiple and self._selected_rows>1


    def wxcommand_delete(self, _evt: wx.CommandEvent):
        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()

        progress = ProgressWnd(self.grid, 'Удаление', wx.Size(300, 100))
        progress.CenterOnParent()
        progress.Show()
        notifier = progress.get_notifier()
        notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject(msg=f'Поиск зависимых объектов'))

        selected_objects = self.grid.table.get_selected_objects()
        selected_count = len(selected_objects)

        items_to_delete = list(selected_objects)
        curr_dataset: MainDatabase = self.config.table.dataset


        full_related_list: List[Tuple[DBStorableRow, DBStorableTable]] = []


        notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject(msg=f'Поиск зависимых объектов', cur_val=0, max_val=len(items_to_delete)))
        for i, item_to_delete in enumerate(items_to_delete):
            curr_dataset.find_related_object_recurse(item_to_delete, full_related_list)
            notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Поиск зависимых объектов', cur_val=i+1, max_val=len(items_to_delete)))

        notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject(msg=f'Поиск зависимых объектов', cur_val=len(items_to_delete), max_val=len(items_to_delete)))
        progress.Close()
        find_related = len(full_related_list)>0
        if not busy:
            wx.EndBusyCursor()
        relations_str = ''

        if find_related:
            relations_str = f'\nзависимые элементы {len(full_related_list)} будут удалены'


        r = wx.MessageDialog(self, f"Удалить {selected_count} {normalize_words('элемент',selected_count)}{relations_str}?", "Подтверждение", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION).ShowModal()
        if r == wx.ID_YES:
            r1 = wx.MessageDialog(self, f"Удалить без возможности восстановления?", "Подтверждение", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION).ShowModal()
            remove_completly = False
            if r1 == wx.ID_YES:
                remove_completly = True

            items_to_delete = list(self.grid.table.get_selected_objects())
            self.grid.ClearSelection()
            freezed = self.grid.IsFrozen()
            if not freezed:
                self.grid.Freeze()
            progress = ProgressWnd(self, 'Удаление', wx.Size(300, 100))
            progress.CenterOnParent()
            progress.Show()
            notifier = progress.get_notifier()
            notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject(msg=f'Удаление', cur_val=0, max_val=len(items_to_delete)+len(full_related_list)))
            for i, obj in enumerate(items_to_delete):
                # noinspection PyTypeChecker
                table: MainDBStorableTable = self.config.table
                if not remove_completly:
                    table.delete_mark(obj, app_settings.use_history, True)
                else:
                    table.delete(obj, app_settings.use_history, True)
                notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Удаление', cur_val=i+1, max_val=len(items_to_delete)+len(full_related_list)))
            d_table: MainDBStorableTable
            for i, (d_obj, d_table) in enumerate(full_related_list):
                if not remove_completly:
                    d_table.delete_mark(d_obj, app_settings.use_history, True)
                else:
                    d_table.delete(d_obj, app_settings.use_history, True)

                notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Удаление', cur_val=len(items_to_delete)+i+1, max_val=len(items_to_delete)+len(full_related_list)))
            notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Удаление', cur_val=len(items_to_delete) + len(full_related_list), max_val=len(items_to_delete) + len(full_related_list)))

            progress.Close()
            if not freezed:
                self.grid.Thaw()
        self.grid.SetFocus()
        self.grid.update_col_header()
        self.grid.update_row_header()
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()

    def wxcommand_can_delete(self):
        return self.config.can_delete and self._selected_rows>0


    def wxcommand_clear_filters(self, _evt: wx.CommandEvent):
        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()
        frozen = self.grid.IsFrozen()
        if not frozen:
            self.grid.Freeze()
        for col in range(self.grid.GetNumberCols()):
            self.grid.table.get_column_info(col).filter_value = None
        self.grid.table.update_filter()
        self.grid.update_row_sizes()
        if not frozen:
            self.grid.Thaw()
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()
        if not busy:
            wx.EndBusyCursor()

    def wxcommand_can_clear_filters(self):
        is_filtered = False
        for col in range(self.grid.table.GetNumberCols()):
            if self.grid.table.get_column_info(col).filter_value is not None:
                is_filtered = True
                break
        return is_filtered

    def wxcommand_undo(self, _evt: wx.CommandEvent):
        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()
        self.config.table.history_undo()
        self.grid.table.update_sort()
        self.grid.table.update_filter()
        self.grid.update_row_sizes()
        if not busy:
            wx.EndBusyCursor()
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()

    def wxcommand_can_undo(self):
        return self.config.table.history_can_undo()

    def wxcommand_redo(self, _evt: wx.CommandEvent):
        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()
        self.grid.table.update_sort()
        self.config.table.history_redo()
        self.grid.table.update_sort()
        self.grid.table.update_filter()
        self.grid.update_row_sizes()
        if not busy:
            wx.EndBusyCursor()

        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()

    def wxcommand_can_redo(self):
        return self.config.table.history_can_redo()


    def wxcommand_can_show_relations(self):
        return self.grid.table.GetNumberRows()>0


    def wxcommand_show_relations(self, _evt: wx.CommandEvent):
        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()
        checked = self.toolbar.get_tool_state_by_iid(302)
        dataset: MainDatabase = self.config.table.dataset

        if checked:
            for i in range(self.grid.table.get_total_rows_count()):
                found_obj = dataset.find_related_objects(self.grid.table.get_object(i,False))
                if found_obj:
                    self.grid.table.get_row_info(i,False).color = wx.ColourDatabase().FindName("YELLOW")
        else:
            for i in range(self.grid.table.get_total_rows_count()):
                self.grid.table.get_row_info(i,True).color = None
        self.grid.update_view()
        self.grid.Refresh()
        if not busy:
            wx.EndBusyCursor()

    @gui_widgets.WxEvents.debounce(0.1, False)
    def on_multiple_update(self):
        tmp_dict = dict(self._updated_objects)
        for event_type, rows in tmp_dict.items():
            if event_type == EventType.ITEM_ADDED:
                row: DBStorableRow
                if len(rows)>1:
                    new_rows = []
                    for row in rows:
                        new_rows.append((row, self.config.convert_row(row)))
                    self._update_manager.add_task(self, 0, self.grid.table.add_multiple_rows, new_rows)
                    #self.grid.table.add_multiple_rows(new_rows)
                elif len(rows)==1:
                    rows: List[DBStorableRow]
                    self._update_manager.add_task(self, 0, self.grid.table.add_row, rows[0], self.config.convert_row(rows[0]))
                    self._update_manager.add_task(self, 0, self.grid.table.goto_object, rows[0], self.grid.GetGridCursorCol())

                    #self.grid.table.add_row(rows[0], self.config.convert_row(rows[0]))
                    #self.grid.table.goto_object(rows[0], self.grid.GetGridCursorCol())
                #self._logger.info(f'add item {}')
            elif event_type in [EventType.ITEM_CHANGED, EventType.ITEM_NEED_UPDATE]:
                if len(rows) > 1:
                    new_rows = []
                    for row in rows:
                        row: Tuple[DBStorableRow, DBStorableRow]
                        new_rows.append((row[1], self.config.convert_row(row[1])))
                    self._update_manager.add_task(self, 0, self.grid.table.write_multiple_rows, new_rows)

                    # self.grid.table.write_multiple_rows(new_rows)
                elif len(rows) == 1:

                    rows: List[Tuple[DBStorableRow, DBStorableRow]]
                    self._update_manager.add_task(self, 0, self.grid.table.write_row, rows[0][1], self.config.convert_row(rows[0][1]))
                    self._update_manager.add_task(self, 0, self.grid.table.goto_object, rows[0][1], self.grid.GetGridCursorCol())

                    # self.grid.table.write_row(rows[0][1], self.config.convert_row(rows[0][1]))
                    #self.grid.table.goto_object(rows[0][1], self.grid.GetGridCursorCol())

            elif event_type == EventType.ITEM_DELETED:
                if len(rows) > 1:
                    #self.grid.table.delete_multiple_rows(rows)
                    del_rows = []
                    del_rows.extend(rows)
                    self._update_manager.add_task(self, 0, self.grid.table.delete_multiple_rows, del_rows)
                elif len(rows) == 1:
                    #self.grid.table.delete_row(rows[0])
                    self._update_manager.add_task(self, 0, self.grid.table.delete_row, rows[0])
            self._updated_objects[event_type].clear()

        self._update_manager.add_task(self, 0, self.toolbar.update_wxcommand_states)
        #self.toolbar.update_wxcommand_states()
        self._update_manager.add_task(self, 0, self._main_menu.update_wxcommand_states)
        #self._main_menu.update_wxcommand_states()
        self._update_manager.add_task(self, 0, self.update_wxcommands)
        #self.update_wxcommands()



    @gui_widgets.WxEvents.debounce(0.8,False)
    def _execute_on_dialog_val_changed(self, io_panel: InputOutputPanel, name: str):
        if self.config.on_dialog_val_delayed_changed:
            self.config.on_dialog_val_delayed_changed(io_panel, name, self._cur_item)

    def _on_dialog_val_changed(self, io_panel: InputOutputPanel, name: Optional[str]):
        if self.config.on_dialog_val_changed:
            self.config.on_dialog_val_changed(io_panel,name, self._cur_item)
        self._execute_on_dialog_val_changed(io_panel, name)

    def on_notify(self, event_type: EventType, event_object: EventObject):

        if event_type not in self._updated_objects.keys():
            self._updated_objects[event_type] = []
        obj = event_object.obj
        if type(obj) == DBStorableTable:
            if event_type == EventType.HISTORY_CHANGED:
                self.toolbar.update_wxcommand_states()
                self._main_menu.update_wxcommand_states()
                self.update_wxcommands()
        else:
            if event_type == EventType.ITEM_ADDED:
                new_obj: DBStorableRow = event_object.obj
                self._updated_objects[event_type].append(new_obj)
                self.on_multiple_update()
            elif event_type in [EventType.ITEM_CHANGED, EventType.ITEM_NEED_UPDATE]:
                new_obj: DBStorableRow = event_object.obj
                old_obj: DBStorableRow = event_object.old_obj
                # noinspection PyTypeChecker
                self._updated_objects[event_type].append((old_obj, new_obj))
                self.on_multiple_update()
            elif event_type == EventType.ITEM_DELETED:
                new_obj: DBStorableRow = event_object.obj
                self._updated_objects[event_type].append(new_obj)
                self.on_multiple_update()

