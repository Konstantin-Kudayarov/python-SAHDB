import configparser

import itertools
from typing import Any, List, Tuple, Dict

import wx.grid


import basicclasses
from basic import EventType, EventProgressObject, default_notify_level, EventObject, EventSubscriber

from grid_panel import TableEditorPanel
from basicclasses import MainDatabase, app_settings, MainDBStorableTable
from gui_widgets import (DBInputDialog, BasicCheckListWithFilter, message_box, ProgressWnd,
                         BasicPanel, WxEvents, BasicPopupWindow, BasicList)


class RequiredTrainingsPanel(TableEditorPanel):
    dataset: MainDatabase
    _cur_item: Any
    def __init__(self, parent, name, logger, status_bar, main_menu, config, update_manager):
        TableEditorPanel.__init__(self, parent, name, logger, status_bar, main_menu, config, update_manager)
        self.toolbar.update_wxcommand_states()
        self.dataset = config.grid_table.dataset
        self._cur_item = None

    def wxcommand_add(self, _evt: wx.CommandEvent):
        db_input_dialog = DBInputDialog(self, 'Добавить', self._dialogs_ini, self.config.dialog_cfg, wx.Size(300, 200), True, True, self._logger)


        db_input_dialog.input_panel.add_property('employees', 'Сотрудники', BasicCheckListWithFilter, False, style=wx.LB_SORT)
        db_input_dialog.input_panel.set_property_size('employees', -1, -1)
        db_input_dialog.input_panel.set_property('employees', None, self.dataset.employees_cb_values)

        db_input_dialog.input_panel.add_property('train_type', 'Типы обучений', BasicCheckListWithFilter, False, style=wx.LB_SORT)
        db_input_dialog.input_panel.set_property_size('train_type', -1, -1)
        db_input_dialog.input_panel.set_property('train_type', None, self.dataset.train_types_cb_values)



        db_input_dialog.create_items()
        db_input_dialog.input_panel.set_property_param('start_date', 'third_state', False)
        db_input_dialog.input_panel.set_property_param('stop_date', 'third_state', False)
        db_input_dialog.input_panel.set_property_param('required', 'third_state', False)

        db_input_dialog.input_panel.set_focus()
        db_input_dialog.input_panel.property_value_changed_callback = self._on_dialog_val_changed
        # db_input_dialog.load_from_item(new_justification)
        # db_input_dialog.input_panel.property_value_changed_callback = self.input_box_val_changed
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
            sel_employees = db_input_dialog.input_panel.get_property('employees',False)
            sel_train_types = db_input_dialog.input_panel.get_property('train_type', False)



            if sel_employees and len(sel_employees)>0 and sel_train_types and len(sel_train_types)>0:
                progress = ProgressWnd(self.GetTopLevelParent(), 'Добавление', wx.Size(300, 100))
                notifier = progress.get_notifier()
                progress.CenterOnParent()
                progress.Show()
                notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Добавление', default_notify_level))

                seek_tuples = list(itertools.product(sel_employees, sel_train_types))

                tr_required_table = self.dataset.get_table(basicclasses.TrainingRequired)

                for i, seek_tuple in enumerate(seek_tuples):
                    notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject('Добавление', cur_val=i+1, max_val=len(seek_tuples), level=default_notify_level))
                    if seek_tuple not in self.dataset.lookup_required_trainings.keys():
                        new_row = basicclasses.TrainingRequired(tr_required_table)
                        new_row.new_guid()
                        new_row.active = True
                        new_row.employee = seek_tuple[0]
                        new_row.train_type = seek_tuple[1]
                        new_row.start_date = db_input_dialog.input_panel.get_property('start_date', False)
                        new_row.stop_date = db_input_dialog.input_panel.get_property('stop_date', False)
                        new_row.required = db_input_dialog.input_panel.get_property('required', False)
                        # noinspection PyTypeChecker
                        table: MainDBStorableTable = self.config.table
                        if not table.undelete_mark(new_row, app_settings.use_history, True):
                            table.add(new_row, app_settings.use_history, True)
                        else:
                            pass
                    else:
                        if db_input_dialog.input_panel.get_property('required', False) is True:
                            old_row = self.dataset.lookup_required_trainings[seek_tuple]
                            old_row.active = True
                            old_row.start_date = db_input_dialog.input_panel.get_property('start_date', False)
                            old_row.stop_date = db_input_dialog.input_panel.get_property('stop_date', False)
                            old_row.required = db_input_dialog.input_panel.get_property('required', False)
                            # noinspection PyTypeChecker
                            table: MainDBStorableTable = self.config.table
                            table.write(old_row, app_settings.use_history, True)
                        #cur_row: basicclasses.TrainingRequired = self.dataset.lookup_required_trainings[seek_tuple]
                        #cur_row.start_date = db_input_dialog.input_panel.get_property('start_date', False)
                        #cur_row.stop_date = db_input_dialog.input_panel.get_property('stop_date', False)
                        #cur_row.required = db_input_dialog.input_panel.get_property('required', False)
                        #self.config.table.write(cur_row, app_settings.use_history, True)
                self.grid.ClearSelection()
                notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject('Добавление', cur_val=len(seek_tuples), max_val=len(seek_tuples), level=default_notify_level))
                progress.Close()
            else:
                message_box(self, 'Ошибка', 'Не все данные введены. Добавление элементов не выполнено', wx.ICON_WARNING)

        db_input_dialog.save_state()
        self.toolbar.update_wxcommand_states()
        self._main_menu.update_wxcommand_states()


