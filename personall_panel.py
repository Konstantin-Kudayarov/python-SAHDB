
import shutil
import tempfile
import uuid
from typing import List, Tuple, Any, Optional

import wx
import wx.grid
import os

import basic
import basicclasses
from grid_panel import TableEditorPanel
from gui_widgets import ( InputOutputPanel, message_box, WxCommand, ImageList, BasicFileSelect,
                          DBInputDialog, InputBox)
from gui_widgets_grid import BasicGrid

from db_data_adapter import DBStorableRow
from warining_window import set_io_panel_warnings

from basicclasses import MainDatabase, app_settings




class PersonallDocPanel(TableEditorPanel):
    dataset: MainDatabase
    _tmp_filenames: List[str]
    _cur_item: Any
    info_wnd: Optional[InputBox]
    def __init__(self, parent, name, logger, status_bar, main_menu, config, update_manager):
        TableEditorPanel.__init__(self, parent, name, logger, status_bar, main_menu, config, update_manager)
        self.info_wnd = None
        add_view_doc_command = WxCommand(502, 'Просмотр документа', os.path.join(app_settings.run_path, r'Icons\Common\doc_view.ico'), execute_func=self.wxcommand_view_doc, can_execute_func=self.wxcommand_can_view_doc)
        self.toolbar.add_tool_item(add_view_doc_command)

        show_info_command = WxCommand(504, 'Информация', os.path.join(app_settings.run_path, r'Icons\Common\blogs.ico'), execute_func=self.wxcommand_show_info, can_execute_func=self.wxcommand_can_show_info)
        self.toolbar.add_tool_item(show_info_command)

        self.toolbar.update_wxcommand_states()
        self.dataset = config.grid_table.dataset
        self.grid.can_drop_to_cell = self.can_drop_to_cell
        self.grid.can_drop_to_cell_data = self.can_drop_to_cell_data
        self.grid.drop_to_cell_execute = self.drop_to_cell_execute
        self.grid.on_selection_changed = self.on_selection_changed

        def on_col_order_changed():
            pass

        def on_row_order_changed():
            pass

        def on_filters_changed():
            self.toolbar.update_wxcommand_states()
            self._main_menu.update_wxcommand_states()

        self.grid.table.on_col_order_changed = on_col_order_changed
        self.grid.table.on_row_order_changed = on_row_order_changed
        self.grid.on_filters_changed = on_filters_changed


        def on_click_cell(_pos: wx.Point, _selected_cells: List[wx.grid.GridCellCoords], _lclick: bool, _rclick: bool, _dclick: bool, _inside_selected: bool, _grid: BasicGrid):
            pass
        self.grid.on_click_cell = on_click_cell

        self._tmp_filenames = []
        self._cur_item = None

    def can_drop_to_cell(self, _coords: wx.grid.GridCellCoords):
        if self.grid.table.GetNumberRows()>0:
            return True
        return False


    def can_drop_to_cell_data(self, _coords: wx.grid.GridCellCoords, data_object: Any):
        #sel_items: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        if self.dataset.connected:
            if type(data_object) == list:
                if len(data_object)==1:
                    if os.path.exists(data_object[0]):
                        return True
        return False

    def drop_to_cell_execute(self, _coords: wx.grid.GridCellCoords, data_object: Any, def_result: int):
        sel_items: List[basicclasses.PersonallDocument] = self.grid.table.get_selected_objects()
        if len(sel_items)!=1:
            return
        item = sel_items[0]
        filename = data_object[0]

        new_file_name = os.path.normpath(os.path.join(tempfile.gettempdir(), str(uuid.uuid4()) + os.path.splitext(filename)[1]))
        try:
            shutil.copy(filename, new_file_name)
            self._tmp_filenames.append(new_file_name)
        except Exception as ex:
            self._logger.error(f'{self} ошибка копирования {filename} в {new_file_name} {ex}')

        wx.LaunchDefaultApplication(new_file_name)
        self.add_personall_doc_dialog(item.person, item.doc_type, filename)
        wx.CallAfter(self.GetTopLevelParent().Raise)
        if def_result == wx.DragMove:
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except Exception as ex:
                    self._logger.error(f'{self} ошибка удаления {filename} {ex}')


    def deinit_panel(self):
        for f in self._tmp_filenames:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception as ex:
                    self._logger.error(f'{self} ошибка удаления {f} {ex}')
        return TableEditorPanel.deinit_panel(self)

    def wxcommand_can_view_doc(self):
        sel_objects: List[basicclasses.PersonallDocument] = self.grid.table.get_selected_objects()
        if len(sel_objects) > 0:
            p_doc: basicclasses.PersonallDocument = sel_objects[0]
            if p_doc.name_path:
                dataset: MainDatabase = p_doc.table.dataset
                file_name = dataset.get_doc_file_name(p_doc)
                if os.path.exists(file_name):
                    return True
        return False

    def wxcommand_view_doc(self, _evt: wx.CommandEvent):
        sel_objects: List[basicclasses.PersonallDocument] = self.grid.table.get_selected_objects()
        if len(sel_objects) > 0:
            p_doc: basicclasses.PersonallDocument = sel_objects[0]
            if p_doc.name_path:
                dataset: MainDatabase = p_doc.table.dataset
                file_name = dataset.get_doc_file_name(p_doc)
                if os.path.exists(file_name):
                    wx.LaunchDefaultApplication(file_name)


    def add_personall_doc_dialog(self, person: basicclasses.Person, doc_type: basicclasses.PersonalDocType, filename: Optional[str]):
        db_input_dialog = DBInputDialog(self, 'Добавить', self._dialogs_ini, self.config.dialog_cfg, wx.Size(300, 200), True, True, self._logger)
        db_input_dialog.create_items()
        db_input_dialog.input_panel.set_focus()
        db_input_dialog.input_panel.add_property('file', 'Файл', BasicFileSelect, False)
        db_input_dialog.input_panel.set_property_size('file', -1, -1)
        db_input_dialog.input_panel.property_value_changed_callback = self.dialog_val_changed
        db_input_dialog.CenterOnParent()

        if filename:
            db_input_dialog.input_panel.set_property('file',filename, None)

        if person:
            db_input_dialog.input_panel.set_property('person', person, None)
        if doc_type:
            db_input_dialog.input_panel.set_property('doc_type', doc_type, None)

        if db_input_dialog.ShowModal() == wx.ID_OK:
            # noinspection PyTypeChecker
            new_row: basicclasses.PersonallDocument = self.config.table.table_type(self.config.table)
            db_input_dialog.save_to_item(new_row)
            new_row.active = True

            busy = wx.IsBusy()
            if not busy:
                wx.BeginBusyCursor()
            can_add, error_str = self.dialog_can_add_or_insert(new_row)
            if not busy:
                wx.EndBusyCursor()

            if can_add:
                busy = wx.IsBusy()
                if not busy:
                    wx.BeginBusyCursor()
                new_row.name_path = ''
                new_row.doc_file_hash = None
                new_row.doc_file_exists = False
                name_path, doc_hash, doc_exists = self._save_file(db_input_dialog.input_panel, new_row)
                new_row.name_path = name_path
                new_row.doc_file_hash = doc_hash
                new_row.doc_file_exists = doc_exists
                self.config.table.add(new_row,app_settings.use_history,True)
                self.grid.ClearSelection()

                if not busy:
                    wx.EndBusyCursor()
            else:
                message_box(self, 'Ошибка', f'Данные введены неверно.\n{error_str}', wx.ICON_WARNING)

        db_input_dialog.save_state()
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()


    @staticmethod
    def _save_file(io_panel: InputOutputPanel, doc: basicclasses.PersonallDocument):
        new_doc_path = io_panel.get_property('file', False)
        dataset: MainDatabase = doc.table.dataset
        if new_doc_path and os.path.exists(new_doc_path) and os.path.isfile(new_doc_path):
            src_ext = os.path.splitext(new_doc_path)[1]
            old_doc_path = None
            old_hash = None
            if doc.name_path:
                old_doc_path = dataset.get_doc_file_name(doc)
                if old_doc_path and os.path.exists(old_doc_path):
                    old_hash = basic.hash_file(old_doc_path, 512)
            name_path = dataset.generate_node_path(doc) + src_ext
            doc_hash = basic.hash_file(new_doc_path, 512)
            doc_exists = True
            dst_doc_path = os.path.join(dataset.workspace_settings.db_files_path, name_path)

            if old_doc_path and old_doc_path != new_doc_path and os.path.exists(old_doc_path):
                dataset.move_file(old_doc_path, app_settings.archive_folder,True)

            if old_hash != doc_hash or new_doc_path != dst_doc_path:
                dataset.copy_file(new_doc_path,dst_doc_path)


        else:
            name_path = dataset.generate_node_path(doc)
            doc_hash = None
            doc_exists = False

        return name_path, doc_hash, doc_exists



    def dialog_val_changed(self, io_panel: InputOutputPanel, _name: str):
        required_fields = {'person': 'личность',
                           'doc_type': 'вид документа'
                           }
        warning_list = []
        for n, descr in required_fields.items():
            val = io_panel.get_property(n, False)
            if not val:
                warning_list.append(required_fields[n])

        person = io_panel.get_property('person', False)
        doc_type = io_panel.get_property('doc_type', False)
        doc_name = io_panel.get_property('doc_name', False)
        item: basicclasses.PersonallDocument

        info_items: List[Tuple[ImageList.BuiltInImage, str]] = []
        for item in self.dataset.get_table(basicclasses.PersonallDocument).get_items():
            if self._cur_item is not None:
                if self._cur_item == item:
                    continue
            if item.person == person and item.doc_type == doc_type and item.doc_name == doc_name:
                info_msg = f'Для элемента {item.person.full_name} {item.doc_type.full_name} {item.doc_name} найден такой-же элемент:{item.guid}'
                info_items.append((ImageList.BuiltInImage.WARNING, info_msg))
        set_io_panel_warnings(self._logger, io_panel, info_items, warning_list)



    def dialog_can_add_or_insert(self, personal_doc: basicclasses.PersonallDocument) -> Tuple[bool, str]:
        item: basicclasses.PersonallDocument
        for item in self.dataset.get_table(basicclasses.PersonallDocument).get_items():
            if item.guid == personal_doc.guid:
                continue
            if item.person == personal_doc.person and item.doc_type == personal_doc.doc_type and item.doc_name == personal_doc.doc_name:
                return False, 'Документ с такими параметрами уже существует'
        return True, ''



    def wxcommand_edit(self, _evt: wx.CommandEvent):
        db_input_dialog = DBInputDialog(self, 'Редактировать', self._dialogs_ini, self.config.dialog_cfg, wx.Size(300, 200), True, True, self._logger)
        db_input_dialog.create_items()
        db_input_dialog.input_panel.set_focus()
        db_input_dialog.input_panel.property_value_changed_callback = self._on_dialog_val_changed
        items = self.grid.table.get_selected_objects()

        if len(items)==1:
            item: DBStorableRow = items[0]
            db_input_dialog.load_from_item(item)
            db_input_dialog.CenterOnParent()
            db_input_dialog.load_state()
            # noinspection PyTypeChecker
            self._cur_item = item
            self._on_dialog_val_changed(db_input_dialog.input_panel, None)

            db_input_dialog.input_panel.add_property('file', 'Файл', BasicFileSelect, False)
            db_input_dialog.input_panel.set_property_size('file', -1, -1)
            db_input_dialog.input_panel.enable_property('person', False)
            db_input_dialog.input_panel.enable_property('doc_type', False)

            if item:
                if item.name_path:
                    filename = self.dataset.get_doc_file_name(item)
                    if os.path.exists(filename):
                        db_input_dialog.input_panel.set_property('file', filename, None)

            db_input_dialog.input_panel.set_focus()
            db_input_dialog.CenterOnParent()
            if db_input_dialog.ShowModal() == wx.ID_OK:
                # noinspection PyTypeChecker
                tmp_item: basicclasses.PersonallDocument = self.config.table.table_type(self.config.table)
                tmp_item.set_guid(item.guid)
                db_input_dialog.save_to_item(tmp_item)
                busy = wx.IsBusy()
                if not busy:
                    wx.BeginBusyCursor()
                can_edit, error_str = self.dialog_can_add_or_insert(tmp_item)
                if not busy:
                    wx.EndBusyCursor()
                item: basicclasses.PersonallDocument
                if can_edit:
                    tmp_item.save(item,False, True)
                    name_path, doc_hash, doc_exists = self._save_file(db_input_dialog.input_panel, item)
                    item.name_path = name_path
                    item.doc_file_hash = doc_hash
                    item.doc_file_exists = doc_exists
                    self.config.table.write(item, app_settings.use_history, True)
                    self.grid.ClearSelection()

                else:
                    message_box(self, 'Ошибка', f'Данные введены неверно.\n{error_str}', wx.ICON_WARNING)
            db_input_dialog.save_state()
            self._cur_item = None
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()


    def wxcommand_add(self, _evt: wx.CommandEvent):
        selected_documents: List[basicclasses.PersonallDocument] = self.grid.table.get_selected_objects()
        person = None
        doc_type = None
        if selected_documents:
            p_doc: basicclasses.PersonallDocument = selected_documents[0]
            person = p_doc.person
            doc_type = p_doc.doc_type
        self.add_personall_doc_dialog(person, doc_type, None)

    def wxcommand_show_info(self, evt: wx.CommandEvent):
        act_trainings: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        if len(act_trainings) == 0:
            return

        def close():
            self.info_wnd = None

        if self.info_wnd is None:
            self.info_wnd = InputBox(self, 'Информация', None, self._dialogs_ini, scrollable=False, sizeable=True, show_buttons=False)
            self.info_wnd.input_panel.add_property('info', 'Информация:', wx.StaticText, False)
            self.info_wnd.Show()
            self.info_wnd.on_close_dialog = close
        else:
            self.info_wnd.Raise()
        self.update_info_wnd()

    def on_selection_changed(self):
        TableEditorPanel.on_selection_changed(self)
        self.update_info_wnd()

    def update_info_wnd(self):
        p_docs: List[basicclasses.PersonallDocument] = self.grid.table.get_selected_objects()
        if self.info_wnd:
            info_str = ''
            for p_doc in p_docs:

                info_str += f'{p_doc.doc_type.full_name}: {p_doc.person.full_name_with_date}\n'
                info_str += f'{p_doc.doc_name+"\n" if p_doc.doc_name else ""}'
                info_str += f'{p_doc.doc_file_hash}\n'
            self.info_wnd.input_panel.set_property('info', info_str, None)

    def wxcommand_can_show_info(self):
        return len(self.grid.get_selected_grid_rows())>0