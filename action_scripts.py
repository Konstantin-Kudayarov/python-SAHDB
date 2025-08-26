import configparser
import datetime


from typing import List, Dict, Callable, Tuple, Union, Optional

import dateutil
import dateutil.relativedelta
import wx
import os
import itertools



from gui_widgets import WxEvents, BasicNotebook, BasicPanel
from gui_widgets import (InputBox, BasicCheckListWithFilter, message_box, ProgressWnd,
                         BasicDialog, BasicList, BasicCombobox, InputOutputPanel, ImageList,
                         BasicFileSelect, BasicDatePicker)

from office_docs import ExcelDocument
from warining_window import set_io_panel_warnings, show_info_window, set_iopanel_popup_messages


from basic import EventProgressObject, EventType, Logger, default_notify_level, hash_file



import basicclasses
from basicclasses import MainDatabase, app_settings, MainDBStorableTable,ImportEmployeesConfig




class TrainingEditorDialog(InputBox):
    edit_mode: bool
    dataset: MainDatabase
    ini_config: configparser.ConfigParser
    logger: Logger
    def __init__(self, parent, ini_config, edit_mode, dataset, logger):
        if not edit_mode:
            title = 'Добавить'
        else:
            title = 'Редактировать'

        InputBox.__init__(self, parent, title, None, ini_config, wx.DefaultPosition, wx.DefaultSize, True, True)
        self.edit_mode = edit_mode
        self.dataset = dataset
        self.logger = logger

        if not edit_mode:
            self.input_panel.add_property('multiple', 'Нескольким', bool, False)
            self.input_panel.add_property('employee', 'Сотрудник', BasicCombobox, False)
            self.input_panel.set_property_size('employee', -1, -1)
            self.input_panel.add_property('employees', 'Сотрудники', BasicCheckListWithFilter, False)
            self.input_panel.set_property_size('employees', -1, -1)
        else:
            self.input_panel.add_property('training', 'Обучение', BasicCombobox, False)
            self.input_panel.set_property_size('training', -1, -1)
            self.input_panel.add_property('employee_list', 'Сотрудники', BasicList, False)
            self.input_panel.set_property_size('employee_list', -1, -1)


        self.input_panel.add_property('train_type', 'Тип обучения', BasicCombobox, False)
        self.input_panel.set_property_size('train_type', -1, -1)
        self.input_panel.add_property('doc_type', 'Вид документа', BasicCombobox, False)
        self.input_panel.set_property_size('doc_type', -1, -1)

        self.input_panel.add_property(f'headerline', None, wx.StaticLine, False)
        self.input_panel.set_property_size('headerline', -1, -1)
        self.input_panel.add_property(f'doc_type_name', '', None, False)
        self.input_panel.set_property(f'doc_type_name', '', None)

        self.input_panel.add_property(f'node_path', '', str, False, style=wx.BORDER_NONE|wx.TE_READONLY)


        self.input_panel.set_property_size('doc_type_name', -1, -1)
        self.input_panel.add_property(f'number', '№ документа', str, False)
        self.input_panel.set_property_size('number', 150, -1)
        self.input_panel.add_property(f'issued_date', 'Дата выдачи', datetime.date, False)
        self.input_panel.set_property_size('issued_date', 150, -1)
        self.input_panel.add_property(f'valid_till', 'Дата окончания', datetime.date, False)
        self.input_panel.set_property_size('valid_till', 150, -1)
        self.input_panel.add_property(f'issued_by', 'Кем выдан', BasicCombobox, False)
        self.input_panel.set_property_size('issued_by', -1, -1)
        self.input_panel.set_property(f'issued_by', None, self.dataset.company_cb_values)
        self.input_panel.add_property(f'file', 'Файл', BasicFileSelect, True)
        self.input_panel.set_property_size('file', -1, -1)
        if self.edit_mode:
            self.input_panel.set_property_param('file', 'third_state', True)
        else:
            self.input_panel.set_property_param('file', 'third_state', False)
        self.input_panel.set_property_param('file', 'drag_and_drop', True)
        self.input_panel.update_view()
        self.load_state()
        self.CenterOnParent()
        self.input_panel.set_focus()
        self.input_panel.property_value_changed_callback = self.on_value_changed
        self.Layout()


    def load_dialog_items(self, act_trainings: List[basicclasses.ActiveTraining], file_name: Optional[str]):
        if not self.edit_mode:
            train_type: Optional[basicclasses.TrainType] = None
            employees: List[basicclasses.Employee] = []
            for act_training in act_trainings:
                if train_type is None:
                    train_type = act_training.train_type
                if act_training.train_type == train_type:
                    employees.append(act_training.employee)
            if len(employees) == 0:
                self.input_panel.set_property('multiple',False, None)
                self.input_panel.set_property('employee', None, self.dataset.employees_cb_values)
                self.input_panel.set_property('employees', None, self.dataset.employees_cb_values)
            elif len(employees)==1:
                self.input_panel.set_property('multiple', False, None)
                self.input_panel.set_property('employee', employees[0], self.dataset.employees_cb_values)
                self.input_panel.set_property('employees', None, self.dataset.employees_cb_values)
            elif len(employees)>1:
                self.input_panel.set_property('multiple', True, None)
                self.input_panel.set_property('employee', None, self.dataset.employees_cb_values)
                self.input_panel.set_property('employees', employees, self.dataset.employees_cb_values)


            self.input_panel.show_property('multiple', True, False)
            self.input_panel.show_property('employee', True, False)
            self.input_panel.show_property('employees', True, False)
            self.input_panel.show_property('training', False, False)
            self.input_panel.show_property('employee_list', False, True)
            self.input_panel.enable_property('train_type', True)
            self.input_panel.set_property('train_type', train_type, self.dataset.train_types_cb_values)
            self.input_panel.enable_property('doc_type', True)
            self.input_panel.set_property('doc_type', None, self.dataset.doc_types_cb_values)
            self.input_panel.set_property_param('file', 'third_state',False)
            self.input_panel.set_property('file', file_name, None)


        else:
            used_names: List[str] = []
            for act_training in act_trainings:
                for training in act_training.trainings:
                    if training.training_name not in used_names:
                        used_names.append(training.training_name)

            cb_training_items = []
            cb_training_data = []
            for training_name in used_names:
                cb_training_data.append((training_name, training_name))
                cb_training_items.append(training_name)



            self.input_panel.set_property('training', None, cb_training_data)

            self.input_panel.show_property('multiple',False, False)
            self.input_panel.show_property('employee', False, False)
            self.input_panel.show_property('employees', False, False)
            self.input_panel.show_property('training', True, False)
            self.input_panel.show_property('employee_list', True, True)
            self.input_panel.enable_property('train_type',False)
            self.input_panel.set_property('train_type', None, self.dataset.train_types_cb_values)
            self.input_panel.enable_property('doc_type', False)
            self.input_panel.set_property('doc_type', None, self.dataset.doc_types_cb_values)
            self.input_panel.set_property_param('file', 'third_state',True)

            if len(used_names)==1:
                self.input_panel.set_property('training', used_names[0], None)




        self.on_value_changed(self.input_panel, 'multiple')
        self.on_value_changed(self.input_panel, 'train_type')
        self.on_value_changed(self.input_panel, 'training')

    def save_dialog_items(self, item: basicclasses.Training):
        item.number = self.input_panel.get_property('number',False)
        item.issued_date = self.input_panel.get_property('issued_date', False)
        item.valid_till = self.input_panel.get_property('valid_till', False)
        item.issued_by = self.input_panel.get_property('issued_by', False)
        item.train_type = self.input_panel.get_property('train_type', False)
        item.doc_type = self.input_panel.get_property('doc_type', False)


    #def load_items(self):
    #    if not self.edit_mode:
    #        self.input_panel.set_property('train_type', None, self.dataset.train_types_cb_values)
    #        self.input_panel.enable_property('train_type',False)
    #        self.input_panel.set_property('doc_type', None, self.dataset.doc_types_cb_values)
    #        self.input_panel.enable_property('doc_type', False)


    def on_value_changed(self, io_panel: InputOutputPanel, param_name: str):
        if io_panel.have_property('multiple'):
            multiple = io_panel.get_property('multiple', False)
        else:
            multiple = False

        if param_name == 'multiple':
            if multiple:
                io_panel.show_property('employee',False, False)
                io_panel.show_property('employees', True, True)
                self.Freeze()
                self.Layout()
                self.Thaw()
            else:
                io_panel.show_property('employee', True, False)
                io_panel.show_property('employees', False, True)
                self.Freeze()
                self.Layout()
                self.Thaw()

        selected_train_type = io_panel.get_property('train_type',False)
        selected_doc_type = io_panel.get_property('doc_type', False)
        if io_panel.have_property('employee'):
            selected_employee = io_panel.get_property('employee', False)
            selected_employees = io_panel.get_property('employees', False)
        else:
            selected_employee = None
            selected_employees = None
        if io_panel.have_property('training'):
            selected_training_name: Optional[str] = io_panel.get_property('training', False)
        else:
            selected_training_name = None



        # region Обновить видимость элементов

        show_editable = False
        if selected_train_type and selected_doc_type:
            if not self.edit_mode:
                if (multiple and selected_employees) or (not multiple and selected_employee):
                    show_editable = True
            else:
                if selected_training_name:
                    show_editable = True

        if io_panel.is_proprty_visible('headerline') != show_editable:
            io_panel.show_property('headerline', show_editable, False)
            io_panel.show_property('doc_type_name', show_editable, False)
            io_panel.show_property('number', show_editable, False)
            io_panel.show_property('issued_date', show_editable, False)
            io_panel.show_property('valid_till', show_editable, False)
            io_panel.show_property('file', show_editable, False)
            io_panel.show_property('issued_by', show_editable, True)

            self.Freeze()
            io_panel.Freeze()

            io_panel.Layout()
            self.Layout()

            self.Refresh()
            
            io_panel.Thaw()
            self.Thaw()


        # endregion

        # region Обновить доступность элементов комбобоксов и автозаполнение
        if param_name == 'train_type':
            if selected_train_type:
                tmp_list = list(self.dataset.doc_types_cb_values)
                for doc_name, doc_type in list(tmp_list):
                    if doc_type not in selected_train_type.doc_types:
                        tmp_list.remove((doc_name, doc_type))
                sel_doc_type = None
                if len(selected_train_type.doc_types) == 1:
                    sel_doc_type = selected_train_type.doc_types[0]
                io_panel.set_property('doc_type', sel_doc_type, tmp_list)
            else:
                io_panel.set_property('doc_type', None, [])
            self.on_value_changed(io_panel, 'doc_type')
        elif param_name == 'issued_date':
            if selected_train_type:
                issued_date = io_panel.get_property('issued_date', False)
                if issued_date:
                    years = int(selected_train_type.valid_period_year)
                    months = int((selected_train_type.valid_period_year - years) * 12)
                    valid_till = dateutil.relativedelta.relativedelta(years=years, months=months) + issued_date
                    io_panel.set_property('valid_till', valid_till,None)
        elif param_name == 'doc_type':
            if selected_doc_type:
                io_panel.set_property('doc_type_name', selected_doc_type.full_name, None)
            else:
                io_panel.set_property('doc_type_name', None, None)
        elif param_name == 'training' and io_panel.have_property('training'):
            if selected_training_name:
                employees = []
                train_type: Optional[basicclasses.TrainType] = None
                doc_type: Optional[basicclasses.DocumentType] = None

                number: Optional[str] = None
                issued_date: Optional[datetime.date] = None
                valid_till: Optional[datetime.date] = None
                issued_by: Optional[basicclasses.Company] = None
                node_path: Optional[str] = None


                if selected_training_name in self.dataset.lookup_training_names.keys():
                    sel_trainings: List[basicclasses.Training] = self.dataset.lookup_training_names[selected_training_name]
                    if len(sel_trainings)>0:
                        for tr in sel_trainings:
                            if train_type is None:
                                train_type = tr.train_type
                            if doc_type is None:
                                doc_type = tr.doc_type
                            if tr.train_type == train_type and tr.doc_type == doc_type:
                                employees.append((tr.employee.employee_string, tr.employee))
                        number = sel_trainings[0].number
                        issued_date = sel_trainings[0].issued_date
                        valid_till = sel_trainings[0].valid_till
                        issued_by = sel_trainings[0].issued_by
                        node_path = sel_trainings[0].name_path



                        if sel_trainings[0].doc_file_exists:
                            file_name = self.dataset.get_training_file_name(sel_trainings[0])
                            if not os.path.exists(file_name):
                                message_box(io_panel,'Ошибка', f'Файл {file_name} не найден', wx.ICON_WARNING)


                io_panel.set_property('employee_list', None, employees)
                io_panel.set_property('train_type', train_type, None)
                io_panel.set_property('doc_type', doc_type, None)

                io_panel.set_property('number', number,None)
                io_panel.set_property('issued_date', issued_date, None)
                io_panel.set_property('valid_till', valid_till, None)
                io_panel.set_property('issued_by', issued_by, None)
                io_panel.set_property('node_path', node_path, None)
                self.on_value_changed(io_panel, 'doc_type')
            else:
                io_panel.set_property('employee_list', None, [])
                io_panel.set_property('train_type', None, None)
                io_panel.set_property('doc_type', None, None)

                io_panel.set_property('number', None,None)
                io_panel.set_property('issued_date', None, None)
                io_panel.set_property('valid_till', None, None)
                io_panel.set_property('issued_by', None, None)
                io_panel.set_property('node_path', None, None)
                self.on_value_changed(io_panel, 'doc_type')
        # endregion

        self.update_io_panel_data(io_panel)



    def _show_warnings(self, io_panel: InputOutputPanel, button_msgs: List[Tuple[ImageList.BuiltInImage, str]]):
        if not self.edit_mode:
            required_fields = {'employee': 'сотрудник',
                               'employees': 'сотрудники',
                               'train_type': 'тип обучения',
                               'doc_type': 'вид документа'
                               }
        else:
            required_fields = {'training': 'обучение'
                               }
        warning_list = []
        remove_employee = True
        remove_employees = True

        if io_panel.have_property('multiple'):
            if io_panel.is_proprty_visible('multiple'):
                if io_panel.get_property('multiple',False):
                    remove_employees = False
                else:
                    remove_employee = False

        if remove_employee and 'employee' in required_fields.keys():
            del required_fields['employee']
        if remove_employees and 'employees' in required_fields.keys():
            del required_fields['employees']

        for n, descr in required_fields.items():
            if io_panel.have_property(n):
                val = io_panel.get_property(n, False)
                if not val:
                    warning_list.append(required_fields[n])
        set_io_panel_warnings(self.logger, io_panel, button_msgs, warning_list)


    @WxEvents.debounce(0.8, False)
    def update_io_panel_data(self, io_panel: InputOutputPanel):
        warning_list: List[Tuple[ImageList.BuiltInImage, str]] = []
        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()

        seek_tuples: List[Tuple[basicclasses.Employee, basicclasses.TrainType]] = []

        selected_trainings = []
        if self.edit_mode:
            sel_training_name = io_panel.get_property('training',False)
            selected_trainings = []
            if sel_training_name in self.dataset.lookup_training_names.keys():
                selected_trainings = list(self.dataset.lookup_training_names[sel_training_name])

            employees = list(self.dataset.get_table(basicclasses.Employee).get_items())

            for tr in selected_trainings:
                if tr.employee in employees:
                    employees.remove(tr.employee)
            train_type = io_panel.get_property('train_type', False)
            if train_type and employees:
                seek_tuples = itertools.product(employees, [train_type])


        else:
            employees = list(self.dataset.get_table(basicclasses.Employee).get_items())
            if io_panel.get_property('multiple', False):
                sel_employees = io_panel.get_property('employees',False)
                train_type = io_panel.get_property('train_type',False)

                if train_type and sel_employees:
                    for e in sel_employees:
                        if e in employees:
                            employees.remove(e)
                    seek_tuples = itertools.product(employees, [train_type])
            else:
                employee = io_panel.get_property('employee', False)
                train_type = io_panel.get_property('train_type', False)
                if train_type and employee:
                    if employee in employees:
                        employees.remove(employee)
                    seek_tuples = itertools.product(employees, [train_type])

        # region Найти обучения с таким же именем


        doc_type = io_panel.get_property('doc_type', False)
        train_type = io_panel.get_property('train_type', False)
        number = io_panel.get_property('number', False)
        issued_date = io_panel.get_property('issued_date', False)
        valid_till = io_panel.get_property('valid_till', False)
        issued_by = io_panel.get_property('issued_by', False)

        for seek_tuple in seek_tuples:
            if seek_tuple in self.dataset.lookup_active_trainings.keys():
                for tr in self.dataset.lookup_active_trainings[seek_tuple].trainings:
                    if tr not in selected_trainings:
                        t_train_type, t_doc_type, t_number, t_issued_date, t_valid_till, t_issued_by = tr.train_type, tr.doc_type, tr.number, tr.issued_date, tr.valid_till, tr.issued_by
                        if (train_type, doc_type, number, issued_date, valid_till, issued_by) == (t_train_type, t_doc_type, t_number, t_issued_date, t_valid_till, t_issued_by):
                            warning_list.append((ImageList.BuiltInImage.WARNING, f'Для сотрудника {seek_tuple[0].employee_string} типа обучения {train_type.short_name} {doc_type.full_name} {number} {tr.issued_date.strftime(app_settings.date_format) if tr.issued_date else ""} найдено такое же обучение ID={tr.guid}'))

        # endregion

        # region Найти обучения которые не требуются

        for seek_tuple in seek_tuples:
            if seek_tuple in self.dataset.lookup_required_trainings.keys():
                if not self.dataset.lookup_required_trainings[seek_tuple].required:
                    warning_list.append((ImageList.BuiltInImage.WARNING, f'Для сотрудника {seek_tuple[0].employee_string} типа обучения {seek_tuple[1].short_name} обучение не требуется'))

        # endregion

        # region Найти файлы с одинаковым хэшем
        file_name = io_panel.get_property('file', False)

        if file_name and type(file_name)==str and os.path.exists(file_name):
            file_hash = hash_file(file_name, 512)
            if file_hash in self.dataset.lookup_file_hashes.keys():
                for tr in self.dataset.lookup_file_hashes[file_hash]:
                    if tr not in selected_trainings:
                        warning_list.append((ImageList.BuiltInImage.WARNING, f'Для файла {os.path.split(file_name)[1]} найден такой же файл для обучения {tr.training_name} для сотрудника {tr.employee.employee_string}'))
        # endregion

        if not busy:
            wx.EndBusyCursor()
        self._show_warnings(io_panel, list(warning_list))