class RecommendedTrainingsPanel(BasicPanel, EventSubscriber):
    dataset: MainDatabase
    name: str
    old_text: str

    employees = []
    positions = []
    departments = []
    train_types = []

    def __init__(self, parent, name, dataset):
        self.name = name
        self.parent = parent
        self.dataset = dataset

        self.employees = []
        self.positions = []
        self.departments = []
        self.train_types = []
        self.old_text = ''

        BasicPanel.__init__(self, parent)
        EventSubscriber.__init__(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        name_label = wx.StaticText(self, label=name)
        f: wx.Font = name_label.GetFont()
        f.SetPointSize(app_settings.header_size)
        name_label.SetFont(f)
        sizer.Add(name_label, 0, wx.ALL, 1)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.apply_button = wx.Button(self,label='Применить')
        button_sizer.Add(self.apply_button, 0, wx.ALL, 5)
        self.apply_button.Bind(wx.EVT_BUTTON, self.apply_execute)

        help_button = wx.Button(self, label='Подсказка')
        button_sizer.Add(help_button, 0, wx.ALL, 5)
        help_button.Bind(wx.EVT_BUTTON, self.help_execute)


        sizer.Add(button_sizer, 0, wx.ALL, 1)

        #toolbar = BasicToolBar(self)
        #sizer.Add(toolbar,0, wx.ALL, 1)

        text_box = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_RICH2|wx.TE_DONTWRAP)
        text_box.Bind(wx.EVT_TEXT, self._on_text_changed)
        text_box.Bind(wx.EVT_CHAR, self._on_text_input)
        self.text_box = text_box
        self.default_style = wx.TextAttr()
        self.text_box.GetStyle(0,self.default_style)

        sizer.Add(text_box, 1, wx.ALL | wx.EXPAND, 1)

        self.SetSizer(sizer)
        self.dataset = dataset




    def _update_text_style(self):
        frozen = self.text_box.IsFrozen()
        if not frozen:
            self.text_box.Freeze()
        text_content = self.text_box.GetValue()


        self.text_box.SetStyle(0, len(text_content), self.default_style)

        marked_positions = []
        # отметить комментарии

        comment_style = wx.TextAttr(self.default_style)
        comment_font: wx.Font = wx.Font(comment_style.GetFont())
        comment_font.SetWeight(wx.FONTWEIGHT_NORMAL)
        comment_font.SetStyle(wx.FONTSTYLE_NORMAL)
        comment_style.SetTextColour(wx.ColourDatabase().FindName("GRAY"))
        comment_style.SetFont(comment_font)

        section_style = wx.TextAttr(self.default_style)
        section_font: wx.Font = wx.Font(section_style.GetFont())
        section_font.SetWeight(wx.FONTWEIGHT_BOLD)
        section_font.SetStyle(wx.FONTSTYLE_NORMAL)
        section_style.SetTextColour(wx.ColourDatabase().FindName("BLUE"))
        section_style.SetFont(section_font)

        param_style = wx.TextAttr(self.default_style)
        param_font: wx.Font = wx.Font(param_style.GetFont())
        param_font.SetWeight(wx.FONTWEIGHT_BOLD)
        param_font.SetStyle(wx.FONTSTYLE_NORMAL)
        param_style.SetFont(param_font)


        correct_param_value_style = wx.TextAttr(self.default_style)
        correct_param_value_font: wx.Font = wx.Font(correct_param_value_style.GetFont())
        correct_param_value_font.SetWeight(wx.FONTWEIGHT_BOLD)
        correct_param_value_font.SetStyle(wx.FONTSTYLE_NORMAL)
        correct_param_value_style.SetFont(correct_param_value_font)
        correct_param_value_style.SetTextColour(wx.ColourDatabase().FindName("FOREST GREEN"))


        incorrect_param_value_style = wx.TextAttr(self.default_style)
        incorrect_param_value_font: wx.Font = wx.Font(correct_param_value_style.GetFont())
        incorrect_param_value_font.SetWeight(wx.FONTWEIGHT_BOLD)
        incorrect_param_value_font.SetStyle(wx.FONTSTYLE_NORMAL)
        incorrect_param_value_style.SetFont(incorrect_param_value_font)
        incorrect_param_value_style.SetTextColour(wx.ColourDatabase().FindName("RED"))

        remain_style = wx.TextAttr(self.default_style)
        remain_font: wx.Font = wx.Font(remain_style.GetFont())
        remain_font.SetWeight(wx.FONTWEIGHT_NORMAL)
        remain_font.SetStyle(wx.FONTSTYLE_NORMAL)
        remain_style.SetTextColour(wx.ColourDatabase().FindName("VIOLET RED"))
        remain_style.SetFont(remain_font)


        param_delimiter_style = wx.TextAttr(self.default_style)
        param_delimiter_style_font: wx.Font = wx.Font(param_delimiter_style.GetFont())
        param_delimiter_style_font.SetWeight(wx.FONTWEIGHT_BOLD)
        param_delimiter_style_font.SetStyle(wx.FONTSTYLE_NORMAL)
        param_delimiter_style.SetFont(param_delimiter_style_font)


        comments = self.dataset.recommendations.get_comments_positions(text_content)
        for start, stop in comments:
            self.text_box.SetStyle(start, stop, comment_style)
        marked_positions.extend(comments)

        sections = self.dataset.recommendations.get_sections_positions(text_content)
        for start, stop in sections:
            self.text_box.SetStyle(start, stop, section_style)
        marked_positions.extend(sections)

        params = self.dataset.recommendations.get_params_positions(text_content)
        for start, stop in params:
            self.text_box.SetStyle(start, stop, param_style)
        marked_positions.extend(params)

        param_values: Dict[str, Dict[str, List[Tuple[str, int, int]]]] = self.dataset.recommendations.get_param_values(text_content)
        for section_name, param_dict in param_values.items():
            for param_name, param_values_list in param_dict.items():
                for param_value, p_start, p_stop in param_values_list:
                    if self.dataset.recommendations.is_param_correct(param_name, param_value):
                        self.text_box.SetStyle(p_start, p_stop, correct_param_value_style)
                    else:
                        self.text_box.SetStyle(p_start, p_stop, incorrect_param_value_style)


        prev_start = 0
        marked_positions.sort(key=lambda b:b[0])
        for start, stop in marked_positions:
            if prev_start<start:
                self.text_box.SetStyle(prev_start, start, remain_style)
            prev_start = stop
        self.text_box.SetStyle(prev_start, len(text_content), remain_style)
        if not frozen:
            self.text_box.Thaw()

    def apply_execute(self, _evt: wx.CommandEvent):
        progress = ProgressWnd(self, 'Обработка', wx.Size(300, 100))
        progress.CenterOnParent()
        progress.Show()
        notifier = progress.get_notifier()

        text_content = self.text_box.GetValue()
        self.dataset.recommendations.save(text_content)
        self.dataset.recommendations.update_recommendations(notifier)
        self.apply_button.Enable(False)
        progress.Close()

    def help_execute(self, _evt: wx.CommandEvent):
        text_message = '# это комментарий\n'
        text_message += '[имя секции] - все правила должны быть оформлены секциями\n'
        text_message += 'сотрудники=Фамилия Имя Отчество Должность Представительство\n'
        text_message += 'должности=должность1|...\n'
        text_message += 'представительства=представительство1|...\n'
        text_message += 'обучения=обуч1|...\n'
        text_message += 'начало=дд.мм.гггг\n'
        text_message += 'окончание=дд.мм.гггг\n'
        text_message += 'только_указанные=да - если попадает под другие правила, другие правила не действуют\n'
        message_box(self,'Справка',text_message, wx.ICON_INFORMATION)


    @WxEvents.debounce(1, False)
    def _on_text_changed_debounce(self):
        busy = wx.IsBusy()
        if not busy:
            wx.BeginBusyCursor()

        text_content = self.text_box.GetValue()
        if text_content != self.old_text:
            self._update_text_style()
            self.old_text = text_content

        if not busy:
            wx.EndBusyCursor()


    def _on_text_changed(self, _evt: wx.CommandEvent):
        self._on_text_changed_debounce()
        self.apply_button.Enable(True)


    def _on_text_input(self, evt: wx.KeyEvent):
        self.show_helper_wnd()
        evt.Skip()


    def on_popup_item_clicked(self, event_type: EventType, event_object: EventObject, popup: wx.PopupTransientWindow, pstart, pend):
        ctrl : BasicList = event_object.obj
        if event_type == EventType.ITEM_CHANGED:
            insert_slice = ctrl.get_value()
            replacement_name = ctrl.get_name(insert_slice[0])
            original_text = self.text_box.GetValue()
            new_text = original_text[:pstart]+replacement_name+original_text[pend:]

            self.text_box.Freeze()
            self.text_box.SetValue(new_text)
            self._update_text_style()
            self.text_box.SetInsertionPoint(pstart+len(replacement_name))
            self.text_box.Thaw()
            popup.Dismiss()




    @WxEvents.debounce(1,False)
    def show_helper_wnd(self):
        text_content: str = self.text_box.GetValue()
        cursor_point = self.text_box.GetInsertionPoint()

        if len(text_content)>cursor_point:
            point: wx.Point = self.text_box.PositionToCoords(cursor_point)
            popup = BasicPopupWindow(self, True)
            txt_extent : wx.Size = self.text_box.GetTextExtent(text_content[cursor_point:cursor_point+1])

            param_values = self.dataset.recommendations.get_param_values(text_content)
            popup_values = {}
            popup_pstart = None
            popup_pend = None
            for section_name, params_dict in param_values.items():
                for param_name, params_list in param_values[section_name].items():
                    for param_val, pstart, pend in params_list:
                        if pstart<=cursor_point<=pend:
                            param_val = text_content[pstart:cursor_point]
                            if param_name == 'сотрудники':
                                for key in self.dataset.recommendations.employees.keys():
                                    if key.startswith(param_val) or not param_val:
                                        popup_values[key] = (pstart, pend)
                                        popup_pstart = pstart
                                        popup_pend = pend
                            elif param_name == 'должности':
                                for key in self.dataset.recommendations.positions.keys():
                                    if key.startswith(param_val) or not param_val:
                                        popup_values[key] = (pstart, pend)
                                        popup_pstart = pstart
                                        popup_pend = pend
                            elif param_name == 'представительства':
                                for key in self.dataset.recommendations.departments.keys():
                                    if key.startswith(param_val) or not param_val:
                                        popup_values[key] = (pstart, pend)
                                        popup_pstart = pstart
                                        popup_pend = pend
                            elif param_name == 'обучения':
                                for key in self.dataset.recommendations.train_types.keys():
                                    if key.startswith(param_val) or not param_val:
                                        popup_values[key] = (pstart, pend)
                                        popup_pstart = pstart
                                        popup_pend = pend


            point = wx.Point(point.x, point.y+txt_extent.Height)
            point = self.text_box.ClientToScreen(point)
            popup.SetPosition(point)
            items_list = BasicList(popup._panel)
            items_list.register_callback(self.on_popup_item_clicked, popup, popup_pstart, popup_pend)
            #items_list.SetMinSize(wx.Size(100,100))
            avail_values = []
            for key,val in popup_values.items():
                avail_values.append((key, key))
            items_list.set_available_values(avail_values)
            popup.add_control(items_list)
            if avail_values:
                popup.Popup()

    def init_panel(self, _ini_file: configparser.ConfigParser()):
        cfg = self.dataset.get_config('recommendations')
        if cfg:
            self.text_box.SetValue(cfg)
            self.old_text = cfg
        self.dataset.recommendations.register_listener(self)
        self._update_text_style()
        self.apply_button.Enable(False)


    def deinit_panel(self):
        self.dataset.recommendations.unregister_listener(self)
        return configparser.ConfigParser()


    def on_notify(self, event_type: EventType, event_object: EventObject):
        self._update_text_style()

