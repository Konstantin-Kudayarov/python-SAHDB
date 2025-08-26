import configparser
import datetime
import itertools

import os
import re
import shutil
import uuid
from enum import IntEnum
from typing import Optional, List, Union, Dict, Tuple, Any, Type

import basic
from basic import normalize_str_to_path, config_parser_to_string, config_parser_from_string, EventProgressObject


from db_data_adapter import DBStorableRow, DBStorableDataset, MSAccessAdapter, SQLiteAdapter, DBStorableTable
from basic import Logger, XMLStorable, get_run_path, EventType, EventPublisher, EventObject, EventSubscriber
from db_data_adapter import PropertyType, DBFindRule




class ImportEmployeesConfig(XMLStorable):
    """Порядок сортировки строк"""
    position_relations: Dict[str, str]
    department_relations: Dict[str, str]
    employees_relations: Dict[str, str]
    ignore_departments: List[str]
    not_ignore: List[str]
    fields: Dict[int, int]
    offset: int

    def __init__(self):
        XMLStorable.__init__(self)
        self.department_relations = {   'Представительство в г. Бузулук':'БЗ',
                                        'Представительство в г. Ноябрьск':'НО',
                                        'Представительство в г. Нефтеюганск':'НФ',
                                        'Представительство в г. Иркутск':'ИР',
                                        'Представительство в г. Нижневартовск': 'НО',
                                        'Служба исполнительного директора, Представительство в г.Нижневартовск': 'НВ',
                                        'Управление продаж, Представительство в г. Нефтеюганск':'НФ',
                                        'Управление по охране труда, Служба охраны труда, Представительство в г. Нижневартовск': 'НВ',
                                        'Управление по охране труда, Представительство в г. Бузулук': 'БЗ'
                                   }
        self.position_relations = {'Инженер':'Инж.',
                                   'Главный инженер':'Гл.инж.',
                                   'Ведущий технолог':'Вед.технолог',
                                   'Ведущий инженер':'Вед.инж.',
                                   'Старший инженер': 'Ст.инж.',
                                   'Ведущий инженер-технолог': 'Вед.инж.-технолог',

                                   'Директор Представительства':'Дир.предс-ва',
                                   'Менеджер':'Менеджер',
                                   'Заместитель главного инженера':'Зам. гл. инж.',
                                   'Заместитель директора представительства':'Зам. дир. предс-ва',

                                   'Руководитель производственно-диспетчерского сопровождения': '',
                                   'Контрактный инженер': 'Контр. инж.',
                                   'Старший специалист': 'Ст. специалист службы ОТ',
                                   'Начальник управления':'Нач. упр-я по ОТ',
                                   'Кладовщик':'Кладовщик',
                                   'Заместитель генерального директора по региональному развитию':'',
                                   'Грузчик': 'Грузчик',
                                   'Руководитель проекта': 'Руководитель проекта'

                                   }
        self.ignore_departments = []
        self.not_ignore = []

        self.employees_relations = {}
        self.fields = {0: 2, 1: 3, 2: 4}
        self.offset = 2


class Config(DBStorableRow):
    config_content: str
    config_type: str
    config_name: str
    config_type_name: str
    config_file: bool

class Person(DBStorableRow):
    """Личность"""
    last_name: str
    """Фамилия"""
    first_name: str
    """Имя"""
    middle_name: str
    """Отчество"""
    birth_date: datetime.date
    """Дата рождения"""
    birth_place: str
    """Место рождения"""

    passport_series: str
    """Паспорт: серия"""
    passport_number: str
    """Паспорт: номер"""
    passport_issued: str
    """Паспорт: кем выдан"""
    passport_issued_date: datetime.date
    """Паспорт: дата выдачи"""
    passport_valid_till_date: datetime.date
    """Паспорт: срок действия"""
    passport_issued_code: str
    """Паспорт: код подразделения"""

    living_place: str
    """Место проживания"""

    ssn_number: str
    """СНИЛ: номер"""
    ssn_issued_date: datetime.date
    """СНИЛС: дата выдачи"""

    taxnumber_number: str
    """ИНН: номер"""
    taxnumber_issued_date: datetime.date
    """ИНН: дата выдачи"""

    phones: List[str]
    """телефоны"""
    emails: List[str]
    """е-мэйлы"""

    user_name: str
    """Имя пользователя"""

    active: bool
    """Персона активна"""

    _tmp_index: str
    @property
    def full_name(self):
        """Фамилия Имя Отчество"""
        return f'{self.last_name if self.last_name else ""}{' '+self.first_name if self.first_name else ""}{' '+self.middle_name if self.middle_name else ""}'

    @property
    def full_name_with_date(self):
        """Фамилия Имя Отчество Дата рождения"""
        if not hasattr(self, '_tmp_index'):
            self._tmp_index = datetime.datetime.now().strftime("%S.%f")[:-3]
        return f'{self.full_name} {self.birth_date.strftime(app_settings.date_format) if self.birth_date else self._tmp_index}'

    #@property
    #def short_name(self):
    #    return f'{self.last_name if self.last_name else ""}{' '+self.first_name[0]+'.' if self.first_name else ""}{' '+self.middle_name[0]+'.' if self.middle_name else ""}'

    @property
    def node_name(self)->str:
        return f'{normalize_str_to_path(self.last_name) if self.last_name else ""}{' '+normalize_str_to_path(self.first_name) if self.first_name else ""}{' '+normalize_str_to_path(self.middle_name[0]) if self.middle_name else ""}'
class Department(DBStorableRow):
    """Представительство"""
    name: str
    """Наименование"""
    code: str
    """Код"""
    city: str
    """Город"""
    active: bool
    """Представительство активно"""

    @property
    def node_name(self):
        return normalize_str_to_path(self.name)
class CompanyPrefixes(IntEnum):
    UNKNOWN = 0
    """Неизвестно"""
    LLC = 1
    """Общество с ограниченной ответственностью"""
    CJSC = 2
    """Закрытое акционерное общество"""
    JSC = 3
    """Акционерное общество"""

    @property
    def short_name(self):
        if self == CompanyPrefixes.UNKNOWN:
            return 'Неизвестно'
        elif self == CompanyPrefixes.LLC:
            return 'ООО'
        elif self == CompanyPrefixes.CJSC:
            return 'ЗАО'
        elif self == CompanyPrefixes.JSC:
            return 'АО'

    @property
    def full_name(self):
        if self == CompanyPrefixes.UNKNOWN:
            return 'Неизвестно'
        elif self == CompanyPrefixes.LLC:
            return 'Общество с ограниченной ответственностью'
        elif self == CompanyPrefixes.CJSC:
            return 'Закрытое акционерное общество'
        elif self == CompanyPrefixes.JSC:
            return 'Акционерное общество'

class Company(DBStorableRow):
    """Наименование организации"""
    prefix: CompanyPrefixes
    """Префикс организации"""
    name: str
    """Наименование организации"""
    short_name: str
    """Краткое наименование организации"""
    active: bool
    """Организация активна"""
    @property
    def company_short_name(self):
        return f'{self.prefix.short_name} \"{self.short_name}\"'

    @property
    def node_name(self):
        return normalize_str_to_path(self.company_short_name)


class Position(DBStorableRow):
    """Должность"""
    name: str
    """Наименование"""
    short_name: str
    """Короткое наименование"""
    description: str
    """Комментарий"""

    active: bool
    """Должность активна"""

# region Обучения

class PersonalDocType(IntEnum):
    PASSPORT = 100
    """Паспорт"""
    SSN = 101
    """СНИЛС"""
    TAX_NUMBER = 102
    """ИНН"""
    SIGN = 103
    """подпись"""
    DIPLOMA = 104
    """диплом"""
    PHOTO = 105
    """фотография"""
    OTHER = 200
    """другое"""

    @property
    def short_name(self):
        if self == PersonalDocType.PASSPORT:
            return 'Пасп.'
        elif self == PersonalDocType.SSN:
            return 'СНИЛС'
        elif self == PersonalDocType.TAX_NUMBER:
            return 'ИНН'
        elif self == PersonalDocType.SIGN:
            return 'Подп.'
        elif self == PersonalDocType.DIPLOMA:
            return 'Дипл.'
        elif self == PersonalDocType.PHOTO:
            return 'Фото.'
        elif self == PersonalDocType.OTHER:
            return 'Др.'


    @property
    def full_name(self):
        if self == PersonalDocType.PASSPORT:
            return 'Паспорт'
        elif self == PersonalDocType.SSN:
            return 'СНИЛС'
        elif self == PersonalDocType.TAX_NUMBER:
            return 'ИНН'
        elif self == PersonalDocType.SIGN:
            return 'Подпись'
        elif self == PersonalDocType.DIPLOMA:
            return 'Диплом'
        elif self == PersonalDocType.PHOTO:
            return 'Фото'
        elif self == PersonalDocType.OTHER:
            return 'Другое'


