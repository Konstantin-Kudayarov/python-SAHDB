import datetime
import os
import wx

from typing import List, Tuple

import basicclasses
import office_docs

from grid_panel import TableEditorPanel
from update_manager import UpdateManager
from basic import Logger, EventProgressObject, EventType, EventPublisher
from gui_widgets import WxCommand, BasicCheckListWithFilter, ProgressWnd, InputBox, get_colour


from main_window import app_settings
from basicclasses import MainDatabase, Employee, TrainType, TrainingRequest


class ExportTrainRequest:
    main_panel: TableEditorPanel
    _update_manager: UpdateManager
    _logger: Logger

    def __init__(self, main_panel: TableEditorPanel, update_manager: UpdateManager, logger: Logger):
        self.main_panel = main_panel
        self._update_manager = update_manager
        self._logger = logger
        main_panel.toolbar.add_separator_item()
        export_cmd = WxCommand(501, 'Экспорт заявок', os.path.join(app_settings.run_path, r'Icons\MainNotebook\export_xls.ico'), execute_func=self.wxcommand_export_trainings, can_execute_func=self.wxcommand_can_export_trainings)
        main_panel.toolbar.add_tool_item(export_cmd)
        main_panel.toolbar.update_wxcommand_states()

    def write_file(self, dataset: MainDatabase, items: List[Tuple[Employee, TrainType, datetime.date]], notifier: EventPublisher):
        inital_date: datetime.date = items[0][2]
        notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject('Генерация файла'))
        if inital_date:
            fn_name = f'{inital_date.year}_{inital_date.month:02d}_{inital_date.day:02d}_заявка_на_обучение'
        else:
            fn_name = 'без_даты_заявка_на_обучение'
        cur_i = 1
        file_name = os.path.join(dataset.workspace_settings.train_request_path, fn_name + '.xlsx')
        while os.path.exists(file_name):
            file_name = os.path.join(dataset.workspace_settings.train_request_path, fn_name + f'({cur_i})' + '.xlsx')
            cur_i += 1

        notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject('Начало создания'))
        xls_file = office_docs.ExcelDocument(self._logger)
        xls_file.create()
        emp: Employee
        tr_type: TrainType
        dt: datetime.date
        # item: Tuple[basicclasses.Employee, basicclasses.TrainType, datetime.date]

        sorted_items: List[Tuple[Employee, TrainType, datetime.date]] = sorted(items, key=lambda item: (item[1].short_name, item[0].person.full_name_with_date))

        gray_color = xls_file.get_cell_fill(get_colour('LIGHT GRAY'), wx.BRUSHSTYLE_SOLID)
        green_color = xls_file.get_cell_fill(get_colour('SPRING GREEN'), wx.BRUSHSTYLE_SOLID)
        center_alignment = xls_file.get_cell_alignment('center', 'center', False)
        center_with_wrap = xls_file.get_cell_alignment('center', 'center', True)
        all_border = xls_file.get_cell_borders('thin', 'thin', 'thin', 'thin')

        # region Заголовок таблицы
        xls_file.set_data(1, 2, 'Фамилия')
        xls_file.set_fill(1, 2, gray_color)
        xls_file.set_alignment(1, 2, center_alignment)
        xls_file.set_border(1, 2, all_border)
        xls_file.set_col_width(2, 20)
        xls_file.merge_cell(1, 2, 0, 1)

        xls_file.set_data(1, 3, 'Имя')
        xls_file.set_fill(1, 3, gray_color)
        xls_file.set_alignment(1, 3, center_alignment)
        xls_file.set_border(1, 3, all_border)
        xls_file.set_col_width(3, 20)
        xls_file.merge_cell(1, 3, 0, 1)

        xls_file.set_data(1, 4, 'Отчество')
        xls_file.set_fill(1, 4, gray_color)
        xls_file.set_alignment(1, 4, center_alignment)
        xls_file.set_border(1, 4, all_border)
        xls_file.set_col_width(4, 20)
        xls_file.merge_cell(1, 4, 0, 1)

        xls_file.set_data(1, 5, 'Паспорт')
        xls_file.set_fill(1, 5, gray_color)
        xls_file.set_alignment(1, 5, center_alignment)
        xls_file.set_border(1, 5, all_border)
        xls_file.merge_cell(1, 5, 3, 0)

        xls_file.set_data(2, 5, 'Номер')
        xls_file.set_fill(2, 5, gray_color)
        xls_file.set_alignment(2, 5, center_alignment)
        xls_file.set_border(2, 5, all_border)
        xls_file.set_col_width(5, 7)

        xls_file.set_data(2, 6, 'Серия')
        xls_file.set_fill(2, 6, gray_color)
        xls_file.set_alignment(2, 6, center_alignment)
        xls_file.set_border(2, 6, all_border)
        xls_file.set_col_width(6, 9)

        xls_file.set_data(2, 7, 'Кем выдан')
        xls_file.set_fill(2, 7, gray_color)
        xls_file.set_alignment(2, 7, center_alignment)
        xls_file.set_border(2, 7, all_border)
        xls_file.set_col_width(7, 30)

        xls_file.set_data(2, 8, 'Когда выдан')
        xls_file.set_fill(2, 8, gray_color)
        xls_file.set_alignment(2, 8, center_alignment)
        xls_file.set_border(2, 8, all_border)
        xls_file.set_col_width(8, 12)

        xls_file.set_data(1, 9, 'Дата рождения')
        xls_file.set_fill(1, 9, gray_color)
        xls_file.set_alignment(1, 9, center_with_wrap)
        xls_file.set_border(1, 9, all_border)
        xls_file.set_col_width(9, 12)
        xls_file.merge_cell(1, 9, 0, 1)

        xls_file.set_data(1, 10, 'СНИЛС')
        xls_file.set_fill(1, 10, gray_color)
        xls_file.set_alignment(1, 10, center_alignment)
        xls_file.set_border(1, 10, all_border)
        xls_file.set_col_width(10, 15)
        xls_file.merge_cell(1, 10, 0, 1)

        xls_file.set_data(1, 11, 'Должность')
        xls_file.set_fill(1, 11, gray_color)
        xls_file.set_alignment(1, 11, center_alignment)
        xls_file.set_border(1, 11, all_border)
        xls_file.set_col_width(11, 15)
        xls_file.merge_cell(1, 11, 0, 1)

        xls_file.set_data(1, 12, 'Представительство')
        xls_file.set_fill(1, 12, gray_color)
        xls_file.set_alignment(1, 12, center_alignment)
        xls_file.set_border(1, 12, all_border)
        xls_file.set_col_width(12, 35)
        xls_file.merge_cell(1, 12, 0, 1)

        # endregion

        # greenColor = openpyxl.styles.PatternFill(start_color='0092D050', end_color='0092D050', fill_type='solid')

        xls_cur_row = 3
        cur_train_type = None
        for emp, tr_type, dt in sorted_items:
            if tr_type != cur_train_type:
                xls_file.set_data(xls_cur_row, 2, f'{tr_type.short_name} ({tr_type.name})')
                xls_file.set_alignment(xls_cur_row, 12, center_alignment)
                xls_file.set_border(xls_cur_row, 2, all_border)
                xls_file.merge_cell(xls_cur_row, 2, 10, 0)
                xls_file.set_fill(xls_cur_row, 2, green_color)
                cur_train_type = tr_type
                xls_cur_row += 1

            xls_file.set_data(xls_cur_row, 2, emp.person.last_name)
            xls_file.set_alignment(xls_cur_row, 2, center_alignment)
            xls_file.set_border(xls_cur_row, 2, all_border)

            xls_file.set_data(xls_cur_row, 3, emp.person.first_name)
            xls_file.set_alignment(xls_cur_row, 3, center_alignment)
            xls_file.set_border(xls_cur_row, 3, all_border)

            xls_file.set_data(xls_cur_row, 4, emp.person.middle_name)
            xls_file.set_alignment(xls_cur_row, 4, center_alignment)
            xls_file.set_border(xls_cur_row, 4, all_border)

            xls_file.set_data(xls_cur_row, 5, emp.person.passport_series, quote_prefix=True)
            xls_file.set_alignment(xls_cur_row, 5, center_alignment)
            xls_file.set_border(xls_cur_row, 5, all_border)

            xls_file.set_data(xls_cur_row, 6, emp.person.passport_number, quote_prefix=True)
            xls_file.set_alignment(xls_cur_row, 6, center_alignment)
            xls_file.set_border(xls_cur_row, 6, all_border)

            xls_file.set_data(xls_cur_row, 7, emp.person.passport_issued)
            xls_file.set_alignment(xls_cur_row, 7, center_with_wrap)
            xls_file.set_border(xls_cur_row, 7, all_border)

            xls_file.set_data(xls_cur_row, 8, emp.person.passport_issued_date.strftime(app_settings.date_format) if emp.person.passport_issued_date else "не указана", 'auto')
            xls_file.set_alignment(xls_cur_row, 8, center_alignment)
            xls_file.set_border(xls_cur_row, 8, all_border)

            xls_file.set_data(xls_cur_row, 9, emp.person.birth_date if emp.person.birth_date else "не указана", 'auto')
            xls_file.set_alignment(xls_cur_row, 9, center_alignment)
            xls_file.set_border(xls_cur_row, 9, all_border)

            xls_file.set_data(xls_cur_row, 10, emp.person.ssn_number)
            xls_file.set_alignment(xls_cur_row, 10, center_alignment)
            xls_file.set_border(xls_cur_row, 10, all_border)

            xls_file.set_data(xls_cur_row, 11, emp.position.name)
            xls_file.set_alignment(xls_cur_row, 11, center_with_wrap)
            xls_file.set_border(xls_cur_row, 11, all_border)

            xls_file.set_data(xls_cur_row, 12, emp.department.name)
            xls_file.set_alignment(xls_cur_row, 12, center_with_wrap)
            xls_file.set_border(xls_cur_row, 12, all_border)

            notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(f'Добавление обучения {tr_type.short_name} {emp.person.full_name_with_date}'))
            xls_cur_row += 1

        xls_file.save(file_name)
        return file_name

    def wxcommand_export_trainings(self, _evt: wx.CommandEvent):
        items: List[TrainingRequest] = self.main_panel.grid.table.get_selected_objects()
        if len(items) > 0:
            busy = wx.IsBusy()
            if not busy:
                wx.BeginBusyCursor()
            dataset = items[0].table.dataset
            items_to_export: List[Tuple[Employee, TrainType, datetime.date]] = []
            r_date = items[0].request_date
            tr_request: basicclasses.TrainingRequest
            for tr_request in dataset.get_table(TrainingRequest).get_items():
                if r_date is not None and not tr_request.completed and r_date == tr_request.request_date:
                    seek_tuple = tr_request.employee, tr_request.train_type, tr_request.request_date
                    if seek_tuple not in items_to_export:
                        items_to_export.append(seek_tuple)

            item_values = []
            for emp, tr_type, d in items_to_export:
                item_values.append((f'{emp.person.full_name_with_date} {tr_type.short_name}{" от " + d.strftime(app_settings.date_format) if d else " без даты"}', (emp, tr_type, d)))

            input_box = InputBox(self.main_panel, 'Выбор заявок', None, None, size=wx.Size(500, 300), scrollable=False, sizeable=False, ignore_enter_key=False)

            input_box.input_panel.add_property('selected_items', '', BasicCheckListWithFilter, False)
            input_box.input_panel.set_property_size('selected_items', 600, 150)
            input_box.input_panel.set_property('selected_items', items_to_export, item_values)
            input_box.input_panel.add_property('show_file', 'Отобразить файл', bool, False)
            input_box.input_panel.set_property('show_file', True, None)

            # input_box.input_panel.add_property('complete_date', '', datetime.date, False)
            input_box.input_panel.update_view()

            input_box.Fit()
            input_box.Layout()
            input_box.CenterOnParent()
            input_box.input_panel.set_focus()

            if not busy:
                wx.EndBusyCursor()

            r = input_box.ShowModal()

            if r == wx.ID_OK:
                progress = ProgressWnd(self.main_panel.GetTopLevelParent(), 'Изменение', wx.Size(300, 100))
                progress.CenterOnParent()
                progress.Show()
                notifier = progress.get_notifier()
                notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Создание файла'))
                result_fn = self.write_file(dataset, input_box.input_panel.get_property('selected_items', False), notifier)
                if result_fn and os.path.exists(result_fn) and input_box.input_panel.get_property('show_file', False):
                    wx.LaunchDefaultApplication(result_fn)
                    path_to_file, file = os.path.split(result_fn)
                    if os.path.exists(path_to_file):
                        wx.LaunchDefaultBrowser(path_to_file)


                notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Создание файла завершено'))
                progress.Close()

    def wxcommand_can_export_trainings(self):
        items: List[TrainingRequest] = self.main_panel.grid.table.get_selected_objects()
        for item in items:
            if not item.completed:
                return True
        return False