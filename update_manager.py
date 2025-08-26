import uuid
from typing import Dict, Any, List, Tuple, Callable, Optional


from basic import Logger, EventPublisher, EventProgressObject, EventType
from gui_widgets import BasicStatusBar

class MainWindowStatusBar:
    _status_bar: BasicStatusBar
    def __init__(self, status_bar: BasicStatusBar):
        self._status_bar = status_bar


    def init(self):
        self._status_bar.set_panel_width(1, 0)  # пустой статус
        self._status_bar.set_panel_text('', 1)  # имя файла БД
        self._status_bar.fit_panel(1)
        self._status_bar.set_panel_width(32, 2)  # статус обновления графики
        self._status_bar.set_panel_width(150, 3)  # выбрано записей в таблица

        self._status_bar.set_panel_text(' ', 4)  # статус обновления файловой системы/связь с сервером
        self._status_bar.set_panel_width(32, 4)
        self._status_bar.set_panel_text(' ', 5)  # пока не определен
        self._status_bar.set_panel_width(16, 5)


    def show_current_file_name(self, file_name: str):
        self._status_bar.set_panel_text(f'{file_name}',1)
        self._status_bar.fit_panel(1)

    def show_selected_rows(self, sel_count: int):
        if sel_count:
            self._status_bar.set_panel_text(f'Выбрано {sel_count} эл.',3)
            self._status_bar.fit_panel(3)
        else:
            self._status_bar.set_panel_text(f'', 3)


    def show_update_manager_status(self, items: int):
        if items>0:
            self._status_bar.set_panel_bitmap('update',4)
            self._status_bar.set_panel_bitmap_hint(f'Осталось {items} эл.',4)
        else:
            self._status_bar.set_panel_bitmap(None, 4)
            self._status_bar.set_panel_bitmap_hint(f'', 4)

class UpdateManager:
    _need_update: bool
    _logger: Logger
    _tasks: Dict[uuid.UUID, Tuple[Callable, Any, Any, Any, Any]]
    _tasks_guids: List[uuid.UUID]
    _tasks_parent: Dict[Any, List[uuid.UUID]]
    _tasks_groups: Dict[Any, List[uuid.UUID]]
    _notifier: Optional[EventPublisher]
    _active_task_parent: Any
    _status_manager: MainWindowStatusBar
    #_parent_wnd: Union[wx.Frame, wx.Window, wx.Control]

    def __init__(self, logger: Logger, status_manager: MainWindowStatusBar): #, parent_wnd: Union[wx.Frame, wx.Window, wx.Control]):
        self._logger = logger
        self._tasks = {}
        self._tasks_parent  = {}
        self._tasks_groups = {}
        self._need_update = False
        self._tasks_guids = []
        self._active_task_parent = None
        self._status_manager = status_manager


    def stop(self):
        self._tasks.clear()
        self._tasks_guids.clear()
        self._tasks_parent.clear()
        self._tasks_groups.clear()

    def set_active_task_parent(self, parent: Any):
        self._active_task_parent = parent
        if parent in self._tasks_parent.keys():
            task_ids = list(self._tasks_parent[parent])
            if self._notifier:
                self._notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject(msg=f'Обновление', cur_val=0, max_val=len(task_ids)))
            for i, task_id in enumerate(task_ids):
                if self._notifier:
                    self._notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(msg=f'Обновление', cur_val=i+1, max_val=len(task_ids)))
                self.execute_task(task_id)
            if self._notifier:
                self._notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject(msg=f'Обновление', cur_val=len(task_ids), max_val=len(task_ids)))



    def add_task(self, task_parent: Any, task_group:int,  callable_func: Callable, *args, **kwargs):
        new_uuid = uuid.uuid4()
        self._tasks[new_uuid] = (callable_func, args, kwargs, task_parent, task_group)
        if task_parent not in self._tasks_parent.keys():
            self._tasks_parent[task_parent] = []
        self._tasks_parent[task_parent].append(new_uuid)
        if task_group not in self._tasks_groups.keys():
            self._tasks_groups[task_group] = []
        self._tasks_groups[task_group].append(new_uuid)
        self._tasks_guids.append(new_uuid)
        self._need_update = True
        if task_parent == self._active_task_parent:
            self.execute_task(new_uuid)
        else:
            self._status_manager.show_update_manager_status(len(self._tasks_guids))

    def execute_task(self, task_id: uuid.UUID):
        if task_id in self._tasks.keys():
            func = self._tasks[task_id][0]
            args = self._tasks[task_id][1]
            kwargs = self._tasks[task_id][2]
            task_parent = self._tasks[task_id][3]
            task_group = self._tasks[task_id][4]
            if args and kwargs:
                func(*args, **kwargs)
            elif args:
                func(*args)
            elif kwargs:
                func(**kwargs)
            else:
                func()
            del self._tasks[task_id]
            self._tasks_guids.remove(task_id)
            self._tasks_parent[task_parent].remove(task_id)
            self._tasks_groups[task_group].remove(task_id)
            if len(self._tasks_parent[task_parent])==0:
                del self._tasks_parent[task_parent]
            if len(self._tasks_groups[task_group])==0:
                del self._tasks_groups[task_group]
            if len(self._tasks)==0:
                self._need_update = False
            self._status_manager.show_update_manager_status(len(self._tasks_guids))

    def clear(self):
        self._tasks.clear()
        self._tasks_groups.clear()
        self._tasks_parent.clear()
        self._tasks_guids.clear()

    @property
    def need_update(self):
        """требуется ли обновление"""
        return self._need_update

    def set_notifier(self, notifier: Optional[EventPublisher]):
        self._notifier = notifier

    def get_notifier(self):
        return self._notifier

    def update(self):
        if len(self._tasks_guids)>0:
            guid = self._tasks_guids[0]
            self.execute_task(guid)
        else:
            self._need_update = False