class DocumentType(IntEnum):
    UNKNOWN = 0
    """Неизвестно"""
    LICENSE = 1
    """Удостоверение"""
    PROTOCOL = 2
    """Протокол"""
    ENQUIRY = 3
    """Справка"""
    CERTIFICATE = 4
    """Сертификат"""
    JOURNAL_ENTRY = 6
    """Запись в журнале"""
    DIPLOMA = 7
    """Диплом"""

    @property
    def short_name(self):
        if self == DocumentType.UNKNOWN:
            return 'Неизв.'
        elif self == DocumentType.LICENSE:
            return 'Удост.'
        elif self == DocumentType.PROTOCOL:
            return 'Прот.'
        elif self == DocumentType.ENQUIRY:
            return 'Спр.'
        elif self == DocumentType.CERTIFICATE:
            return 'Серт.'
        elif self == DocumentType.DIPLOMA:
            return 'Дип.'
        elif self == DocumentType.JOURNAL_ENTRY:
            return 'Журн.'


    @property
    def full_name(self):
        if self == DocumentType.UNKNOWN:
            return 'Неизвестно'
        elif self == DocumentType.LICENSE:
            return 'Удостоверение'
        elif self == DocumentType.PROTOCOL:
            return 'Протокол'
        elif self == DocumentType.ENQUIRY:
            return 'Справка'
        elif self == DocumentType.CERTIFICATE:
            return 'Сертификат'
        elif self == DocumentType.DIPLOMA:
            return 'Диплом'
        elif self == DocumentType.JOURNAL_ENTRY:
            return 'Запись в журнале'

    @property
    def node_name(self):
        return normalize_str_to_path(self.full_name)

class Employee(DBStorableRow):
    """Сотрудник"""
    person: Person
    """Личность"""
    payroll_number: str
    """Табельный номер"""
    department: Department
    """Представительство"""
    company: Company
    """Организация"""
    position: Position
    """Должность"""
    hire_date: datetime.date
    """Дата трудоустройства"""
    fire_date: datetime.date
    """Дата увольнения"""
    fire_reason: str
    """Причина увольнения"""
    active: bool
    """Сотрудник активен"""

    #@property
    #def name_folder(self):
    #    return f'{os.path.join(normalize_str_to_path(self.company.company_short_name), normalize_str_to_path(self.department.name), self.person.name_folder)}'

    @property
    def node_name(self):
        if self.person:
            return self.person.node_name

    @property
    def employee_string(self):
        return f'{self.person.full_name_with_date if self.person else "неизвестный сотрудник"} {self.position.short_name if self.position else "неизвестная должность"} ({self.department.code if self.department else "неизв.представительство"})'


class TrainType(DBStorableRow):
    """Тип обучения"""
    name: str
    """Наименование"""

    short_name: str
    """Короткое наименование"""

    doc_types: List[DocumentType]
    """Виды документов"""

    valid_period_year: float
    """Срок действия"""

    train_period_hours: int
    """Длительность обучения"""
    active: bool
    """Тип обучения активен"""

class Training(DBStorableRow):
    """Документ"""
    doc_type: DocumentType
    """Вид документа"""
    train_type: TrainType
    """Тип обучения"""
    number: str
    """Номер документа"""
    issued_by: Company
    """Выдан"""
    issued_date: datetime.date
    """Дата выдачи"""
    valid_till: datetime.date
    """Действителен до даты"""
    employee: Employee
    """Сотрудник"""
    doc_file_hash: str
    """хэш файла"""
    doc_file_exists: bool
    """файл существует по указанному пути"""
    doc_file_extension: str
    """расширение файла"""
    active: bool
    """Обучение активно"""
    name_path: str
    """путь к элементу в дереве \Бузулук\Иванов\Удостоверение\Удостоверение 12.pdf"""

    #@property
    #def object_hash(self):
    #    src_str = f'{self.doc_type.name if self.doc_type else ""}{self.train_type.guid if self.train_type else ""}{self.number if self.number else ""}{self.issued_date.strftime("%d.%m.%Y") if self.issued_date else ""}{self.issued_by.guid if self.issued_by else ""}'
    #    return str_to_hash(src_str,512)

    @property
    def training_name(self):
        """имя элемента: ОТ Удостоверение №1 от 01.01.2025 имя компании выдавшей документ"""
        return f'{self.train_type.short_name if self.train_type else ""}{" "+self.doc_type.full_name if self.doc_type else ""}{" " + self.number if self.number else ""}{" " + self.issued_date.strftime(app_settings.date_format) if self.issued_date else ""}{" " + self.issued_by.company_short_name if self.issued_by else ""}'

        #return f'{self.doc_type.full_name if self.doc_type else ""}{" "+self.employee.person.full_name_with_date}{" "+self.employee.position.short_name}{" ("+self.employee.department.code+")"}{" "+self.number if self.number else ""}{" "+self.issued_date.strftime(app_settings.date_format) if self.issued_date else ""}{" "+self.issued_by.company_short_name if self.issued_by else ""}'

    @property
    def node_name(self):
        """умя файла короткое: Удостоверение ОТ Иванов Вед.инж."""
        return normalize_str_to_path(f'{self.doc_type.node_name}{" "+self.train_type.short_name if self.train_type else ""}{" "+self.employee.person.node_name if self.employee.person else ""}{" "+self.employee.position.short_name}') #{" ("+str(index)+")" if index is not None else ""}')

    @property
    def node_common_name(self):
        return normalize_str_to_path(f'{self.doc_type.full_name if self.doc_type else ""}{" "+self.train_type.short_name if self.train_type else ""}{" "+self.number if self.number else ""}{" "+self.issued_date.strftime(app_settings.date_format) if self.issued_date else ""}{" "+self.issued_by.company_short_name if self.issued_by else ""}') #{" ("+str(index)+")" if index is not None else ""}')


    #@property
    #def name_folder(self):
    #    return os.path.join(self.employee.name_folder,normalize_str_to_path(self.doc_type.full_name),normalize_str_to_path(self.training_name))

    #@property
    #def common_name_folder(self):
    #    return os.path.join(normalize_str_to_path(self.employee.company.company_short_name), normalize_str_to_path(self.doc_type.full_name), normalize_str_to_path(f'{self.doc_type.full_name if self.doc_type else ""}{" "+self.number if self.number else ""}{" "+self.issued_date.strftime(app_settings.date_format) if self.issued_date else ""}'))

class PersonallDocument(DBStorableRow):
    person : Person
    """Личность"""
    doc_type: PersonalDocType
    """тип документа"""
    doc_name: str
    """Наименование документа"""
    doc_info: str
    """Информация о документе """
    issued_date: datetime.date
    """дата выдачи"""
    name_path: str
    """путь к элементу в дереве"""
    doc_file_hash: str
    """хэш файла"""
    doc_file_exists: bool
    """файл существует по указанному пути"""
    active: bool
    """Документ активен"""

    @property
    def node_name(self):
        if self.doc_name:
            return  f'{normalize_str_to_path(self.doc_type.full_name)} {normalize_str_to_path(self.doc_name)} {normalize_str_to_path(self.person.full_name_with_date)}'
        else:
            return f'{normalize_str_to_path(self.doc_type.full_name)} {normalize_str_to_path(self.person.full_name_with_date)}'


class TrainingRequired(DBStorableRow):
    """Необходимость обучения"""
    employee: Optional[Employee]
    """Сотрудник"""
    train_type: Optional[TrainType]
    """Тип обучения"""
    start_date: Optional[datetime.date]
    """Дата действия требования"""
    stop_date: Optional[datetime.date]
    """Дата действия требования"""
    required: bool
    """Требуется обучение"""
    active: bool
    """Необходимость обучения активно"""

    @property
    def is_required_today(self):
        if self.start_date and self.start_date>datetime.date.today():
            return False
        if self.stop_date and self.stop_date<datetime.date.today():
            return False
        return self.required




# endregion

# region Заявки на обучение

class TrainingRequest(DBStorableRow):
    """Заявка на обучение"""
    employee: Optional[Employee]
    """Сотрудник"""
    train_type: Optional[TrainType]
    """Тип обучения"""
    doc_type: Optional[DocumentType]
    """Вид документа"""

    request_date: Optional[datetime.date]
    """Дата заявки"""
    complete_date: Optional[datetime.date]
    """Дата исполнения"""
    active: bool
    """Заявка активна"""
    @property
    def requested(self):
        if hasattr(self,'request_date'):
            return self.request_date is not None
        return False

    @property
    def completed(self):
        if hasattr(self, 'complete_date'):
            return self.complete_date is not None
        return False


# endregion


class WorkspaceSettings(XMLStorable):
    db_files_path: str
    train_request_path: str
    config_path: str
    export_doc_path: str
    import_employees_file_name: str

    def __init__(self):
        XMLStorable.__init__(self)
        self.db_files_path = ''
        self.train_request_path = ''
        self.config_path = ''
        self.export_doc_path = ''
        self.import_employees_file_name = ''