class EditImportDialog(BasicDialog):
    cfg: ImportEmployeesConfig
    def __init__(self, parent, title, cfg: ImportEmployeesConfig):
        self.cfg = cfg
        BasicDialog.__init__(self, parent, title, None,wx.DefaultPosition, wx.Size(500,300),configparser.ConfigParser(),True)
        notebook = BasicNotebook(self, wx.Size(16, 16))

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        p1 = BasicPanel(notebook)
        ps1 = wx.BoxSizer(wx.VERTICAL)
        self.edit_departments = wx.TextCtrl(p1, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_DONTWRAP)
        p1.SetSizer(ps1)
        ps1.Add(self.edit_departments, 1, wx.EXPAND | wx.ALL, 0)
        p1.Layout()

        p2 = BasicPanel(notebook)
        ps2 = wx.BoxSizer(wx.VERTICAL)
        self.edit_positions = wx.TextCtrl(p2, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_DONTWRAP)
        p2.SetSizer(ps2)
        ps2.Add(self.edit_positions, 1, wx.EXPAND | wx.ALL, 0)
        p2.Layout()

        p3 = BasicPanel(notebook)
        ps3 = wx.BoxSizer(wx.VERTICAL)
        self.fields_and_offset = wx.TextCtrl(p3, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_DONTWRAP)
        p3.SetSizer(ps3)
        ps3.Add(self.fields_and_offset, 1, wx.EXPAND | wx.ALL, 0)
        p3.Layout()


        p4 = BasicPanel(notebook)
        ps4 = wx.BoxSizer(wx.VERTICAL)
        self.employees_relations = wx.TextCtrl(p4, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_DONTWRAP)
        p4.SetSizer(ps4)
        ps4.Add(self.employees_relations, 1, wx.EXPAND | wx.ALL, 0)
        p4.Layout()

        p5 = BasicPanel(notebook)
        ps5 = wx.BoxSizer(wx.VERTICAL)
        self.ignore_departments = wx.TextCtrl(p5, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_DONTWRAP)
        p5.SetSizer(ps5)
        ps5.Add(self.ignore_departments, 1, wx.EXPAND | wx.ALL, 0)
        p5.Layout()

        p6 = BasicPanel(notebook)
        ps6 = wx.BoxSizer(wx.VERTICAL)
        self.not_ignore_persons = wx.TextCtrl(p6, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_DONTWRAP)
        p6.SetSizer(ps6)
        ps6.Add(self.not_ignore_persons, 1, wx.EXPAND | wx.ALL, 0)
        p6.Layout()


        notebook.add_page('Подразделения', p1)
        notebook.add_page('Должности', p2)
        notebook.add_page('Связи', p3)
        notebook.add_page('Сотрудники', p4)
        notebook.add_page('Игнорировать', p5)
        notebook.add_page('Не игнорировать', p6)


        main_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(main_sizer)
        self.Layout()

        output_text = ''
        for position_name, position_alter in cfg.position_relations.items():
            output_text += f'{position_name}={position_alter}\n'
        output_text = output_text.rstrip('\n')
        self.edit_positions.SetValue(output_text)

        output_text = ''
        for department_name, department_alter in cfg.department_relations.items():
            output_text += f'{department_name}={department_alter}\n'
        output_text = output_text.rstrip('\n')
        self.edit_departments.SetValue(output_text)

        output_text = ''
        for emp_name, emp_alter in cfg.employees_relations.items():
            output_text += f'{emp_name}={emp_alter}\n'
        output_text = output_text.rstrip('\n')
        self.employees_relations.SetValue(output_text)

        output_text = ''
        for dep_name in cfg.ignore_departments:
            output_text += f'{dep_name}\n'
        output_text = output_text.rstrip('\n')
        self.ignore_departments.SetValue(output_text)

        output_text = ''
        for employee_name in cfg.not_ignore:
            output_text += f'{employee_name}\n'
        output_text = output_text.rstrip('\n')
        self.not_ignore_persons.SetValue(output_text)


        output_text = ''
        #employee_name_xls = 0
        #position_xls = 1
        #department_xls = 2
        #offset

        for key, val in cfg.fields.items():
            if key == 0:
                output_text += f'сотрудники={val}\n'
            elif key == 1:
                output_text += f'должности={val}\n'
            elif key == 2:
                output_text += f'подразделения={val}\n'
        output_text +=f'смещение={cfg.offset}'
        self.fields_and_offset.SetValue(output_text)


    def on_close_dialog(self):
        departments_text = self.edit_departments.GetValue()
        self.cfg.department_relations.clear()
        for line in departments_text.splitlines():
            sp_line = line.split('=')
            if len(sp_line)==2:
                self.cfg.department_relations[sp_line[0]] = sp_line[1]

        positions_text = self.edit_positions.GetValue()
        self.cfg.position_relations.clear()
        for line in positions_text.splitlines():
            sp_line = line.split('=')
            if len(sp_line)==2:
                self.cfg.position_relations[sp_line[0]] = sp_line[1]

        employees_text = self.employees_relations.GetValue()
        self.cfg.employees_relations.clear()
        for line in employees_text.splitlines():
            sp_line = line.split('=')
            if len(sp_line) == 2:
                self.cfg.employees_relations[sp_line[0]] = sp_line[1]

        ignore_departments_text = self.ignore_departments.GetValue()
        self.cfg.ignore_departments.clear()
        for line in ignore_departments_text.splitlines():
            self.cfg.ignore_departments.append(line)

        not_ignore_text = self.not_ignore_persons.GetValue()
        self.cfg.not_ignore.clear()
        for line in not_ignore_text.splitlines():
            self.cfg.not_ignore.append(line)

        relations_txt = self.fields_and_offset.GetValue()
        for line in relations_txt.splitlines():
            sp_line = line.split('=')

            if len(sp_line)==2:
                try:
                    val = int(sp_line[1])
                except Exception as _ex:
                    continue
                if sp_line[0] == 'сотрудники':
                    self.cfg.fields[0] = val
                elif sp_line[0] == 'должности':
                    self.cfg.fields[1] = val
                elif sp_line[0] == 'подразделения':
                    self.cfg.fields[2] = val
                elif sp_line[0] == 'смещение':
                    self.cfg.offset = val
        if self.close_callback:
            self.close_callback()



