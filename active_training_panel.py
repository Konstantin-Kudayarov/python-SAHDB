
import datetime
import shutil
import tempfile
import uuid
from typing import List, Any, Optional, Tuple

import wx
import wx.grid
import os

import basicclasses
from grid_panel import TableEditorPanel
from gui_widgets import ( message_box, WxCommand,
                         InputBox, BasicCheckListWithFilter,ProgressWnd)
from gui_widgets_grid import BasicGrid
from action_scripts import ActionScripts
from basic import EventType, EventProgressObject, default_notify_level

from basic import normalize_words
from basicclasses import MainDatabase, app_settings


class ActiveTrainingPanel(TableEditorPanel):
    dataset: MainDatabase
    _tmp_filenames: List[str]
    action_scripts: ActionScripts
    export_doc_files_wnd: Optional[InputBox]
    info_wnd: Optional[InputBox]
    def __init__(self, parent, name, logger, status_bar, main_menu, config, update_manager, action_scripts):
        TableEditorPanel.__init__(self, parent, name, logger, status_bar, main_menu, config, update_manager)
        self.action_scripts = action_scripts
        self.info_wnd = None
        add_command = WxCommand(501, 'Создать заявки', os.path.join(app_settings.run_path, r'Icons\MainNotebook\tasks_add.ico'), execute_func=self.wxcommand_add_tasks, can_execute_func=self.wxcommand_can_add_tasks)
        self.toolbar.add_tool_item(add_command)
        add_view_doc_command = WxCommand(502, 'Просмотр документа', os.path.join(app_settings.run_path, r'Icons\Common\doc_view.ico'), execute_func=self.wxcommand_view_doc, can_execute_func=self.wxcommand_can_view_doc)
        self.toolbar.add_tool_item(add_view_doc_command)
        add_view_doc_command = WxCommand(503, 'Экспорт документа', os.path.join(app_settings.run_path, r'Icons\Common\document_export.ico'), execute_func=self.wxcommand_export_doc_files, can_execute_func=self.wxcommand_can_view_doc)
        self.toolbar.add_tool_item(add_view_doc_command)

        show_info_command = WxCommand(504, 'Информация', os.path.join(app_settings.run_path, r'Icons\Common\blogs.ico'), execute_func=self.wxcommand_show_info, can_execute_func=self.wxcommand_can_show_info)
        self.toolbar.add_tool_item(show_info_command)

        self.toolbar.update_wxcommand_states()
        self.dataset = config.grid_table.dataset
        self.export_doc_files_wnd = None
        self.grid.can_drop_to_cell = self.can_drop_to_cell
        self.grid.can_drop_to_cell_data = self.can_drop_to_cell_data
        self.grid.drop_to_cell_execute = self.drop_to_cell_execute

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
        self.grid.on_selection_changed = self.on_selection_changed

        def on_click_cell(_pos: wx.Point, _selected_cells: List[wx.grid.GridCellCoords], _lclick: bool, _rclick: bool, _dclick: bool, _inside_selected: bool, _grid: BasicGrid):
            pass

        self.grid.on_click_cell = on_click_cell
        self._tmp_filenames = []




    def wxcommand_add(self, _evt: wx.CommandEvent):
        selected_act_training: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        self.action_scripts.add_training_with_dialog(self, self._dialogs_ini, selected_act_training, self._logger, None)
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()
        self.grid.SetFocus()



    def wxcommand_edit(self, _evt: wx.CommandEvent):
        selected_act_training: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        self.action_scripts.edit_training(self, self._dialogs_ini, selected_act_training, self._logger)
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()
        self.grid.SetFocus()



    def wxcommand_can_edit(self):
        selected_act_training: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        for sel_obj in selected_act_training:
            if len(sel_obj.trainings)>0:
                return True
        return False

    def wxcommand_delete(self, _evt: wx.CommandEvent):
        items: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()

        self.action_scripts.delete_trainings(self, self._dialogs_ini, items, self._logger)
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()
        self.grid.SetFocus()






    def wxcommand_can_delete(self):
        items: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        for item in items:
            if item.trainings:
                return True
        return False

    def wxcommand_add_tasks(self, _evt: wx.CommandEvent):
        items: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()

        if len(items) > 0:
            busy = wx.IsBusy()
            if not busy:
                wx.BeginBusyCursor()

            dataset: basicclasses.MainDatabase = items[0].table.dataset
            selected_train_request = []
            avail_train_request_values = []

            table = dataset.get_table(basicclasses.TrainingRequest)

            required_tr_request = []
            for item in items:
                for doc_type in item.train_type.doc_types:
                    new_tr_request = basicclasses.TrainingRequest(table)
                    new_tr_request.new_guid()
                    new_tr_request.employee = item.employee
                    new_tr_request.train_type = item.train_type
                    new_tr_request.doc_type = doc_type
                    new_tr_request.complete_date = None
                    new_tr_request.active = True
                    name = f'{item.employee.person.full_name_with_date} {item.train_type.short_name} {doc_type.full_name}'
                    avail_train_request_values.append((name, new_tr_request))
                    if item.required:
                        required_tr_request.append(new_tr_request)



            for tr_str, tr in avail_train_request_values:
                seek_tuple = tr.employee, tr.train_type, tr.doc_type
                need_add = True
                if tr not in required_tr_request:
                    need_add = False
                if seek_tuple in dataset.lookup_train_requests.keys():
                    for t in dataset.lookup_train_requests[seek_tuple]:
                        if not t.completed:
                            need_add = False
                if need_add:
                    if tr not in selected_train_request:
                        selected_train_request.append(tr)


            if not busy:
                wx.EndBusyCursor()

            if len(selected_train_request) == 0:
                message_box(self, 'Предупреждение', 'Для выбранных объектов нет необходимости добавлять заявки', wx.ICON_INFORMATION)

            input_box = InputBox(self, 'Добавление заявок', None, None, size=wx.Size(500, 300), scrollable=False, sizeable=False, ignore_enter_key=False)
            input_box.input_panel.add_property('selected_items', '', BasicCheckListWithFilter, False)
            input_box.input_panel.set_property_size('selected_items', 600, 250)
            input_box.input_panel.set_property('selected_items', selected_train_request, avail_train_request_values)
            input_box.input_panel.add_property('request_date', '', datetime.date, False)
            input_box.input_panel.set_property('request_date', datetime.date.today(), None)

            input_box.input_panel.update_view()
            input_box.Fit()
            input_box.Layout()
            input_box.CenterOnParent()
            input_box.input_panel.set_focus()
            result = input_box.ShowModal()

            if result == wx.ID_OK:
                selected_tr_requests: List[basicclasses.TrainingRequest] = input_box.input_panel.get_property('selected_items', False)
                busy = wx.IsBusy()
                if not busy:
                    wx.BeginBusyCursor()

                for tr_request in selected_tr_requests:
                    tr_request.request_date = input_box.input_panel.get_property('request_date', False)
                    table.add(tr_request, app_settings.use_history, True)

                if not busy:
                    wx.EndBusyCursor()
                message_info = f'Добавлено: {len(selected_tr_requests)} {normalize_words('объект', len(selected_tr_requests))}'
                message_box(self, 'Информация', message_info, wx.ICON_INFORMATION)

        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()

    def wxcommand_can_add_tasks(self):
        selected_items: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        if len(selected_items)>0:
            return True
        return False

    def wxcommand_view_doc(self, _evt: wx.CommandEvent):
        sel_objects: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        if len(sel_objects) > 0:
            p_doc: basicclasses.ActiveTraining = sel_objects[0]
            if p_doc.trainings:
                p_doc: basicclasses.ActiveTraining = sel_objects[0]
                if p_doc.trainings:
                    dataset: MainDatabase = p_doc.table.dataset
                    for tr in p_doc.trainings:
                        if tr.name_path:
                            file_name = dataset.get_training_file_name(tr)
                            if os.path.exists(file_name):
                                wx.LaunchDefaultApplication(file_name)

    def wxcommand_can_view_doc(self):
        sel_objects: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        if len(sel_objects) > 0:
            p_doc: basicclasses.ActiveTraining = sel_objects[0]
            if p_doc.trainings:
                dataset: MainDatabase = p_doc.table.dataset
                for tr in p_doc.trainings:
                    if tr.name_path:
                        file_name = dataset.get_training_file_name(tr)
                        if os.path.exists(file_name):
                            return True
        return False




    def wxcommand_export_doc_files_ok_button_click(self):
        file_dialog = wx.DirDialog(self, 'Выбрать папку', defaultPath=self.dataset.workspace_settings.export_doc_path)
        r = file_dialog.ShowModal()
        if r != wx.ID_OK:
            return
        save_path = file_dialog.GetPath()
        if not os.path.exists(save_path):
            message_box(self, 'Ошибка', 'Директория не выбрана', wx.ICON_WARNING)
            return

        self.dataset.workspace_settings.export_doc_path = save_path
        selected_tranings: List[basicclasses.Training] = self.export_doc_files_wnd.input_panel.get_property('items',False)

        doc_hashes = []
        for training in selected_tranings:
            if training.doc_file_hash and training.doc_file_exists:
                if training.doc_file_hash not in doc_hashes:
                    doc_hashes.append(training.doc_file_hash)

        file_names = {}
        for doc_hash in doc_hashes:
            if doc_hash in self.dataset.lookup_file_hashes.keys():
                tmp_training_list = list(self.dataset.lookup_file_hashes[doc_hash])
                tmp_training_list.sort(key=lambda t: (t.doc_type.short_name, t.train_type.short_name, t.employee.person.full_name))
                doc_type = None
                tt_list: List[basicclasses.TrainType] = []
                emp_list: List[basicclasses.Employee] = []
                last_item = None
                for t in tmp_training_list:
                    if last_item is None:
                        last_item = t
                    if doc_type is None:
                        doc_type = t.doc_type
                    if t in selected_tranings:
                        if t.train_type not in tt_list:
                            tt_list.append(t.train_type)
                        if t.employee not in emp_list:
                            emp_list.append(t.employee)
                    if doc_type!= t.doc_type or t == tmp_training_list[len(tmp_training_list)-1]:
                        file_name_template = f'{t.doc_type.full_name} {','.join(tt.short_name for tt in tt_list)} {','.join(emp.person.last_name+emp.person.first_name[0] for emp in emp_list)}'
                        file_name_template = file_name_template[:100]
                        original_name = self.dataset.get_training_file_name(last_item)
                        file_names[original_name] = file_name_template
                    last_item = t

        progress = ProgressWnd(self.GetTopLevelParent(), 'Экспорт файлов', wx.Size(300, 100))
        notifier = progress.get_notifier()
        notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Экспорт файлов', level=default_notify_level))
        progress.CenterOnParent()
        progress.Show()
        i_max = len(file_names)
        error_list = []
        for i, (src_file_name, dst_file_name) in enumerate(file_names.items()):
            notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject('Экспорт файлов', cur_val=i + 1, max_val=i_max, level=default_notify_level))

            if os.path.exists(src_file_name):
                j = 1
                dst_path_name = os.path.join(save_path, dst_file_name)+os.path.splitext(src_file_name)[1]
                while os.path.exists(dst_path_name):
                    dst_path_name = os.path.join(save_path, dst_file_name+f'_другой({j})') + os.path.splitext(src_file_name)[1]
                    j += 1
                try:
                    shutil.copy(src_file_name, dst_path_name)
                except Exception as ex:
                    error_list.append(f'Ошибка копирования {os.path.split(src_file_name)[1]} {os.path.split(dst_path_name)[1]} {ex}')

        self.export_doc_files_wnd.Close()
        self.export_doc_files_wnd = None
        notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Экспорт файлов завершен', level=default_notify_level))
        progress.Close()
        if error_list:
            message_box(self, 'Ошибка', f'{'\n'.join(error_list)}', wx.ICON_ERROR)



    def wxcommand_export_doc_files_close(self):
        self.export_doc_files_wnd = None

    def wxcommand_export_doc_files(self, _evt: wx.CommandEvent):
        if self.export_doc_files_wnd is None:
            self.export_doc_files_wnd = InputBox(self, 'Экспорт файлов', None, self._dialogs_ini,sizeable=True)
            self.export_doc_files_wnd.input_panel.add_property('items','',BasicCheckListWithFilter, False)
            self.export_doc_files_wnd.on_ok_button = self.wxcommand_export_doc_files_ok_button_click
            self.export_doc_files_wnd.on_close_dialog = self.wxcommand_export_doc_files_close
            self.export_doc_files_wnd.Show()
        sel_objects: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        if len(sel_objects) > 0:
            panel_avail_objects: List[basicclasses.Training] = self.export_doc_files_wnd.input_panel.get_property('items',True) or []
            panel_selected_objects: List[basicclasses.Training] = self.export_doc_files_wnd.input_panel.get_property('items',False) or []

            for act_tr in sel_objects:
                for tr in act_tr.trainings:
                    file_name = self.dataset.get_training_file_name(tr)
                    if os.path.exists(file_name):
                        if tr not in panel_avail_objects:
                            panel_avail_objects.append(tr)
                            panel_selected_objects.append(tr)
            panel_values: List[Tuple[str, basicclasses.Training]] = []
            for pt in panel_avail_objects:
                panel_values.append((f'{pt.employee.person.full_name_with_date} {pt.training_name}', pt))
            self.export_doc_files_wnd.input_panel.set_property('items', panel_selected_objects, panel_values)




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
        sel_items: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        if len(sel_items)!=1:
            return
        filename = data_object[0]

        new_file_name = os.path.normpath(os.path.join(tempfile.gettempdir(), str(uuid.uuid4()) + os.path.splitext(filename)[1]))
        try:
            shutil.copy(filename, new_file_name)
            self._tmp_filenames.append(new_file_name)
        except Exception as ex:
            self._logger.error(f'{self} ошибка копирования {filename} в {new_file_name} {ex}')
        wx.LaunchDefaultApplication(new_file_name)


        add_result = self.action_scripts.add_training_with_dialog(self,self._dialogs_ini, sel_items,self._logger, filename)
        wx.CallAfter(self.GetTopLevelParent().Raise)
        if def_result == wx.DragMove and add_result:
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except Exception as ex:
                    self._logger.error(f'{self} ошибка удаления {filename} {ex}')


    def deinit_panel(self):
        if self.info_wnd:
            self.info_wnd.Close()
        if self.export_doc_files_wnd:
            self.export_doc_files_wnd.Close()
        for f in self._tmp_filenames:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception as ex:
                    self._logger.error(f'{self} ошибка удаления {f} {ex}')
        return TableEditorPanel.deinit_panel(self)



    def wxcommand_can_show_info(self):
        return len(self.grid.get_selected_grid_rows())>0


    def wxcommand_show_info(self, evt: wx.CommandEvent):
        act_trainings: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        if len(act_trainings)==0:
            return
        def close():
            self.info_wnd = None
        if self.info_wnd is None:
            self.info_wnd = InputBox(self,'Информация', None, self._dialogs_ini, scrollable=False, sizeable=True, show_buttons=False)
            self.info_wnd.input_panel.add_property('info','Информация:',wx.StaticText, False)
            self.info_wnd.Show()
            self.info_wnd.on_close_dialog = close
        else:
            self.info_wnd.Raise()
        self.update_info_wnd()

    def on_selection_changed(self):
        TableEditorPanel.on_selection_changed(self)
        self.update_info_wnd()

    def update_info_wnd(self):
        act_trainings: List[basicclasses.ActiveTraining] = self.grid.table.get_selected_objects()
        if self.info_wnd:
            info_str = ''
            for act_training in act_trainings:
                trainings: List[basicclasses.Training] = list(act_training.trainings)
                t: basicclasses.Training
                trainings.sort(key=lambda t: (t.issued_date, t.doc_type))
                for tr in trainings:
                    info_str += f'{tr.doc_type.short_name}: {tr.number} от:{tr.issued_date.strftime('%d.%m.%Y') if tr.issued_date else "---"} действует до: {tr.valid_till.strftime('%d.%m.%Y') if tr.valid_till else "---"}\n'
                    info_str += f'{tr.name_path or ""}{tr.doc_file_extension or ""} {'существует' if tr.doc_file_exists else 'нет файла'}\n'
                    info_str += f'{tr.doc_file_hash}\n'
                info_str+='------------\n'
            info_str = info_str.rstrip('------------\n')
            self.info_wnd.input_panel.set_property('info',info_str, None)