class ActiveTraining(DBStorableRow):
    employee: Employee
    train_type: TrainType
    start_date: Optional[datetime.date]
    stop_date: Optional[datetime.date]
    trainings: List[Training]
    required: bool
    requested: bool

class MainDBStorableTable(DBStorableTable):
    def undelete_mark(self, item: DBStorableRow, use_history: bool, save_to_db: bool)->bool:
        if type(item) == TrainingRequired:
            item: TrainingRequired
            filter_rules = [('employee', item.employee.guid, DBFindRule.EQUAL),
                            ('train_type', item.train_type.guid, DBFindRule.EQUAL)]
            values: List[TrainingRequired] = self.read_from_db(filter_rules, None, add_to_table=False)
            if len(values)==1:
                write_item = values[0]
                item.set_guid(write_item.guid)
                self.add(item, False, False)
                item.active = True
                self.write(item,use_history, save_to_db)
                return True
            elif len(values)>1:
                for val in values:
                    self.add(val, False, False)
                    self.delete(val, False, True)
        return False



    def delete_mark(self, item: DBStorableRow, use_history: bool, save_to_db: bool) -> bool:
        if hasattr(item, 'active'):
            setattr(item, 'active', False)
        answer = self.write(item, use_history, save_to_db)
        if answer:
            self.delete(item,False,False)
        return answer