class ActionScripts:
    dataset: MainDatabase
    parent: wx.Frame

    logger: Logger
    sizer: Optional[wx.GridBagSizer]
    dialog_config: configparser.ConfigParser
    def __init__(self, parent:wx.Frame, dataset: MainDatabase, logger: Logger, ini_file: configparser.ConfigParser):
        self.dataset = dataset
        self.parent = parent
        self.logger = logger
        self.sizer = None
        self.dialog_config = ini_file
        self.import_employees_dlg = None

    # какие проверки нужны:
    # 1. убрать добавить требуемые обучения, на основании рекомендованных (выполнено!)
    # 2. проверить требуемые обучения уволенных, вновь принятых (на основе рекомендаций)
    # 3. удалить старые обучения (с истекшим сроком действия)
    # 4. Импортировать рекомендуемые обучения


    # Проверка сотрудников (на соответствие с базой 1С из xlsx файла)
    def wxcommand_edit_import_employees_config(self, _evt: wx.CommandEvent):
        config = ImportEmployeesConfig()
        self.dataset.update_config('import_employees')
        tmp_config = self.dataset.get_config('import_employees')
        if tmp_config:
            config = tmp_config
        self.dataset.write_config('import_employees', config, False, None)

        def on_close():
            self.dataset.write_config('import_employees', config, False, None)
            self.import_employees_dlg = None

        if self.import_employees_dlg is None:
            dlg = EditImportDialog(self.parent, 'Взаимосвязи импорта', config)
            dlg.close_callback = on_close
            self.import_employees_dlg = dlg
            dlg.Show()
        else:
            self.import_employees_dlg.Raise()

    def wxcommand_check_employees(self, _evt: wx.CommandEvent):
        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()

        config = ImportEmployeesConfig()
        self.dataset.update_config('import_employees')
        tmp_config = self.dataset.get_config('import_employees')
        if tmp_config:
            config = tmp_config
        self.dataset.write_config('import_employees', config, False, None)


        error_list = []


        persons_list = {}
        person: basicclasses.Person
        for person in self.dataset.get_table(basicclasses.Person).get_items():
            person_str = f'{person.last_name} {person.first_name} {person.middle_name}'
            if person_str not in persons_list.keys():
                persons_list[person_str] = person
            else:
                error_list.append((ImageList.BuiltInImage.ERROR, f'Личность {person_str} задвоилась, исправьте БД'))


        positions_list = {}
        position: basicclasses.Position
        for position in self.dataset.get_table(basicclasses.Position).get_items():
            position_str = f'{position.short_name}'
            if position_str not in positions_list.keys():
                positions_list[position_str] = position
            else:
                error_list.append((ImageList.BuiltInImage.ERROR, f'Личность {position_str} задвоилась, исправьте БД'))

        departments_list = {}
        department: basicclasses.Department
        for department in self.dataset.get_table(basicclasses.Department).get_items():
            department_str = f'{department.code}'
            departments_list[department_str] = department

        if not busy:
            wx.EndBusyCursor()

        initial_path = self.dataset.workspace_settings.config_path
        if self.dataset.workspace_settings.import_employees_file_name:
            tmp_path = os.path.split(self.dataset.workspace_settings.import_employees_file_name)[0]
            if os.path.exists(tmp_path):
                initial_path = tmp_path

        file_dialog = wx.FileDialog(self.parent, "Выбрать файл с сотрудниками", defaultDir=initial_path, wildcard="Exel файл (*.xlsx)|*.xlsx", style=wx.FD_OPEN)  # | wx.FD_FILE_MUST_EXIST, name="Выбрать")

        r = file_dialog.ShowModal()
        if r != wx.ID_OK:
            return

        self.dataset.workspace_settings.import_employees_file_name = file_dialog.GetPath()

        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()
        xls_info: Tuple[str, str, str]


        employees_should_exists: List[Tuple[str, str, str]] = []

        error_list = []
        xls_file = ExcelDocument(self.logger)
        xls_file.open(file_dialog.GetPath())
        for i in range(1000000):
            current_errors = False
            employee_name_xls = xls_file.get_data(i+config.offset, config.fields[0])
            if not employee_name_xls:
                break

            if employee_name_xls in config.employees_relations.keys():
                employee_name_xls = config.employees_relations[employee_name_xls]

            position_xls = xls_file.get_data(i+config.offset, config.fields[1])
            department_xls = xls_file.get_data(i + config.offset, config.fields[2])
            if employee_name_xls not in persons_list.keys():
                error_list.append((ImageList.BuiltInImage.ERROR,f'Не найдена личность {employee_name_xls} {position_xls} {department_xls}, строка файла {i+config.offset}, необходимо добавить сотрудника'))
                current_errors = True
            if position_xls not in config.position_relations.keys():
                error_list.append((ImageList.BuiltInImage.ERROR,f'Не найдена должность {position_xls} в конфигурационном файле, строка файла {i+config.offset}'))
                current_errors = True
            else:
                if config.position_relations[position_xls] not in positions_list.keys():
                    error_list.append((ImageList.BuiltInImage.ERROR, f'Не найдена должность {config.position_relations[position_xls]} в базе данных, строка файла {i+config.offset}'))
                    current_errors = True

            if department_xls not in config.department_relations.keys():
                error_list.append((ImageList.BuiltInImage.ERROR,f'Не найдено подразделение {department_xls} в конфигурационном файле, строка файла {i+config.offset}'))
                current_errors = True
            else:
                if config.department_relations[department_xls] not in departments_list.keys():
                    error_list.append((ImageList.BuiltInImage.ERROR, f'Не найдено подразделение {config.department_relations[department_xls]} в базе данных, строка файла {i+config.offset}'))
                    current_errors = True

            if current_errors:
                continue

            employees_should_exists.append((employee_name_xls, config.position_relations[position_xls], config.department_relations[department_xls]))

        xls_file.close()
        if not busy:
            wx.EndBusyCursor()
        if error_list:
            show_info_window(self.logger, self.parent, 'Ошибки', error_list, modal=False)
            return
        else:
            employee: basicclasses.Employee
            for employee in self.dataset.get_table(basicclasses.Employee).get_items():
                if employee.department.name in config.ignore_departments:
                    if employee.person.full_name not in config.not_ignore:
                        continue

                seek_tuple = employee.person.full_name, employee.position.short_name, employee.department.code
                if seek_tuple in employees_should_exists: # этот сотрудник среди сотрудников, которые должны существовать
                    employees_should_exists.remove(seek_tuple)
                    if employee.fire_date: # но при этом сотрудник уволен
                        # необходимо оповестить, что сотрудник должен быть добавлен
                        error_list.append((ImageList.BuiltInImage.WARNING, f'Необходимо принять на работу {employee.person.full_name_with_date} {employee.position.name} {employee.department.name}'))
                else: # этот сотрудник не найден в списке и должен быть уволен
                    # необходимо оповестить, что этот сотрудник должен быть уволен
                    if not employee.fire_date: #но только если он не уволен
                        error_list.append((ImageList.BuiltInImage.WARNING, f'Необходимо уволить {employee.person.full_name_with_date} {employee.position.name} {employee.department.name}'))

            for person, position, department in employees_should_exists:
                error_list.append((ImageList.BuiltInImage.WARNING, f'Необходимо принять на работу {person} {position} {department}'))
        if error_list:
            show_info_window(self.logger, self.parent, 'Результаты проверки', error_list,modal=False)
        else:
            message_box(self.parent, 'Результаты проверки', 'Все сотрудники соответствуют списку 1С', wx.ICON_INFORMATION)

    # копирование обучений одного сотрудника другому
    def wxcommand_copy_trainings(self, _evt: wx.CommandEvent):


        progress = ProgressWnd(self.parent.GetTopLevelParent(), 'Подготовка', wx.Size(300, 100))
        notifier = progress.get_notifier()
        notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Выполняется подготовка...', level=default_notify_level))
        progress.CenterOnParent()
        #progress.Show()
        #progress.Hide()


        def on_input_box_value_changed(io_panel: InputOutputPanel, prop_name: str):
            src_employee: basicclasses.Employee = io_panel.get_property('src_employee', False)
            dst_employee: basicclasses.Employee = io_panel.get_property('dst_employee', False)
            selected_trainings: List[basicclasses.Training] = io_panel.get_property('trainings', False)

            error_msg_list = []
            if not src_employee:
                error_msg_list.append('от кого обучения')
            if not dst_employee:
                error_msg_list.append('кому обучения')
            if not selected_trainings:
                error_msg_list.append('перечень копируемых обучений')

            if error_msg_list:
                set_iopanel_popup_messages(self.logger,io_panel, 'Необходимо выбрать: '+', '.join(error_msg_list), wx.ICON_WARNING)
            else:
                set_iopanel_popup_messages(self.logger, io_panel, None, None)


            if prop_name == 'src_employee':
                if src_employee:
                    progress.SetTitle('Поиск обучений')
                    progress.Show()
                    notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Идет поиск...', level=default_notify_level))
                    trainings_list = []
                    act_training: basicclasses.ActiveTraining
                    training: basicclasses.Training
                    for act_training in self.dataset.get_table(basicclasses.ActiveTraining).get_items():
                        if act_training.employee != src_employee:
                            continue

                        for training in act_training.trainings:
                            if training not in trainings_list:
                                trainings_list.append(training)

                    training_checklist_items = []
                    for training in trainings_list:
                        tr_name_str = f'{training.doc_type.full_name} {training.train_type.short_name} '
                        tr_name_str += f'{training.number}{' '+training.issued_date.strftime('%d.%m.%Y') if training.issued_date else ""}'
                        tr_name_str += f'{' '+training.valid_till.strftime('%d.%m.%Y') if training.valid_till else ""}'
                        tr_name_str += f'{' с файлом' if training.doc_file_exists else ' без файла'}'
                        if training.valid_till:
                            if training.valid_till<=datetime.date.today():
                                tr_name_str +=' !истекший срок действия!'
                        training_checklist_items.append((tr_name_str, training))
                    io_panel.set_property('trainings', None, training_checklist_items)
                    progress.Hide()

            if prop_name == 'trainings' or prop_name == 'dst_employee':
                found_same_trainings: List[Tuple[basicclasses.Training, basicclasses.Training]] = []
                if not error_msg_list:
                    progress.SetTitle('Поиск обучений')
                    progress.Show()
                    notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Идет поиск...', level=default_notify_level))


                    for training in list(selected_trainings):
                        seek_tuple = dst_employee, training.train_type
                        if seek_tuple in self.dataset.lookup_active_trainings.keys():
                            for tr in self.dataset.lookup_active_trainings[seek_tuple].trainings:
                                if tr.train_type == training.train_type and tr.doc_type == training.doc_type:
                                    if tr.valid_till>=datetime.date.today():
                                        found_same_trainings.append((training, tr))
                    progress.Hide()

                    if found_same_trainings:
                        output_list:List[Tuple[Optional[ImageList.BuiltInImage], str]] = []
                        for training_tuple in found_same_trainings:
                            out_str = f'Выбранное обучение {training_tuple[0].training_name}, есть похожее {training_tuple[1].training_name}'
                            output_list.append((None, out_str))
                        set_iopanel_popup_messages(self.logger, io_panel, 'Найдены действующие обучения', wx.ICON_WARNING, output_list)


        input_box = InputBox(self.parent, 'Копирование обучений', None, self.dialog_config, size=wx.DefaultSize, scrollable=False, sizeable=True, ignore_enter_key=False)
        input_box.input_panel.property_value_changed_callback = on_input_box_value_changed
        input_box.input_panel.add_property('src_employee', 'От кого обучения', BasicCombobox, False)
        input_box.input_panel.set_property('src_employee', None, self.dataset.employees_cb_values)
        input_box.input_panel.add_property('dst_employee', 'Кому обучения', BasicCombobox, False)
        input_box.input_panel.set_property('dst_employee', None, self.dataset.employees_cb_values)
        input_box.input_panel.add_property('trainings', 'Обучения', BasicCheckListWithFilter, False)
        input_box.input_panel.update_view()
        on_input_box_value_changed(input_box.input_panel,'')

        input_box.Fit()
        input_box.Layout()
        input_box.CenterOnParent()
        input_box.input_panel.set_focus()
        input_box.load_state()
        result = input_box.ShowModal()
        input_box.save_state()
        if result == wx.ID_OK:
            selected_trainings: List[basicclasses.Training] = input_box.input_panel.get_property('trainings',False)
            src_employee: basicclasses.Employee = input_box.input_panel.get_property('src_employee', False)
            dst_employee: basicclasses.Employee = input_box.input_panel.get_property('dst_employee', False)

            if not selected_trainings or len(selected_trainings)==0:
                message_box(self.parent,'Ошибка', 'Не выбраны обучения для копирования', wx.ICON_WARNING)
                progress.Close()
                return

            if not src_employee:
                message_box(self.parent, 'Ошибка', 'Не выбран исходный сотрудник', wx.ICON_WARNING)
                progress.Close()
                return
            if not dst_employee:
                message_box(self.parent, 'Ошибка', 'Не выбран конечный сотрудник', wx.ICON_WARNING)
                progress.Close()
                return
            if src_employee == dst_employee:
                message_box(self.parent, 'Ошибка', 'Выбран один и тот же сотрудник, копирование невозможно', wx.ICON_WARNING)
                progress.Close()
                return

            progress.SetTitle('Сохранение')
            progress.Show()
            notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Выполняется подготовка...', level=default_notify_level))
            max_i = len(selected_trainings)
            training_table = self.dataset.get_table(basicclasses.Training)
            added_trainings = []
            for i, src_training in enumerate(selected_trainings):
                notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject('Копирование', cur_val=i+1, max_val=max_i, level=default_notify_level))

                new_training = basicclasses.Training(training_table)

                new_training.new_guid()
                new_training.doc_type = src_training.doc_type
                new_training.train_type = src_training.train_type
                new_training.number = src_training.number
                new_training.issued_by = src_training.issued_by
                new_training.issued_date = src_training.issued_date
                new_training.valid_till = src_training.valid_till
                new_training.employee = dst_employee
                new_training.active = True

                save_file_name = ''
                file_ext = src_training.doc_file_extension
                if file_ext is None:
                    file_ext = ''
                if src_training.doc_file_exists:
                    save_file_name = os.path.join(self.dataset.workspace_settings.db_files_path, src_training.name_path)+file_ext
                    if not os.path.exists(save_file_name):
                        save_file_name = ''

                add_result, error_msg = self._add_training(new_training,training_table, save_file_name)
                if add_result:
                    added_trainings.append(new_training)

            notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Копирование завершено', cur_val=max_i, max_val=max_i, level=default_notify_level))
            progress.Close()
            self.complete_requests(self.parent, self.dialog_config, added_trainings,self.logger)

        if progress.IsShown():
            progress.Close()



    def wxcommand_file_structure(self, _evt: wx.CommandEvent):
        progress = ProgressWnd(self.parent.GetTopLevelParent(), 'Подготовка', wx.Size(600, 100))
        notifier = progress.get_notifier()
        notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Выполняется подготовка...', level=default_notify_level))
        progress.CenterOnParent()
        progress.Show()

        found_files = []

        archive_folder = os.path.join(self.dataset.workspace_settings.db_files_path, app_settings.archive_folder)
        removed_folder = os.path.join(self.dataset.workspace_settings.db_files_path, app_settings.delete_folder)

        found_files_hashes: Dict[str, List[str]] = {}

        for root, dirs, files in os.walk(self.dataset.workspace_settings.db_files_path):
            cur_path = os.path.relpath(root, self.dataset.workspace_settings.db_files_path)
            notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(f'Поиск файлов {cur_path}', level=default_notify_level))


            for file in files:
                if not (root.startswith(removed_folder) or root.startswith(archive_folder)):
                    found_files.append(os.path.join(root,file))
                file_name = os.path.join(root, file)
                file_hash = hash_file(file_name, 512)
                if file_hash not in found_files_hashes.keys():
                    found_files_hashes[file_hash] = []
                found_files_hashes[file_hash].append(file_name)



        actions: List[Tuple[int, Optional[Union[basicclasses.Training, basicclasses.PersonallDocument]], Optional[str]]] = []
        # 1 - необходимо обновить что файл существует и установить ему хэш
        # 2 - хеш отличается - обновить хэш
        # 3 - файл не найден, обновить информацию в БД
        db_files = []
        training: basicclasses.Training
        e_max = len(self.dataset.get_table(basicclasses.Training).get_items())
        for i, training in enumerate(self.dataset.get_table(basicclasses.Training).get_items()):

            notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(f'Анализ БД: обучения', cur_val=i+1, max_val=e_max, level=default_notify_level))

            train_name_file = os.path.join(self.dataset.workspace_settings.db_files_path, training.name_path)
            if training.doc_file_extension is not None:
                train_name_file += training.doc_file_extension

            if os.path.exists(train_name_file):
                if training.doc_file_exists is False:
                    actions.append((1, training, train_name_file))

                file_hash = hash_file(train_name_file,512)
                if training.doc_file_hash != file_hash:
                    actions.append((2, training, train_name_file))
                db_files.append(train_name_file)
            else:
                if training.doc_file_exists is True:
                    actions.append((3, training, train_name_file))
                if training.doc_file_hash in found_files_hashes.keys():
                    for fn in found_files_hashes[training.doc_file_hash]:
                        actions.append((5, training, fn))



        personal_doc: basicclasses.PersonallDocument
        e_max = len(self.dataset.get_table(basicclasses.PersonallDocument).get_items())

        for i, personal_doc in enumerate(self.dataset.get_table(basicclasses.PersonallDocument).get_items()):
            doc_name_file = os.path.join(self.dataset.workspace_settings.db_files_path, personal_doc.name_path)
            notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(f'Анализ БД: личные документы', cur_val=i+1, max_val=e_max, level=default_notify_level))

            if os.path.exists(doc_name_file):
                if personal_doc.doc_file_exists is False:
                    actions.append((1, personal_doc, doc_name_file))

                file_hash = hash_file(doc_name_file, 512)
                if personal_doc.doc_file_hash != file_hash:
                    actions.append((2, personal_doc, doc_name_file))
                db_files.append(doc_name_file)
            else:
                if personal_doc.doc_file_exists is True:
                    actions.append((3, personal_doc, doc_name_file))
                if personal_doc.doc_file_hash in found_files_hashes.keys():
                    for fn in found_files_hashes[personal_doc.doc_file_hash]:
                        actions.append((5, personal_doc, fn))


        for f_file_name in found_files:
            if f_file_name not in db_files:
                actions.append((4, None, f_file_name))

        notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject(f'Анализ БД завершен', cur_val=1, max_val=1, level=default_notify_level))

        if progress.IsShown():
            progress.Hide()


        input_box_items = []

        actions.sort(key=lambda f: (0 if f[1] is None else (2 if isinstance(f[1], basicclasses.Training) else 1),
                                    f[1].employee.person.full_name_with_date if isinstance(f[1], basicclasses.Training) else None,
                                    f[1].person.full_name_with_date if isinstance(f[1], basicclasses.PersonallDocument) else None,
                                    f[0]))

        for act in actions:
            act_type: int = act[0]
            item: Union[basicclasses.Training, basicclasses.PersonallDocument] = act[1]
            file_name: str = act[2]
            inputbox_str = ''
            if act_type == 1:
                inputbox_str=   'Записать в БД файл существует для:'
            elif act_type == 2:
                inputbox_str =  'Изменить в БД  хэш файла для:'
            elif act_type == 3:
                inputbox_str =  'Установить в БД - файл не существует для:'
            elif act_type == 4:
                inputbox_str = f'Удалить файл из файловой системы: {file_name}'
            elif act_type == 5:
                inputbox_str = f'Скопировать файл для:'
            if act_type in [1,2,3, 5]:
                if type(item) == basicclasses.Training:
                    item: basicclasses.Training
                    inputbox_str += f'{item.employee.person.full_name} {item.employee.position.short_name} {item.employee.department.name} {item.training_name}'
                elif type(item) == basicclasses.PersonallDocument:
                    item: basicclasses.PersonallDocument
                    inputbox_str += f'{item.person.full_name_with_date} {item.doc_type.full_name}{" "+item.doc_name if item.doc_name else ""}'
                if act_type == 5:
                    inputbox_str+= f' {os.path.split(os.path.relpath(file_name, self.dataset.workspace_settings.db_files_path))[0]}...{os.path.basename(file_name)}'

            input_box_items.append((inputbox_str, act))
        if actions:
            input_box = InputBox(self.parent, 'Исправление файлов', None, self.dialog_config, size=wx.DefaultSize, scrollable=False, sizeable=True, ignore_enter_key=False)
            input_box.input_panel.add_property('actions', '', BasicCheckListWithFilter, False)
            input_box.input_panel.update_view()

            input_box.Fit()
            input_box.Layout()
            input_box.CenterOnParent()
            input_box.input_panel.set_focus()
            input_box.load_state()
            input_box.input_panel.set_property('actions', actions, input_box_items)
            result = input_box.ShowModal()
            input_box.save_state()


            if result == wx.ID_OK:
                selected_actions = input_box.input_panel.get_property('actions', False)
                progress.Show()
                error_msg = []
                e_max = len(selected_actions)
                p_doc_table = self.dataset.get_table(basicclasses.PersonallDocument)
                tr_table = self.dataset.get_table(basicclasses.Training)
                for i, act in enumerate(selected_actions):
                    notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(f'Внесение изменений', cur_val=i + 1, max_val=e_max, level=default_notify_level))

                    act_type: int = act[0]
                    item: Union[basicclasses.Training, basicclasses.PersonallDocument] = act[1]
                    file_name: str = act[2]

                    if act_type in [1, 2]:
                        if type(item) == basicclasses.Training:
                            item: basicclasses.Training
                            file_hash = hash_file(file_name, 512)
                            item.doc_file_hash = file_hash
                            item.doc_file_exists = True
                            tr_table.write(item, app_settings.use_history, True)

                        elif type(item) == basicclasses.PersonallDocument:
                            item: basicclasses.PersonallDocument
                            file_hash = hash_file(file_name, 512)
                            item.doc_file_hash = file_hash
                            item.doc_file_exists = True
                            p_doc_table.write(item, app_settings.use_history, True)

                    elif act_type == 3:
                        if type(item) == basicclasses.Training:
                            item: basicclasses.Training
                            item.doc_file_hash = None
                            item.doc_file_exists = False
                            tr_table.write(item, app_settings.use_history, True)


                        elif type(item) == basicclasses.PersonallDocument:
                            item: basicclasses.PersonallDocument
                            item.doc_file_hash = None
                            item.doc_file_exists = False
                            p_doc_table.write(item,app_settings.use_history, True)

                    elif act_type == 4:
                        move_result, move_str = self.dataset.move_file(file_name, app_settings.delete_folder,True)
                        if not move_result:
                            error_msg.append(move_str)
                    elif act_type == 5:
                        dst_file = None
                        if type(item) == basicclasses.Training:
                            item: basicclasses.Training
                            dst_file = os.path.join(self.dataset.workspace_settings.db_files_path, item.name_path)+item.doc_file_extension


                        elif type(item) == basicclasses.PersonallDocument:
                            item: basicclasses.PersonallDocument
                            dst_file = os.path.join(self.dataset.workspace_settings.db_files_path, item.name_path)

                        if dst_file and not os.path.exists(dst_file):
                            copy_result, copy_str = self.dataset.copy_file(file_name, dst_file)
                            if not copy_result:
                                error_msg.append(copy_str)
                        else:
                            error_msg.append(f'Ошибка копирования файла не получилось определить имя конечного файла для исходного: {file_name}')
                if error_msg:
                    show_info_window(self.logger, self.parent, 'Результаты выполнения', error_msg, modal=False)
        else:
            message_box(self.parent, 'Результаты проверки', 'Ошибок в БД и лишних файлов не найдено', wx.ICON_INFORMATION)

        notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(f'Завершено', cur_val=1, max_val=1, level=default_notify_level))
        progress.Close()













    # region Укрупненные действия

    def _add_training(self, new_training: basicclasses.Training, training_table: MainDBStorableTable, file_name: str)->Tuple[bool, List]:
        error_messages = []
        file_ext = ''
        if file_name and os.path.splitext(file_name):
            file_ext = os.path.splitext(file_name)[1]
        new_training.name_path = self.dataset.generate_training_path(new_training)
        new_training.doc_file_extension = None
        if file_name and os.path.exists(file_name):
            dst_file_name = self.dataset.get_training_file_name(new_training)
            copy_result, copy_msg = self.dataset.copy_file(file_name, dst_file_name + file_ext)
            if not copy_result:
                new_training.doc_file_exists = False
                new_training.doc_file_hash = None
                new_training.doc_file_extension = None
                error_messages.append((ImageList.BuiltInImage.ERROR, f'Ошибка копирования файла {file_name} для обучения {new_training.name_path} {copy_msg}'))
            else:
                new_training.doc_file_exists = True
                new_training.doc_file_hash = hash_file(dst_file_name+file_ext, 512)
                new_training.doc_file_extension = file_ext
        else:
            new_training.doc_file_exists = False
            new_training.doc_file_hash = None
            new_training.doc_file_extension = None
        add_result = training_table.add(new_training, app_settings.use_history, True)
        return add_result, error_messages



    def add_training_with_dialog(self, parent_wnd: Union[wx.Frame, wx.Panel], ini_file: configparser.ConfigParser, act_trainings: List[basicclasses.ActiveTraining], logger: Logger, filename: Optional[str]):
        dlg = TrainingEditorDialog(parent_wnd, ini_file, False, self.dataset, logger)
        dlg.load_dialog_items(act_trainings, filename)
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            if dlg.input_panel.get_property('multiple', False):
                employees = list(dlg.input_panel.get_property('employees', False))
            else:
                employee = dlg.input_panel.get_property('employee', False)
                if employee is not None:
                    employees = [employee]
                else:
                    employees = []
            training_table = self.dataset.get_table(basicclasses.Training)

            error_messages = []
            progress = ProgressWnd(parent_wnd.GetTopLevelParent(), 'Добавление', wx.Size(300, 100))
            notifier = progress.get_notifier()
            notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Добавление элементов', level=default_notify_level))
            e_len = len(employees)
            added_trainings: List[basicclasses.Training] = []
            if len(employees) == 0:
                progress.Close()
                message_box(parent_wnd, 'Ошибка', 'Не выбраны сотрудники. Обучение не добавлено', wx.ICON_WARNING)
                return

            for i, employee in enumerate(employees):
                notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Добавление элемента {training_table.name}', cur_val=i+1, max_val=e_len, level=default_notify_level))
                new_training = basicclasses.Training(training_table)
                new_training.new_guid()
                new_training.active = True
                new_training.employee = employee
                dlg.save_dialog_items(new_training)

                if new_training.train_type is None:
                    progress.Close()
                    message_box(parent_wnd, 'Ошибка', 'Не выбран тип обучения. Обучение не добавлено', wx.ICON_WARNING)
                    return
                if new_training.doc_type is None:
                    progress.Close()
                    message_box(parent_wnd, 'Ошибка', 'Не выбран вид документа. Обучение не добавлено', wx.ICON_WARNING)
                    return

                dialog_file_name = dlg.input_panel.get_property('file', False)
                add_result, e_msg = self._add_training(new_training, training_table, dialog_file_name)
                if e_msg:
                    error_messages.extend(e_msg)
                if not add_result:
                    error_messages.append((ImageList.BuiltInImage.ERROR, f'Невозможно добавить: {new_training.name_path}'))
                else:
                    added_trainings.append(new_training)
            notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Добавление элементов завершено', cur_val=e_len, max_val=e_len, level=default_notify_level))
            progress.Close()
            if error_messages:
                show_info_window(self.logger, parent_wnd,'Ошибки добавления', error_messages)

            self.complete_requests(parent_wnd, ini_file, added_trainings, logger)

            # TODO: добавить проверку на заявки и завершить заявки при необходимости


            return len(error_messages)==0
        else:
            return False

    def edit_training(self, parent_wnd: Union[wx.Frame, wx.Panel], ini_file: configparser.ConfigParser, act_trainings: List[basicclasses.ActiveTraining], logger: Logger):
        dlg = TrainingEditorDialog(parent_wnd, ini_file, True, self.dataset, logger)
        dlg.load_dialog_items(act_trainings, None)

        result = dlg.ShowModal()
        if result == wx.ID_OK:
            training_name = dlg.input_panel.get_property('training',False)
            if training_name in self.dataset.lookup_training_names.keys():
                trainings: List[basicclasses.Training] = list(self.dataset.lookup_training_names[training_name])

                training_table = self.dataset.get_table(basicclasses.Training)

                error_messages = []
                progress = ProgressWnd(parent_wnd.GetTopLevelParent(), 'Изменение', wx.Size(300, 100))
                notifier = progress.get_notifier()
                notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Изменение элементов', level=default_notify_level))
                e_len = len(trainings)

                edited_trainings: List[basicclasses.Training] = []

                for i, training in enumerate(trainings):
                    tmp_training = training.copy()
                    notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Изменение элемента {training_table.name}', cur_val=i + 1, max_val=e_len, level=default_notify_level))
                    dlg.save_dialog_items(tmp_training)
                    if tmp_training.train_type is None:
                        progress.Close()
                        message_box(parent_wnd, 'Ошибка', 'Не выбран тип обучения. Обучение не добавлено', wx.ICON_WARNING)
                        return
                    if tmp_training.doc_type is None:
                        progress.Close()
                        message_box(parent_wnd, 'Ошибка', 'Не выбран вид документа. Обучение не добавлено', wx.ICON_WARNING)
                        return

                    dialog_file_name = dlg.input_panel.get_property('file', False)
                    db_file_name = self.dataset.get_training_file_name(tmp_training)

                    # для каждого обучения имя файла будет разным!, но имена обучений одинаковые
                    #

                    # если задано новое имя, то заменим всем объектам новый файл
                    if dialog_file_name != BasicFileSelect:
                        # и если новое имя пустое или новое имя задано
                        if (dialog_file_name and os.path.exists(dialog_file_name)) or not dialog_file_name:
                            # если есть старое имя файла, его небходимо удалить
                            if db_file_name:
                                if os.path.exists(db_file_name):
                                    move_result, move_msg = self.dataset.move_file(db_file_name, app_settings.archive_folder, True)
                                else:
                                    move_result = True
                                    move_msg = ''

                                if not move_result:
                                    error_messages.append((ImageList.BuiltInImage.ERROR, f'Невозможно удалить старый файл: {db_file_name} обучение {tmp_training.name_path} {move_msg}'))
                                else:
                                    tmp_training.doc_file_exists = False
                                    tmp_training.doc_file_hash = None
                                    tmp_training.doc_file_extension = None
                                    tmp_training.save(training, False, True)
                                    write_result = training_table.write(training, app_settings.use_history, True)
                                    if not write_result:
                                        error_messages.append((ImageList.BuiltInImage.ERROR, f'Невозможно изменить: {tmp_training.name_path}'))
                                    else:
                                        if training not in edited_trainings:
                                            edited_trainings.append(training)
                        # если файл с новым именем существует, необходимо скопировать на все объекты
                        if dialog_file_name and os.path.exists(dialog_file_name):
                            dialog_file_ext = os.path.splitext(dialog_file_name)[1]
                            # если расширения файлов отличаются (или было пустое а стало не пустое), то допишем новое расширение
                            new_file_name = self.dataset.get_training_file_name(tmp_training) + dialog_file_ext
                            if dialog_file_name != db_file_name:  # если заданный в диалоге файл это тругой файл
                                copy_result, copy_msg = self.dataset.copy_file(dialog_file_name, new_file_name)
                                if not copy_result:
                                    tmp_training.doc_file_exists = False
                                    tmp_training.doc_file_extension = None
                                    tmp_training.doc_file_hash = None
                                    error_messages.append((ImageList.BuiltInImage.ERROR, f'Невозможно скопировать файл: {dialog_file_name} обучение {tmp_training.name_path} {copy_msg}'))
                                else:
                                    if training not in edited_trainings:
                                        edited_trainings.append(training)
                                    tmp_training.doc_file_extension = dialog_file_ext
                                    tmp_training.doc_file_exists = True
                                    tmp_training.doc_file_hash = hash_file(new_file_name, 512)

                    tmp_training.save(training, False, True)
                    write_result = training_table.write(training, app_settings.use_history, True)
                    if not write_result:
                        error_messages.append((ImageList.BuiltInImage.ERROR, f'Невозможно изменить: {tmp_training.name_path}'))
                    else:
                        if training not in edited_trainings:
                            edited_trainings.append(training)


                notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Изменения элементов завершено', cur_val=e_len, max_val=e_len, level=default_notify_level))
                progress.Close()
                if error_messages:
                    show_info_window(self.logger, parent_wnd, 'Ошибки изменения', error_messages)

            else:
                message_box(parent_wnd, 'Ошибка', 'Не выбрано обучение. Обучение не добавлено', wx.ICON_WARNING)


    def delete_trainings(self, parent_wnd: Union[wx.Frame, wx.Panel], ini_file: configparser.ConfigParser, act_trainings: List[basicclasses.ActiveTraining], logger: Logger):
        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()

        input_box = InputBox(parent_wnd, 'Удаление элементов', None, None, size=wx.Size(500, 300), scrollable=False, sizeable=False, ignore_enter_key=False)
        input_box.input_panel.add_property('selected_items', '', BasicCheckListWithFilter, False)
        input_box.input_panel.set_property_size('selected_items', 600, 250)
        input_box.input_panel.update_view()

        input_box.Fit()
        input_box.Layout()
        input_box.CenterOnParent()
        input_box.input_panel.set_focus()
        input_box.load_state()

        items_to_show: List[Tuple[str, basicclasses.Training]] = []
        items_to_select: List[basicclasses.Training] = []
        for item in act_trainings:
            for tr in item.trainings:
                if tr.name_path in self.dataset.lookup_training_paths.keys():
                    for cur_tr in self.dataset.lookup_training_paths[tr.name_path]:
                        if cur_tr not in items_to_select:
                            item_name = f'{cur_tr.employee.node_name} {cur_tr.training_name}'
                            items_to_show.append((item_name, cur_tr))
                            items_to_select.append(cur_tr)

        input_box.input_panel.set_property('selected_items', items_to_select, items_to_show)
        result = input_box.ShowModal()
        input_box.save_state()
        if not busy:
            wx.EndBusyCursor()
        if result == wx.ID_OK:
            trainings_to_delete: List[basicclasses.Training] = list(input_box.input_panel.get_property('selected_items', False))
            #noinspection PyTypeChecker
            items_list_ctrl: BasicCheckListWithFilter = input_box.input_panel.get_control('selected_items')
            visible_items = items_list_ctrl.get_visible_value()
            for tr_del in list(trainings_to_delete):
                if tr_del not in visible_items:
                    trainings_to_delete.remove(tr_del)

            training_table =  self.dataset.get_table(basicclasses.Training)

            progress = ProgressWnd(parent_wnd.GetTopLevelParent(), 'Удаление', wx.Size(300, 100))
            notifier = progress.get_notifier()
            notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Удаление элементов', level=100))
            progress.CenterOnParent()
            progress.Show()
            e_max_count = len(trainings_to_delete)
            e_count_i = 0
            error_list = []
            for t in list(trainings_to_delete):
                e_count_i += 1
                notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Удаление файла {training_table.name}', cur_val=e_count_i, max_val=e_max_count, level=101))
                file_to_delete = self.dataset.get_training_file_name(t)
                if t.doc_file_exists is True and os.path.exists(file_to_delete):
                    del_result, del_message = self.dataset.move_file(file_to_delete, app_settings.archive_folder, True)
                    if not del_result:
                        error_list.append(del_message)
                notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Удаление данных {training_table.name}', cur_val=e_count_i, max_val=e_max_count, level=101))
                if not training_table.delete_mark(t, app_settings.use_history, True):
                    error_list.append(f'Ошибка удаления: {t.name_path} {t.training_name}')
            notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject(msg=f'Удаление данных {training_table.name} завершено', cur_val=e_count_i, max_val=e_max_count, level=101))
            progress.Close()

            if error_list:
                message_box(parent_wnd, 'Ошибка', f'Ошибка удаления объектов', wx.ICON_ERROR, '\n'.join(error_list))

            self.delete_requests(parent_wnd, ini_file, trainings_to_delete, logger)


    def delete_requests(self, parent_wnd: Union[wx.Frame, wx.Panel], _ini_file: configparser.ConfigParser, trainings: List[basicclasses.Training], _logger: Logger):
        requests = []

        for tr in trainings:
            seek_tuple = (tr.employee, tr.train_type, tr.doc_type)
            if seek_tuple in self.dataset.lookup_train_requests.keys():
                tr_requests: List[basicclasses.TrainingRequest] = self.dataset.lookup_train_requests[seek_tuple]
                for tr_request in tr_requests:
                    if tr_request.requested and tr_request.completed:
                        if tr_request not in requests:
                            requests.append(tr_request)

        if len(requests) > 0:
            input_box = InputBox(parent_wnd, 'Удаление заявок', None, None, size=wx.Size(500, 300), scrollable=False, sizeable=False, ignore_enter_key=False)
            input_box.input_panel.add_property('selected_items', '', BasicCheckListWithFilter, False)
            input_box.input_panel.set_property_size('selected_items', 600, 250)


            items_to_show: List[Tuple[str, basicclasses.TrainingRequest]] = []
            items_to_select: List[basicclasses.TrainingRequest] = []

            for item in requests:
                items_to_show.append((f'{item.employee.employee_string} {item.train_type.short_name} {item.doc_type.short_name}, заявка от: {item.request_date.strftime(app_settings.date_format)}, заявка завершена: {item.complete_date.strftime(app_settings.date_format)}', item))
                items_to_select.append(item)

            input_box.input_panel.set_property('selected_items', items_to_select, items_to_show)
            input_box.input_panel.update_view()
            input_box.load_state()
            input_box.Fit()
            input_box.Layout()
            input_box.CenterOnParent()
            input_box.input_panel.set_focus()
            result = input_box.ShowModal()
            input_box.save_state()
            if result == wx.ID_OK:
                progress = ProgressWnd(parent_wnd.GetTopLevelParent(), 'Завершение заявок', wx.Size(300, 100))
                notifier = progress.get_notifier()
                notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Удаление элементов', level=default_notify_level))
                progress.CenterOnParent()
                progress.Show()

                table = self.dataset.get_table(basicclasses.TrainingRequest)
                selected_items: List[basicclasses.TrainingRequest] = input_box.input_panel.get_property('selected_items', False)
                # noinspection PyTypeChecker
                items_list_ctrl: BasicCheckListWithFilter = input_box.input_panel.get_control('selected_items')
                visible_items = items_list_ctrl.get_visible_value()
                for tr_del in list(selected_items):
                    if tr_del not in visible_items:
                        selected_items.remove(tr_del)

                for i, item in enumerate(selected_items):
                    table.delete_mark(item, app_settings.use_history, True)
                    notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject('Удаление элементов', cur_val=i + 1, max_val=len(selected_items), level=default_notify_level))

                notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Удаление элементов', cur_val=len(selected_items), max_val=len(selected_items), level=default_notify_level))
                progress.Close()


    def complete_requests(self, parent_wnd: Union[wx.Frame, wx.Panel], _ini_file: configparser.ConfigParser, trainings: List[basicclasses.Training], _logger: Logger):
        requests = []

        for tr in trainings:
            seek_tuple = (tr.employee, tr.train_type, tr.doc_type)
            if seek_tuple in self.dataset.lookup_train_requests.keys():
                tr_requests: List[basicclasses.TrainingRequest] = self.dataset.lookup_train_requests[seek_tuple]
                for tr_request in tr_requests:
                    if tr_request.requested and not tr_request.completed:
                        if tr_request not in requests:
                            requests.append(tr_request)

        if len(requests) > 0:
            input_box = InputBox(parent_wnd, 'Завершение заявок', None, None, size=wx.Size(500, 300), scrollable=False, sizeable=False, ignore_enter_key=False)
            input_box.input_panel.add_property('selected_items', '', BasicCheckListWithFilter, False)
            input_box.input_panel.set_property_size('selected_items', 600, 250)
            input_box.input_panel.add_property('complete_date', 'Дата завершения', BasicDatePicker, False)

            items_to_show: List[Tuple[str, basicclasses.TrainingRequest]] = []
            items_to_select: List[basicclasses.TrainingRequest] = []

            for item in requests:
                items_to_show.append((f'{item.employee.employee_string} {item.train_type.short_name} {item.doc_type.short_name}, заявка от: {item.request_date.strftime(app_settings.date_format)}', item))
                items_to_select.append(item)

            input_box.input_panel.set_property('selected_items', items_to_select, items_to_show)
            input_box.input_panel.set_property('complete_date', datetime.date.today(), None)
            input_box.input_panel.update_view()

            input_box.Fit()
            input_box.Layout()
            input_box.CenterOnParent()
            input_box.input_panel.set_focus()
            input_box.load_state()
            result = input_box.ShowModal()
            input_box.save_state()
            if result == wx.ID_OK:
                complete_date = input_box.input_panel.get_property('complete_date', False)
                if not complete_date:
                    complete_date = datetime.date.today()

                progress = ProgressWnd(parent_wnd.GetTopLevelParent(), 'Завершение заявок', wx.Size(300, 100))
                notifier = progress.get_notifier()
                notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Сохранение элементов', level=default_notify_level))
                progress.CenterOnParent()
                progress.Show()

                table = self.dataset.get_table(basicclasses.TrainingRequest)
                selected_items: List[basicclasses.TrainingRequest] = input_box.input_panel.get_property('selected_items', False)
                # noinspection PyTypeChecker
                items_list_ctrl: BasicCheckListWithFilter = input_box.input_panel.get_control('selected_items')
                visible_items = items_list_ctrl.get_visible_value()
                for tr_del in list(selected_items):
                    if tr_del not in visible_items:
                        selected_items.remove(tr_del)

                for i, item in enumerate(selected_items):
                    item.complete_date = complete_date
                    table.write(item, app_settings.use_history, True)
                    notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject('Сохранение элементов', cur_val=i + 1, max_val=len(selected_items), level=default_notify_level))

                notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Сохранение элементов', cur_val=len(selected_items), max_val=len(selected_items), level=default_notify_level))
                progress.Close()

    # endregion