class MainDatabase(DBStorableDataset):
    _tables: Dict[Type[DBStorableRow], MainDBStorableTable]

    predefined_table_types = [Config,
                              Person,
                              PersonallDocument,
                              Department,
                              Company,
                              Position,
                              Employee,
                              TrainType,
                              TrainingRequired,
                              Training,
                              TrainingRequest
                              ]

    _configs: Dict[str, Tuple[uuid.UUID, Union[XMLStorable, configparser.ConfigParser, str]]]

    _db_adapter: Union[MSAccessAdapter, SQLiteAdapter]
    _inited: bool
    _logger: Logger
    name: str
    recommendations: 'RecommendationClass'

    company_prefixes_cb_values: List[Tuple[str, Any]] = []
    person_cb_values: List[Tuple[str, Any]] = []
    position_cb_values: List[Tuple[str, Any]] = []
    department_cb_values: List[Tuple[str, Any]] = []
    company_cb_values: List[Tuple[str, Any]] = []
    parent_types: Dict[Type[DBStorableRow], List[Tuple[Type[DBStorableRow], str]]]
    doc_types_cb_values: List[Tuple[str, Any]] = []
    employees_cb_values: List[Tuple[str, Any]] = []
    """"""
    train_types_cb_values: List[Tuple[str, Any]] = []
    personall_doc_types_cb_values: List[Tuple[str, Any]] = []
    use_base64_for_configs: bool = False


    lookup_required_trainings: Dict[Tuple[Employee, TrainType], TrainingRequired] = {}
    lookup_train_requests: Dict[Tuple[Employee, TrainType, DocumentType], List[TrainingRequest]] = {}
    lookup_active_trainings: Dict[Tuple[Employee, TrainType], ActiveTraining] = {}

    lookup_training_paths: Dict[str, List[Training]] = {}
    """Бузулук\Иванов\Удостоверение ОТ Иванов Вед.инж"""
    #str = name_path (Бузулук\Иванов Иван И\Удостоверение\Удостоверение 1.pdf) или без pdf
    lookup_training_names: Dict[str, List[Training]] = {}


    lookup_file_hashes: Dict[str, List[Training]] = {}

    workspace_settings: WorkspaceSettings

    @property
    def inited(self):
        return self._inited

    _connected: bool
    @property
    def connected(self):
        return self._connected

    #active_trainings: ActiveTrainings


    def __init__(self, logger: Logger, db_type: str):
        self._logger = logger
        self._inited = False
        self._connected = False
        self._configs = {}
        DBStorableDataset.__init__(self, logger)
        if db_type == 'accdb':
            self._db_adapter = MSAccessAdapter(logger)
            self._inited = True
        elif db_type == 'db':
            self._db_adapter = SQLiteAdapter(logger)
            self._inited = True
        else:
            self.logger.error(f'Неизвестный тип адаптера БД:{db_type}')
            self._inited = False

        if self._inited:
            for tt in self.predefined_table_types:
                if tt == Config:
                    table = self.new_table(tt, True, self._db_adapter, MainDBStorableTable)
                else:
                    table = self.new_table(tt, not app_settings.use_history, self._db_adapter, MainDBStorableTable)

                if not self.add_table(table):
                    self._inited = False
                    break
            # noinspection PyTypeChecker
            act_table = self.new_table(ActiveTraining,True, None)
            if not self.add_table(act_table):
                self._inited = False


        val: CompanyPrefixes
        self.company_prefixes_cb_values = []
        for val in CompanyPrefixes:
            if val != CompanyPrefixes.UNKNOWN:
                self.company_prefixes_cb_values.append((val.short_name, val))

        self.workspace_settings = WorkspaceSettings()
        # справочники для comboboxes
        self.person_cb_values = []
        self.department_cb_values = []
        self.position_cb_values = []
        self.company_cb_values = []
        self.employees_cb_values = []
        self.train_types_cb_values = []
        self.doc_types_cb_values = []
        self.personall_doc_types_cb_values = []

        # noinspection PyTypeChecker
        self.parent_types = {}


        # -------------------- конец справочников для comboboxes -------------

        # indexes быстрый доступ к объектам БД

        self.lookup_required_trainings = {}
        self.lookup_train_requests = {}

        self.lookup_active_trainings = {}


        self.lookup_training_paths = {}
        self.lookup_training_names = {}
        self.lookup_file_hashes = {}
        #self.lookup_personal_documents = {}


        # ----- end indexes быстрый доступ к объектам БД --------------



        for val in DocumentType:
            if val != DocumentType.UNKNOWN:
                self.doc_types_cb_values.append((val.full_name, val))

        for val in PersonalDocType:
            self.personall_doc_types_cb_values.append((val.full_name, val))

        all_tables = list(self.predefined_table_types)
        all_tables.append(ActiveTraining)

        for table_type in all_tables:
            for field_name, (prop_type, prop_class) in table_type.get_properties().items():
                if prop_type == PropertyType.CLASS_INSTANCE:
                    if prop_class not in self.parent_types.keys():
                        # noinspection PyTypeChecker
                        self.parent_types[prop_class] = []
                    # noinspection PyTypeChecker
                    self.parent_types[prop_class].append((table_type, field_name))


    def connect(self, main_db_filename: str):
        if os.path.exists(main_db_filename) and self.inited:
            self._db_adapter.connect(main_db_filename, 60, False)
            if self._db_adapter.connected:
                for table in self.get_tables(self._db_adapter):
                    if not self._db_adapter.check_table_structure(table):
                        self._logger.error(f'Структура БД повреждена')
                        self._connected = False
                        self._inited = False
                if not self._inited:
                    if self._db_adapter.connected:
                        self._db_adapter.disconnect()
                    return False



                self._connected = True

                self.name = os.path.split(main_db_filename)[1]
                return True
        return False

    def disconnect(self):
        if self.connected and self.inited:
            self.write_config('workspace_settings', self.workspace_settings, True, 0)
            self._db_adapter.disconnect()
            if not self._db_adapter.connected:
                self._connected = False
                return True
        return False


    def get_table(self, table_type: Type[DBStorableRow]) ->Optional[MainDBStorableTable]:
        return DBStorableDataset.get_table(self, table_type)

    # region Configs

    def get_config(self, name: str)->Union[XMLStorable, configparser.ConfigParser, None]:
        if self.connected:
            if name in self._configs.keys():
                return self._configs[name][1]
        return None

    def update_config(self, name: str):
        if name in self._configs.keys():
            if self._configs[name] in self.get_table(Config).get_items():
                self.get_table(Config).notify_listeners(EventType.ITEM_NEED_UPDATE,EventObject(self._configs[name]))



    def _set_config(self, name: str, config_type: str, config_str: str, guid: uuid.UUID, config_type_name: str):
        if config_type == 'ini':
            cfg = config_parser_from_string(config_str, self.use_base64_for_configs)
        elif config_type == 'xml':
            cfg: Optional[XMLStorable] = globals()[config_type_name]()
            #cfg = XMLStorable()
            cfg.load_from_str(config_str, self.use_base64_for_configs)
        elif config_type == 'txt':
            cfg: str
            cfg = config_str
        else:
            self._logger.error(f'{self} Неверный тип конфигурации {config_type} для {name}')
            cfg = None

        if cfg is not None:
            self._configs[name] = (guid, cfg)

    def write_config(self, name: str, config: Union[XMLStorable, configparser.ConfigParser, str, None], to_db: bool, basic_index: Optional[int])->bool:
        if self.connected:
            config_type_name = None
            if issubclass(type(config), XMLStorable):
                xml_cfg: XMLStorable = config
                config_str = xml_cfg.save_to_str(self.use_base64_for_configs)
                config_type = 'xml'
                config_type_name = type(xml_cfg).__name__
                config_file = not to_db
            elif issubclass(type(config), configparser.ConfigParser):
                ini_config: configparser.ConfigParser = config
                config_str = config_parser_to_string(ini_config, self.use_base64_for_configs)
                config_type = 'ini'
                config_file = not to_db
            elif type(config) == str:
                config_str = config
                config_type = 'txt'
                config_file = not to_db
            else:
                self._logger.error(f'{self} Неверный тип конфигурации {type(config)} для {name}')
                return False
            item_guid = None
            if name in self._configs.keys():
                item_guid = self._configs[name][0]
            row: Config
            if item_guid is not None:
                row = self.get_table(Config).get(item_guid) # noqa
            else:
                row = Config(self.get_table(Config))
            row.config_type = config_type
            if config_file:
                row.config_content = name+'.'+config_type #os.path.join(self.workspace_settings.config_path, name)+'.'+config_type
            else:
                row.config_content = config_str
            row.config_name = name
            row.config_type_name = config_type_name
            row.config_file = config_file
            self._configs[name] = (row.guid, config)
            if item_guid is None:
                row.new_guid(basic_index)
                self.get_table(Config).add(row,False,True)
            else:
                self.get_table(Config).write(row, False, True)
                    #row.write()
            if config_file:
                save_file = os.path.join(self.workspace_settings.config_path, name)+'.'+config_type
                if issubclass(type(config), XMLStorable):
                    config: XMLStorable
                    config.save_to_file(save_file)
                elif issubclass(type(config), configparser.ConfigParser):
                    config: configparser.ConfigParser
                    f = open(save_file,'w')
                    f.write(basic.config_parser_to_string(config, False))
                    f.close()
                elif type(config) == str:
                    f = open(save_file, 'w')
                    f.write(config)
                    f.close()

            return True

        return False

    # endregion

    def create(self, main_db_filename: str)->bool:
        self._logger.debug(f'Начат процесс создания {main_db_filename}')
        if not self.inited:
            self._logger.error(f'Невозможно создать, БД не инициализирована')
            return False
        if self.connected:
            self._logger.error(f'Невозможно создать, БД открыта')
            return False


        if not os.path.exists(main_db_filename):
            if not self._db_adapter.connect(main_db_filename, None, True):
                return False
            for table in self.get_tables(self._db_adapter):
                if table.table_type in self.predefined_table_types:
                    if not self._db_adapter.create_table(table):
                        self._logger.error(f'Ошибка создания таблицы, БД не создана')
                        self._db_adapter.disconnect()
                        self._inited = False
                        return False
                else:
                    self._logger.debug(f'{self} при создании таблицы {table.table_type} она пропущена, так как не находится в predefined_table_types')
            self._connected = True
            self.name = os.path.split(main_db_filename)[1]
            self._logger.debug(f'Завершен процесс создания {main_db_filename}')
            return True

        else:
            self._logger.error(f'Файл существует: {main_db_filename}')
        return False

    def read_tables_from_db(self, notifier: EventPublisher, active: bool = True):
        for table in self.get_tables(self._db_adapter):
            readed = False
            if active:
                if 'active' in table.table_type.get_properties().keys():
                    table.read_from_db([('active', True, DBFindRule.EQUAL)], notifier, [('_guid',True)])
                    readed = True
            if not readed:
                table.read_from_db([], notifier, [('_guid',True)])

        self.correct_structure()
        self.recommendations = RecommendationClass(self, self.logger)
        self.recommendations.update_recommendations(notifier)



    def correct_structure(self):
        pass
        #self._check_required_recommended(notifier, 1)

    def find_related_objects(self, src_obj: DBStorableRow)->List[Tuple[List[DBStorableRow], MainDBStorableTable]]:
        answer = []
        if type(src_obj) in self.parent_types.keys():
            for table_type, field_name in self.parent_types[type(src_obj)]:
                related_table: MainDBStorableTable = self.get_table(table_type)
                related_items = related_table.find_items([(field_name, src_obj, DBFindRule.EQUAL)])
                #if related_items and related_table.table_type not in [TrainingRequired, TrainingRecommended]:
                answer.append((related_items, related_table))
        return answer

    def find_related_object_recurse(self, src_obj: DBStorableRow, src_list: List):
        related:List[Tuple[List, MainDBStorableTable]] = self.find_related_objects(src_obj)
        if related:
            r_object: Tuple[List[DBStorableRow], MainDBStorableTable]
            for r_object in related:
                for r in r_object[0]:
                    src_list.append((r,r_object[1]))
                    self.find_related_object_recurse(r, src_list)


    def on_notify(self, event_type: EventType, event_object: EventObject):
        #print(f'on_notify {event_type.name} {event_object.obj}')
        EventSubscriber.on_notify(self, event_type, event_object)
        if event_type in [EventType.ITEM_ADDED, EventType.ITEM_CHANGED, EventType.ITEM_DELETED, EventType.ITEM_NEED_UPDATE]:
            obj = event_object.obj
            if type(obj) == Config:
                # noinspection PyTypeChecker
                cfg_row: Config = obj
                if event_type in [EventType.ITEM_ADDED, EventType.ITEM_NEED_UPDATE]:
                    if not cfg_row.config_file:
                        self._set_config(cfg_row.config_name, cfg_row.config_type, cfg_row.config_content, cfg_row.guid, cfg_row.config_type_name)
                        if cfg_row.config_name == 'workspace_settings':
                            self.workspace_settings = self.get_config('workspace_settings')

                    else:
                        cfg_filename = os.path.join(self.workspace_settings.config_path, cfg_row.config_content)
                        if os.path.exists(cfg_filename):
                            f = open(cfg_filename, 'r')
                            cfg_str = f.read()
                            f.close()
                            self._set_config(cfg_row.config_name, cfg_row.config_type, cfg_str, cfg_row.guid, cfg_row.config_type_name)
            #if event_type in [EventType.ITEM_ADDED, EventType.ITEM_CHANGED, EventType.ITEM_DELETED]:
            self._update_internal_references(event_type, event_object)  # обновим справочники
            self._update_dependencies_tables(event_type, event_object)  # обновим зависимые таблицы
            self._update_lookup_items(event_type, event_object)         # обновим индексированные объекты поиска
            self._update_structure(event_type, event_object)            # обновим структуру
        else:
            self.logger.error(f'{self} неизвестный тип события {event_type} {event_type.name} {event_object.obj}')
    def _update_internal_references(self, event_type: EventType, event_object: EventObject):
        obj = event_object.obj
        old_obj = event_object.old_obj
        if type(obj) in [Person, Position, Department, Company, TrainingRequired, Employee, TrainType]:
            current_list = None
            new_str = None
            old_str = None
            if type(obj) == Person:
                obj: Person
                old_obj: Person
                current_list = self.person_cb_values
                new_str = obj.full_name_with_date
                if old_obj:
                    old_str = old_obj.full_name_with_date
            elif type(obj) == Position:
                obj: Position
                old_obj: Position
                current_list = self.position_cb_values
                new_str = f'{obj.name}{" ("+obj.description+")" if obj.description else ""}'
                if old_obj:
                    old_str = f'{old_obj.name}{" ("+old_obj.description+")" if old_obj.description else ""}'
            elif type(obj) == Department:
                obj: Department
                old_obj: Department
                current_list = self.department_cb_values
                new_str = obj.name
                if old_obj:
                    old_str = old_obj.name
            elif type(obj) == Company:
                obj: Company
                old_obj: Company
                current_list = self.company_cb_values
                new_str = obj.company_short_name
                if old_obj:
                    old_str = old_obj.company_short_name
            elif type(obj) == Employee:
                obj: Employee
                old_obj: Employee
                current_list = self.employees_cb_values
                employee_fired = ''
                if obj.fire_date is not None:
                    employee_fired = ' |уволен|'
                employee_hired = ''
                if obj.hire_date is not None:
                    employee_hired = f' принят={obj.hire_date.strftime('%d.%m.%Y')}'
                new_str = f'{obj.person.full_name_with_date} {obj.position.short_name} ({obj.department.code}){employee_hired}{employee_fired}'
                if old_obj:
                    old_str = f'{old_obj.person.full_name_with_date} {old_obj.position.short_name} ({old_obj.department.code})'
            elif type(obj) == TrainType:
                obj: TrainType
                old_obj: TrainType
                current_list = self.train_types_cb_values
                new_str = f'{obj.short_name} ({obj.name})'
                if old_obj:
                    old_str = f'{old_obj.short_name} ({obj.name})'


            if current_list is not None:
                if event_type == EventType.ITEM_ADDED:
                    current_list.append((new_str, obj))
                elif event_type == EventType.ITEM_CHANGED:
                    tmp_old_val = old_str, obj
                    if tmp_old_val in current_list:
                        current_list.remove(tmp_old_val)
                    current_list.append((new_str, obj))
                elif event_type == EventType.ITEM_DELETED:
                    tmp_val = new_str, obj
                    if tmp_val in current_list:
                        current_list.remove(tmp_val)
                #else:
                #    self.logger.error(f'{self} _update_internal_references неизвестный тип события {event_type}')

    def _update_dependencies_tables(self, event_type: EventType, event_object: EventObject):
        obj = event_object.obj
        # обновим все таблицы, в которых содержится данный тип изменяемого объекта
        if type(obj) in self.parent_types and event_type in [EventType.ITEM_CHANGED, EventType.ITEM_NEED_UPDATE]:
            for related_items, related_table in self.find_related_objects(obj):
                for related_item in related_items:
                    related_table.notify_listeners(EventType.ITEM_NEED_UPDATE, EventObject(related_item))





    def _update_lookup_items(self, event_type: EventType, event_object: EventObject):
        # обновим lookup_required_trainings Employee, TrainType
        # обновим lookup_train_requests Employee,TrainType, (DocumentType - не изменяется)
        # обновим lookup_recommended_trainings Position, TrainType
        # обновим lookup_active_trainings Employee, TrainType
        # обновим lookup_training_names Employee, TrainType
        # обновим used_training_names
        # обновим lookup_file_hashed
        obj = event_object.obj
        if event_type in [EventType.ITEM_ADDED, EventType.ITEM_CHANGED, EventType.ITEM_DELETED]:
            if type(obj) == TrainingRequired:
                obj: TrainingRequired
                seek_tuple = (obj.employee, obj.train_type)
                if event_type == EventType.ITEM_ADDED:
                    if seek_tuple not in self.lookup_required_trainings.keys():
                        self.lookup_required_trainings[seek_tuple] = obj
                elif event_type == EventType.ITEM_DELETED:
                    if seek_tuple in self.lookup_required_trainings.keys():
                        del self.lookup_required_trainings[seek_tuple]
            elif type(obj) == ActiveTraining:
                obj: ActiveTraining
                seek_tuple = (obj.employee, obj.train_type)
                if event_type == EventType.ITEM_ADDED:
                    if seek_tuple not in self.lookup_active_trainings.keys():
                        self.lookup_active_trainings[seek_tuple] = obj
                elif event_type == EventType.ITEM_DELETED:
                    if seek_tuple in self.lookup_active_trainings.keys():
                        del self.lookup_active_trainings[seek_tuple]
            elif type(obj) == TrainingRequest:
                obj: TrainingRequest
                seek_tuple = (obj.employee, obj.train_type, obj.doc_type)
                if event_type == EventType.ITEM_ADDED:
                    if seek_tuple not in self.lookup_train_requests.keys():
                        self.lookup_train_requests[seek_tuple] = [obj]
                    else:
                        if obj not in self.lookup_train_requests[seek_tuple]:
                            self.lookup_train_requests[seek_tuple].append(obj)
                elif event_type == EventType.ITEM_DELETED:
                    if seek_tuple in self.lookup_train_requests.keys():
                        if obj in self.lookup_train_requests[seek_tuple]:
                            self.lookup_train_requests[seek_tuple].remove(obj)
                        if len(self.lookup_train_requests)==0:
                            del self.lookup_train_requests[seek_tuple]
            elif type(obj) == Training:
                obj: Training
                seek_tuple1 = obj.name_path
                if event_type == EventType.ITEM_ADDED:
                    if seek_tuple1 not in self.lookup_training_paths.keys():
                        self.lookup_training_paths[seek_tuple1] = [obj]
                    else:
                        if obj not in self.lookup_training_paths[seek_tuple1]:
                            self.lookup_training_paths[seek_tuple1].append(obj)
                elif event_type == EventType.ITEM_DELETED:
                    if seek_tuple1 in self.lookup_training_paths.keys():
                        if obj in self.lookup_training_paths[seek_tuple1]:
                            self.lookup_training_paths[seek_tuple1].remove(obj)
                        if len(self.lookup_training_paths) == 0:
                            del self.lookup_training_paths[seek_tuple1]
                elif event_type == EventType.ITEM_CHANGED:
                    old_obj: Training = event_object.old_obj
                    if old_obj.active and obj.active:
                        seek_tuple11 = old_obj.name_path
                        if seek_tuple1 != seek_tuple11:
                            if seek_tuple1 not in self.lookup_training_paths.keys():
                                self.lookup_training_paths[seek_tuple1] = []
                            self.lookup_training_paths[seek_tuple1].append(obj)

                            if seek_tuple11 in self.lookup_training_paths.keys():
                                if obj in self.lookup_training_paths[seek_tuple11]:
                                    self.lookup_training_paths[seek_tuple11].remove(obj)
                                else:
                                    self.logger.error(f'{self} повреждение lookup_training_paths. Eсть элемент который не должен существовать \"{seek_tuple11}\"')
                                if len(self.lookup_training_paths[seek_tuple11])==0:
                                    del self.lookup_training_paths[seek_tuple11]

                seek_tuple2 = obj.training_name
                if event_type == EventType.ITEM_ADDED:
                    if seek_tuple2 not in self.lookup_training_names.keys():
                        self.lookup_training_names[seek_tuple2] = [obj]
                    else:
                        if obj not in self.lookup_training_names[seek_tuple2]:
                            self.lookup_training_names[seek_tuple2].append(obj)
                elif event_type == EventType.ITEM_DELETED:
                    if seek_tuple2 in self.lookup_training_names.keys():
                        if obj in self.lookup_training_names[seek_tuple2]:
                            self.lookup_training_names[seek_tuple2].remove(obj)
                        if len(self.lookup_training_names) == 0:
                            del self.lookup_training_names[seek_tuple2]
                elif event_type == EventType.ITEM_CHANGED:
                    old_obj: Training = event_object.old_obj
                    if old_obj.active and obj.active:
                        seek_tuple21 = old_obj.training_name
                        if seek_tuple2 != seek_tuple21:
                            if seek_tuple2 not in self.lookup_training_names.keys():
                                self.lookup_training_names[seek_tuple2] = []
                            self.lookup_training_names[seek_tuple2].append(obj)

                            if seek_tuple21 in self.lookup_training_names.keys():
                                if obj in self.lookup_training_names[seek_tuple21]:
                                    self.lookup_training_names[seek_tuple21].remove(obj)
                                else:
                                    self.logger.error(f'{self} повреждение lookup_training_names. Eсть элемент который не должен существовать \"{seek_tuple21}\"')
                                if len(self.lookup_training_names[seek_tuple21])==0:
                                    del self.lookup_training_names[seek_tuple21]

                seek_tuple3 = obj.doc_file_hash
                if seek_tuple3:
                    if event_type == EventType.ITEM_ADDED:
                        if seek_tuple3 not in self.lookup_file_hashes.keys():
                            self.lookup_file_hashes[seek_tuple3] = [obj]
                        else:
                            if obj not in self.lookup_file_hashes[seek_tuple3]:
                                self.lookup_file_hashes[seek_tuple3].append(obj)
                    elif event_type == EventType.ITEM_DELETED:
                        if seek_tuple3 in self.lookup_file_hashes.keys():
                            if obj in self.lookup_file_hashes[seek_tuple3]:
                                self.lookup_file_hashes[seek_tuple3].remove(obj)
                            if len(self.lookup_file_hashes) == 0:
                                del self.lookup_file_hashes[seek_tuple3]
                    elif event_type == EventType.ITEM_CHANGED:
                        old_obj: Training = event_object.old_obj
                        if old_obj.active and obj.active:
                            seek_tuple31 = old_obj.doc_file_hash
                            if seek_tuple31 and seek_tuple3 != seek_tuple31:
                                if seek_tuple3 not in self.lookup_file_hashes.keys():
                                    self.lookup_file_hashes[seek_tuple3] = []
                                self.lookup_file_hashes[seek_tuple3].append(obj)

                                if seek_tuple31 in self.lookup_file_hashes.keys():
                                    if obj in self.lookup_file_hashes[seek_tuple31]:
                                        self.lookup_file_hashes[seek_tuple31].remove(obj)
                                    else:
                                        self.logger.error(f'{self} повреждение lookup_file_hashes. Eсть элемент который не должен существовать \"{seek_tuple31}\"')
                                    if len(self.lookup_file_hashes[seek_tuple31]) == 0:
                                        del self.lookup_file_hashes[seek_tuple31]




    def _update_structure(self, event_type: EventType, event_object: EventObject):
        obj: DBStorableRow = event_object.obj
        # lookup_recommended: Dict[Tuple[Position, TrainType], TrainingRecommended] = {}
        # lookup_required_trainings: Dict[Tuple[Employee, TrainType], TrainingRequired] = {}
        # lookup_active_trainings: Dict[Tuple[Employee, TrainType], ActiveTraining] = {}

        # region Обновление активных обучений
        if type(obj) in [Training, TrainingRequired, TrainingRequest]:
            # если обучение или требуемое обучение - обновим ActiveTraining
            if type(obj) == Training:
                obj: Training
                act_training: Optional[ActiveTraining] = None
                seek_tuple = (obj.employee, obj.train_type)
                if seek_tuple in self.lookup_active_trainings.keys():
                    act_training = self.lookup_active_trainings[seek_tuple]
                act_training_table = self.get_table(ActiveTraining)
                if event_type in [EventType.ITEM_ADDED, EventType.ITEM_CHANGED, EventType.ITEM_DELETED]:
                    if act_training is None:
                        if event_type != EventType.ITEM_DELETED:
                            act_training = ActiveTraining(act_training_table)
                            act_training.new_guid()
                            act_training.employee = obj.employee
                            act_training.train_type = obj.train_type
                            act_training.required = self.is_training_required_today(obj)
                            act_training.requested = self.is_training_requested(obj.employee, obj.train_type)
                            act_training.start_date = obj.issued_date
                            act_training.stop_date = obj.valid_till
                            act_training.trainings = [obj]
                            act_training_table.add(act_training,False, True)
                    else:
                        if event_type == EventType.ITEM_ADDED:
                            if obj not in act_training.trainings:
                                act_training.trainings.append(obj)

                        if event_type == EventType.ITEM_DELETED:
                            if obj in act_training.trainings:
                                act_training.trainings.remove(obj)

                        min_date = None
                        max_date = None
                        for training in act_training.trainings:
                            if min_date is None:
                                min_date = training.issued_date
                            if max_date is None:
                                max_date = training.valid_till
                            if training.issued_date is not None and min_date > training.issued_date:
                                min_date = training.issued_date
                            if training.valid_till is not None and max_date < training.valid_till:
                                max_date = training.valid_till
                        act_training.start_date = min_date
                        act_training.stop_date = max_date
                        act_training_table.write(act_training, False, True)
                        if not self.is_training_required_today(obj) and len(act_training.trainings) == 0:
                            act_training_table.delete(act_training, False, True)

            elif type(obj) == TrainingRequired:
                obj: TrainingRequired
                act_training: Optional[ActiveTraining] = None
                seek_tuple = (obj.employee, obj.train_type)
                if seek_tuple in self.lookup_active_trainings.keys():
                    act_training = self.lookup_active_trainings[seek_tuple]
                act_training_table = self.get_table(ActiveTraining)
                if event_type in [EventType.ITEM_ADDED, EventType.ITEM_CHANGED, EventType.ITEM_DELETED]:
                    if act_training is None and obj.is_required_today and event_type !=EventType.ITEM_DELETED:
                        act_training = ActiveTraining(act_training_table)
                        act_training.new_guid()
                        act_training.employee = obj.employee
                        act_training.train_type = obj.train_type
                        act_training.required = obj.is_required_today
                        act_training.requested = self.is_training_requested(obj.employee, obj.train_type)
                        act_training.start_date = None
                        act_training.stop_date = None
                        act_training.trainings = []
                        act_training_table.add(act_training,False, True)
                    elif act_training:
                        if event_type != EventType.ITEM_DELETED:
                            act_training.required = obj.is_required_today
                            act_training_table.write(act_training, False, True)
                        if not obj.is_required_today:
                            if len(act_training.trainings)==0:
                                act_training_table.delete(act_training, False, True)
            elif type(obj) == TrainingRequest:
                obj: TrainingRequest
                seek_tuple = obj.employee, obj.train_type
                act_training_table = self.get_table(ActiveTraining)
                if seek_tuple in self.lookup_active_trainings.keys():
                    item = self.lookup_active_trainings[seek_tuple]
                    item.requested = obj.requested and not obj.completed
                    act_training_table.write(item,False, True)


        # endregion




        # region Обновление требуемых обучений
        if type(obj) == TrainingRequired and not obj.table.table_loading:
            # если обучение не требуется и не рекомендуется, его можно удалить
            obj: TrainingRequired
            if event_type in [EventType.ITEM_CHANGED, EventType.ITEM_NEED_UPDATE]:
                if not obj.required:
                    if not self.is_recommended(obj.employee, obj.train_type) and obj.active:
                        required_table = self.get_table(TrainingRequired)
                        required_table.delete_mark(obj, app_settings.use_history, True)

        # endregion

        if type(obj) in [Department, Position, Employee, TrainType] and not obj.table.table_loading:
            if event_type in [EventType.ITEM_ADDED, EventType.ITEM_CHANGED, EventType.ITEM_DELETED]:
                self.recommendations.update_recommendations_lookups(type(obj))
                self.recommendations.update_recommendations(None)


        # TODO: при удалении зависимых данных, возможно нужно удалять подчиненные данные!

    def is_recommended(self, employee: Employee, train_type: TrainType):
        seek_tuple = employee, train_type
        if seek_tuple in self.recommendations.recommended.keys():
            return True
        return False

    def is_training_requested(self, employee: Employee, train_type: TrainType):

        seek_tuples = itertools.product([employee], [train_type], train_type.doc_types)
        for seek_tuple in seek_tuples:
            if seek_tuple in self.lookup_train_requests.keys():
                for request in self.lookup_train_requests[seek_tuple]:
                    if request.requested and not request.completed:
                        return True
        return False



    def generate_node_path(self, item: Union[Company, Employee, PersonallDocument, Training, Person]): #, sub_item: Optional[DocumentType]):
        if type(item) == Company:
            item: Company
            return item.node_name
        elif type(item) == Employee:
            item: Employee
            return os.path.join(item.company.node_name, item.department.node_name, item.person.node_name)
        elif type(item) == Person:
            item: Person
            return os.path.join('Личное', item.node_name)
        elif type(item) == PersonallDocument:
            item: PersonallDocument
            return os.path.join('Личное', item.person.node_name, item.node_name)
        else:
            self.logger.error(f'{self} невозможно сгенерировать имя для элемента {item}, тип не входит в разрешенные (Company, Employee, PersonallDocument)')

    def generate_training_path(self, item: Training): #, inc_file_index: bool):
        if item.employee is None:
            self.logger.error(f'generate_training_path {item} сотрудник не установлен')
            return f'{item.guid}'
        if item.employee.person is None:
            self.logger.error(f'generate_training_path {item} личность не установлена')
            return f'{item.guid}'
        if item.employee.company is None:
            self.logger.error(f'generate_training_path {item} {item.employee.person.full_name_with_date} организация не установлена')
            return f'{item.guid}'
        if item.employee.department is None:
            self.logger.error(f'generate_training_path {item} {item.employee.person.full_name_with_date} отдел не установлен')
            return f'{item.guid}'
        if item.doc_type is None:
            self.logger.error(f'generate_training_path {item} {item.employee.person.full_name_with_date} документ не установлен')
            return f'{item.guid}'

        tmp_name = os.path.join(item.employee.company.node_name, item.employee.department.node_name, item.employee.person.node_name, item.doc_type.node_name, item.node_name)
        new_name = tmp_name
        i = 1
        while new_name in self.lookup_training_paths.keys():
            new_name = f'{tmp_name} ({i})'
            i +=1
        return new_name

    def is_training_required_today(self, item: Training):
        employee: Employee = item.employee
        train_type: TrainType = item.train_type
        seek_tuple = employee, train_type

        if seek_tuple and seek_tuple in self.lookup_required_trainings.keys():
            return self.lookup_required_trainings[seek_tuple].is_required_today
        return False


    def move_folder(self,src_file_name: str, folder: str, delete: bool = True):
        if os.path.exists(src_file_name):
            files_path = self.workspace_settings.db_files_path
            src_relative_path = os.path.relpath(src_file_name, files_path)
            dst_path = os.path.join(files_path, folder, src_relative_path)
            dst_dir, dst_filename = os.path.split(dst_path)
            dst_filename_only, dst_extension = os.path.splitext(dst_filename)
            try:
                if not os.path.exists(dst_dir):
                    os.makedirs(dst_dir)
                cur_fn_index = 1
                while os.path.exists(dst_path):
                    dst_path = os.path.join(files_path, 'Удалено', dst_dir,  f'{dst_filename_only}({cur_fn_index})')+dst_extension
                    cur_fn_index +=1
                if os.path.isfile(src_file_name):
                    shutil.copyfile(src_file_name, dst_path)
                else:
                    shutil.copytree(src_file_name,dst_path)
                if delete:
                    if os.path.isfile(src_file_name):
                        os.remove(src_file_name)
                    else:
                        shutil.rmtree(src_file_name)
                if os.path.exists(dst_path):
                    return True, ''
            except Exception as ex:
                self._logger.error(f'{self} ошибка выполнения операции {ex}')
        else:
            self._logger.error(f'{self} файл {src_file_name} не найден или не является файлом')
        return False, f'Файл {src_file_name} не найден'

    def move_file(self, src_file_name: str, folder: str, delete: bool = True):
        if os.path.exists(src_file_name) and os.path.isfile(src_file_name):
            files_path = self.workspace_settings.db_files_path
            src_relative_path = os.path.relpath(src_file_name, files_path)
            dst_path = os.path.join(files_path, folder, src_relative_path)
            dst_dir, dst_filename = os.path.split(dst_path)
            dst_filename_only, dst_extension = os.path.splitext(dst_filename)
            try:
                if not os.path.exists(dst_dir):
                    os.makedirs(dst_dir)
                cur_fn_index = 1
                while os.path.exists(dst_path):
                    dst_path = os.path.join(files_path, 'Удалено', dst_dir,  f'{dst_filename_only}({cur_fn_index})')+dst_extension
                    cur_fn_index +=1
                shutil.copyfile(src_file_name, dst_path)
                if delete:
                    os.remove(src_file_name)
                if os.path.exists(dst_path):
                    return True, ''
            except Exception as ex:
                self._logger.error(f'{self} ошибка выполнения операции {ex}')
        else:
            self._logger.error(f'{self} файл {src_file_name} не найден или не является файлом')
        return False, f'Файл {src_file_name} не найден'

    def _copy_to_archive(self, dst_arch_filename: str):
        if os.path.exists(dst_arch_filename):
            files_path = self.workspace_settings.db_files_path
            src_relative_path = os.path.relpath(dst_arch_filename, files_path)
            dst_path = os.path.join(files_path, app_settings.archive_folder, src_relative_path)
            dst_dir, dst_filename = os.path.split(dst_path)
            dst_filename_only1, dst_extension = os.path.splitext(dst_filename)
            try:
                if not os.path.exists(dst_dir):
                    os.makedirs(dst_dir)
                cur_fn_index = 1
                while os.path.exists(dst_path):
                    dst_path = os.path.join(files_path, app_settings.archive_folder, dst_dir, f'{dst_filename_only1}({cur_fn_index})') + dst_extension
                    cur_fn_index += 1
                shutil.copyfile(dst_arch_filename, dst_path)
                if os.path.exists(dst_path):
                    return True, ''
            except Exception as ex1:
                self._logger.error(f'{self} ошибка выполнения операции {ex1}')
        else:
            self._logger.error(f'{self} файл {dst_arch_filename} не найден')
        return False, 'Ошибка файловой системы'

    def copy_file(self, src_file_name: str, dst_file_name: str)->Tuple[bool, str]:
        dst_folder, dst_filename_only = os.path.split(dst_file_name)
        if not os.path.exists(dst_folder):
            try:
                os.makedirs(dst_folder)
            except Exception as ex:
                self._logger.error(f'{self} директория {dst_folder} не создана {ex}')
                return False, 'Ошибка файловой системы'
        if os.path.exists(dst_file_name):
            copy_result, copy_result_msg = self._copy_to_archive(dst_file_name)
            if not copy_result:
                return copy_result, copy_result_msg
            try:
                os.remove(dst_file_name)
            except Exception as ex:
                self._logger.error(f'{self} файл {dst_file_name} не удален {ex}')
                return False, 'Ошибка удаления'
        try:
            shutil.copyfile(src_file_name, dst_file_name)
        except Exception as ex:
            self._logger.error(f'{self} ошибка копирования {src_file_name} {dst_file_name} {ex}')
            return False, 'Ошибка копирования'

        try:
            if not os.path.exists(src_file_name):
                self._logger.error(f'{self} файл {src_file_name} не найден')
                return False, f'Заданный файл {src_file_name} не найден'
            if not self.workspace_settings.db_files_path:
                self._logger.error(f'{self} директория {self.workspace_settings.db_files_path} не задана')
                return False, f'Директория к файлам БД не задана'
            if not os.path.exists(self.workspace_settings.db_files_path):
                os.makedirs(self.workspace_settings.db_files_path)
        except Exception as ex:
            self._logger.error(f'{self} ошибка файловой системы {ex}')
            return False, 'Ошибка файловой системы'
        return True, ''


    def copy_fs_tree(self, src_file_path: str, dst_file_path: str, notifier: EventPublisher):
        if not os.path.exists(dst_file_path):
            try:
                os.makedirs(dst_file_path)
            except Exception as ex:
                self._logger.error(f'{self} ошибка создания {dst_file_path} {ex}')
        if os.path.isfile(src_file_path):
            try:
                shutil.copy2(src_file_path, dst_file_path)
            except Exception as ex:
                self._logger.error(f'{self} ошибка копирования {src_file_path} {dst_file_path} {ex}')
        else:

            try:
                for root, dirs, files in os.walk(src_file_path):
                    for d in dirs:
                        src_dir = os.path.join(root, d)
                        dst_dir = os.path.join(dst_file_path, os.path.relpath(src_dir, src_file_path))
                        os.makedirs(dst_dir, exist_ok=True)
                        notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(f'Копирование {d}'))

                    for file in files:
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(dst_file_path, os.path.relpath(src_file, src_file_path))
                        shutil.copy2(src_file, dst_file)
                        notifier.notify_listeners(EventType.OPERATION_STEP, EventProgressObject(f'Копирование {file}'))
            except Exception as ex:
                self._logger.error(f'{self} ошибка создания {dst_file_path} {ex}')

    def get_training_file_name(self, tr: Training):
        return os.path.join(self.workspace_settings.db_files_path, tr.name_path)+(tr.doc_file_extension or "")

    def get_doc_file_name(self, p: PersonallDocument):
        return os.path.join(self.workspace_settings.db_files_path, p.name_path)


display_size: Optional[Any] = None

class AppSettings(XMLStorable):
    run_path: str
    last_workspace_path: str
    last_file_name: str
    use_history: bool
    date_format: str
    header_size: int
    tab_size: int
    archive_folder: str
    delete_folder: str
    recommendations_to_file: bool


    def __init__(self):
        XMLStorable.__init__(self)
        self.last_workspace_path = ''
        self.last_file_name = ''
        self.run_path = get_run_path()
        self.use_history = True
        self.date_format = "%d.%m.%Y"
        self.header_size = 14
        self.tab_size = 10
        self.archive_folder = 'Архив'
        self.delete_folder = 'Удалено'
        self.recommendations_to_file = False


class RecommendationClass(EventPublisher):
    dataset: MainDatabase
    logger: Logger

    employees: Dict[str, Employee]
    train_types: Dict[str, TrainType]
    positions: Dict[str, Position]
    departments: Dict[str, Department]
    config_name: str
    recommended: Dict[Tuple[Employee, TrainType], bool]
    def __init__(self, dataset: MainDatabase, logger: Logger):
        EventPublisher.__init__(self)
        self.dataset = dataset
        self.logger = logger
        self.config_name = 'recommendations'
        self.employees = {}
        self.train_types = {}
        self.positions = {}
        self.departments = {}
        self.recommended = {}
        self.update_recommendations_lookups(Employee)
        self.update_recommendations_lookups(TrainType)
        self.update_recommendations_lookups(Position)
        self.update_recommendations_lookups(Department)





    def save(self, text_content):
        self.dataset.write_config(self.config_name,text_content, app_settings.recommendations_to_file, None)

    @staticmethod
    def get_comments_positions(text_content: str)->List[Tuple[int, int]]:
        marked_positions = []

        if text_content is None:
            text_content = ''
        re_comment_string = '^#.*$'
        matches = re.finditer(re_comment_string, text_content, re.MULTILINE)
        for match in matches:
            marked_positions.append((match.start(), match.end()))
        return marked_positions

    @staticmethod
    def get_sections_positions(text_content: str)->List[Tuple[int, int]]:
        marked_positions = []

        if text_content is None:
            text_content = ''
        re_section = r'^\[.*\]$'
        matches = re.finditer(re_section, text_content, re.MULTILINE)
        for match in matches:
            marked_positions.append((match.start(), match.end()))
        marked_positions.sort(key=lambda b: b[0])
        return marked_positions

    @staticmethod
    def get_params_positions(text_content: str)->List[Tuple[int, int]]:
        marked_positions = []

        if text_content is None:
            text_content = ''
        prefixes = ['сотрудники=', 'должности=', 'представительства=', 'обучения=', 'начало=', 'окончание=', 'только_указанные=']
        pattern = r"^(?:" + "|".join(map(re.escape, prefixes)) + r").*$"
        matches = re.finditer(pattern, text_content, re.MULTILINE)
        for match in matches:
            marked_positions.append((match.start(), match.end()))
        marked_positions.sort(key=lambda  b: b[0])
        return marked_positions



    @staticmethod
    def get_param_values(text_content: str)->Dict[str, Dict[str, List[Tuple[str, int, int]]]]:


        if text_content is None:
            text_content = ''
        answer: Dict[str, Dict[str, List[Tuple[str, int, int]]]] = {}
        section_positions = list(RecommendationClass.get_sections_positions(text_content))
        section_names = {}
        for sstart, sstop in section_positions:
            section_names[(sstart, sstop)] = text_content[sstart+1:sstop-1]


        for param_str_start, param_str_stop in RecommendationClass.get_params_positions(text_content):
            section_name = ''

            for sstart, sstop in section_names.keys():
                if param_str_start>sstart:
                    section_name = section_names[(sstart, sstop)]

            param_str = text_content[param_str_start:param_str_stop]
            param_name = param_str[:param_str.index('=')]
            param_values_str = param_str[param_str.index('=')+1:]
            # я хер знает как это работает, ИИ предложил, я согласился, а хули нет, когда да, но работает же
            param_pattern = r'(?<=\|)[^|]*(?=\|)|^[^|]*(?=\|)|(?<=\|)[^|]*$|^[^|]*$'
            param_matches = re.finditer(param_pattern, param_values_str)
            param_values = []
            for pm in param_matches:
                param_values.append((pm.group(0), pm.start()+param_str_start+len(param_name)+1, pm.end()+param_str_start+len(param_name)+1))

            if section_name not in answer.keys():
                answer[section_name] = {}
            if param_name not in answer[section_name].keys():
                answer[section_name][param_name] = []
            answer[section_name][param_name].extend(param_values)
        return answer



    def is_param_correct(self, param_name, param_value):
        if param_name == 'сотрудники':
            if param_value in self.employees.keys():
                return True
            return False
        elif param_name == 'должности':
            if param_value in self.positions.keys():
                return True
            return False
        elif param_name == 'представительства':
            if param_value in self.departments.keys():
                return True
            return False
        elif param_name == 'обучения':
            if param_value in self.train_types.keys():
                return True
            return False
        elif param_name == 'начало':
            try:
                datetime.datetime.strptime(param_value,'%d.%m.%Y')
                return True
            except Exception as _ex:
                return False
        elif param_name == 'окончание':
            try:
                datetime.datetime.strptime(param_value,'%d.%m.%Y')
                return True
            except Exception as _ex:
                return False
        elif param_name == 'только_указанные':
            if param_value == 'да':
                return True
            return False


    def update_recommendations_lookups(self, obj_type: type):
        employee: Employee
        position: Position
        department: Department
        train_type: TrainType

        if obj_type == Employee:
            self.employees.clear()
            for employee in self.dataset.get_table(Employee).get_items():
                lookup_str = f'{employee.person.last_name} {employee.person.first_name} {employee.person.middle_name} {employee.position.name} {employee.department.name}'
                if lookup_str not in self.employees.keys():
                    self.employees[lookup_str] = employee
                else:
                    self.logger.error(f'{self} задвоение сотрудника {lookup_str}')
        if obj_type == TrainType:
            self.train_types.clear()
            for train_type in self.dataset.get_table(TrainType).get_items():
                lookup_str = f'{train_type.short_name}'
                if lookup_str not in self.train_types.keys():
                    self.train_types[lookup_str] = train_type
                else:
                    self.logger.error(f'{self} задвоение типа обучения {lookup_str}')

        if obj_type == Position:
            self.positions.clear()
            for position in self.dataset.get_table(Position).get_items():
                lookup_str = f'{position.name}'
                if lookup_str not in self.positions.keys():
                    self.positions[lookup_str] = position
                else:
                    self.logger.error(f'{self} задвоение должности {lookup_str}')


        if obj_type == Department:
            self.departments.clear()
            for department in self.dataset.get_table(Department).get_items():
                lookup_str = f'{department.name}'
                if lookup_str not in self.departments.keys():
                    self.departments[lookup_str] = department
                else:
                    self.logger.error(f'{self} задвоение представительства {lookup_str}')

        self.notify_listeners(EventType.ITEM_NEED_UPDATE, EventObject(self))


    def update_recommendations(self, notifier: Optional[EventPublisher]):
        if notifier:
            notifier.notify_listeners(EventType.OPERATION_BEGIN,EventProgressObject('Обработка рекомендаций'))
        text_content = self.dataset.get_config(self.config_name)
        rules = self.get_param_values(text_content)


        current_recommendations: Dict[Tuple[Employee, TrainType], Tuple[datetime.date, datetime.date]] = {}

        for rule_name, params_dict in rules.items():
            employes_list = []
            positions_ref = {}
            departments_ref = {}
            train_types_list = []

            start_date = None
            stop_date = None
            clear_other = False
            for param_name, values_list in params_dict.items():
                for val in values_list:
                    value = val[0]
                    if param_name == 'сотрудники':
                        if value in self.employees.keys():
                            employes_list.append(self.employees[value])
                    elif param_name == 'должности':
                        if value in self.positions.keys():
                            positions_ref[self.positions[value]] = 1 #.append(self.positions[value])
                    elif param_name == 'представительства':
                        if value in self.departments.keys():
                            departments_ref[self.departments[value]] = 1#.append(self.departments[value])
                    elif param_name == 'обучения':
                        if value in self.train_types.keys():
                            train_types_list.append(self.train_types[value])
                            train_types_defined = True
                    elif param_name == 'начало':
                        try:
                            start_date = datetime.datetime.strptime(value, '%d.%m.%Y').date()
                        except Exception as _ex:
                            start_date = None
                    elif param_name == 'окончание':
                        try:
                            stop_date = datetime.datetime.strptime(value, '%d.%m.%Y').date()
                        except Exception as _ex:
                            start_date = None
                    elif param_name == 'только_указанные':
                        if value == 'да':
                            clear_other = True

            if start_date and start_date>datetime.date.today():
                continue
            if stop_date and stop_date<datetime.date.today():
                continue

            if not employes_list:
                if len(departments_ref) == 0 and len(positions_ref)>0:
                    for d in self.dataset.get_table(Department).get_items():
                        departments_ref[d] = 1
                if len(departments_ref) > 0 and len(positions_ref)==0:
                    for d in self.dataset.get_table(Position).get_items():
                        positions_ref[d] = 1

                item: Employee
                for item in self.dataset.get_table(Employee).get_items():
                    if item.position in positions_ref.keys() and item.department in departments_ref.keys() and not item.fire_date:
                        employes_list.append(item)
            else:
                if clear_other:
                    remove_tuples = list(itertools.product(employes_list, list(self.train_types.values())))
                    for r_tuple in remove_tuples:
                        if r_tuple in current_recommendations.keys():
                            del current_recommendations[r_tuple]

            seek_tuples = list(itertools.product(employes_list, train_types_list))
            if start_date and start_date>=datetime.date.today():
                seek_tuples = []
            if stop_date and stop_date<=datetime.date.today():
                seek_tuples = []

            for seek_tuple in seek_tuples:
                current_recommendations[seek_tuple] = (start_date, stop_date)

        required_table = self.dataset.get_table(TrainingRequired)
        recomended_list_keys = list(self.recommended.keys())
        p1_len = len(recomended_list_keys)
        p_len = len(current_recommendations)+p1_len
        for i, key in enumerate(recomended_list_keys):
            if notifier:
                notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Обработка рекомендаций', cur_val=i+1, max_val=p_len))
            if key not in current_recommendations.keys():
                del self.recommended[key]
                if key in self.dataset.lookup_required_trainings.keys():
                    if self.dataset.lookup_required_trainings[key].required:
                        required_table.notify_listeners(EventType.ITEM_NEED_UPDATE, EventObject(self.dataset.lookup_required_trainings[key]))
                    else:
                        required_table.delete_mark(self.dataset.lookup_required_trainings[key], False, True)

        for i, key in enumerate(current_recommendations.keys()):
            if notifier:
                notifier.notify_listeners(EventType.OPERATION_BEGIN, EventProgressObject('Обработка рекомендаций', cur_val=i + 1 + p1_len, max_val=p_len))
            if key not in self.recommended.keys():
                self.recommended[key] = True
                if key in self.dataset.lookup_required_trainings.keys():
                    required_table.notify_listeners(EventType.ITEM_NEED_UPDATE, EventObject(self.dataset.lookup_required_trainings[key]))
                else:
                    new_required = TrainingRequired(required_table)
                    new_required.employee = key[0]
                    new_required.train_type = key[1]
                    new_required.start_date = current_recommendations[key][0]
                    new_required.stop_date = current_recommendations[key][0]
                    new_required.required = False
                    new_required.active = True
                    if not required_table.undelete_mark(new_required,False, True):
                        new_required.new_guid()
                        required_table.add(new_required,False, True)

        self.recommended = dict(current_recommendations)
        self.notify_listeners(EventType.ITEM_NEED_UPDATE, EventObject(self))
        if notifier:
            notifier.notify_listeners(EventType.OPERATION_END, EventProgressObject('Обработка рекомендаций завершена'))







app_settings = AppSettings()

