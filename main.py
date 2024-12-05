# task_manager.py

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import csv
import os
from PyQt5.QtCore import QSize, QDate, QTime, Qt, QTimer, pyqtSignal, QMimeData, QByteArray
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QDateEdit, QTimeEdit, QLabel, QDialog, QFormLayout,
    QDialogButtonBox, QComboBox, QTextEdit, QFileDialog, QMenuBar, QAction,
    QGroupBox, QRadioButton, QButtonGroup, QSplitter, QToolBar,
    QMenu, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QStylePainter,
)
from PyQt5.QtGui import QColor, QDrag, QFont, QIcon, QPixmap, QKeySequence
from database import create_connection, create_table

class PriorityDelegate(QStyledItemDelegate):
    """
    Делегат для отображения иконок приоритета в списке задач.
    """
    def paint(self, painter, option, index):
        priority = index.data(Qt.UserRole + 1)  # Получаем приоритет напрямую из данных

        # Определение иконки в зависимости от приоритета
        if priority == 'Высокий':
            icon = QIcon('icons/high_priority.png')
        elif priority == 'Средний':
            icon = QIcon('icons/medium_priority.png')
        elif priority == 'Низкий':
            icon = QIcon('icons/low_priority.png')
        else:
            icon = QIcon()

        # Отрисовка иконки
        if not icon.isNull():
            icon.paint(painter, option.rect.left(), option.rect.top(), 24, 24)

        # Смещение текста, чтобы не перекрывать иконку
        option.rect.setLeft(option.rect.left() + 30)
        super().paint(painter, option, index)

class DraggableListWidget(QListWidget):
    taskDropped = pyqtSignal(int, str)  # Сигнал: task_id, new_status

    def __init__(self, status, parent=None):
        super().__init__(parent)
        self.status = status
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setObjectName(status)
        self.init_style()
        self.setItemDelegate(PriorityDelegate())  # Установка делегата для отображения иконок приоритета

    def init_style(self):
        self.setStyleSheet("""
            QListWidget {
                background-color: #3b4252;
                border: 1px solid #4c566a;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #81a1c1;  /* Более "прикольный" цвет при выборе */
                color: #2e3440;
            }
        """)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mimeData = QMimeData()
            # Устанавливаем собственный MIME-тип с task_id
            task_id = item.data(Qt.UserRole)
            mimeData.setData('application/x-task-id', QByteArray(str(task_id).encode('utf-8')))
            drag.setMimeData(mimeData)
            drag.exec_(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-task-id'):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-task-id'):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.source() == self:
            # Разрешить внутреннее перемещение
            super().dropEvent(event)
            return

        if event.mimeData().hasFormat('application/x-task-id'):
            task_id_bytes = event.mimeData().data('application/x-task-id')
            try:
                task_id = int(task_id_bytes.data().decode('utf-8'))
                new_status = self.status
                print(f'Dropped task_id: {task_id} to status: {new_status}')  # Отладка
                self.taskDropped.emit(task_id, new_status)
                event.accept()
            except (IndexError, ValueError) as e:
                QMessageBox.warning(self, 'Ошибка', f'Неверный формат задачи.\n{e}')
                event.ignore()
        else:
            QMessageBox.warning(self, 'Ошибка', 'Неверный формат задачи.')
            event.ignore()

    def contextMenuEvent(self, event):
        # Создание контекстного меню
        item = self.itemAt(event.pos())
        if item:
            menu = QMenu(self)
            update_action = QAction('Обновить', self)
            delete_action = QAction('Удалить', self)
            menu.addAction(update_action)
            menu.addAction(delete_action)
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == update_action:
                self.parent().update_task()
            elif action == delete_action:
                self.parent().delete_task()

class TaskManager(QWidget):
    def __init__(self):
        super().__init__()
        try:
            create_table()
            self.initUI()
            self.initTimer()
        except Exception as e:
            QMessageBox.critical(self, 'Критическая ошибка', f'Не удалось инициализировать приложение.\n{e}')
            sys.exit(1)

    def initUI(self):
        self.setWindowTitle('Таск-менеджер')
        self.setWindowIcon(QIcon('icons/app_icon.png'))  # Убедитесь, что иконка существует

        # Основной стиль приложения
        self.setStyleSheet("""
            QWidget {
                background-color: #2e3440;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10pt;
            }
            QLabel {
                color: #d8dee9;
            }
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QTimeEdit {
                background-color: #434c5e;
                border: 1px solid #4c566a;
                border-radius: 4px;
                padding: 4px;
                color: #d8dee9;
            }
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #81a1c1;
            }
            QPushButton {
                background-color: #88c0d0;
                color: #2e3440;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #81a1c1;
            }
            QRadioButton {
                color: #d8dee9;
            }
            QMenuBar {
                background-color: #434c5e;
                color: #d8dee9;
            }
            QMenuBar::item {
                background-color: #434c5e;
                color: #d8dee9;
            }
            QMenuBar::item:selected {
                background-color: #4c566a;
            }
            QMenu {
                background-color: #3b4252;
                color: #d8dee9;
            }
            QMenu::item:selected {
                background-color: #434c5e;
            }
            QListWidget {
                font-size: 9pt;
            }
            QTextEdit#description_display {
                background-color: #434c5e;
                color: #d8dee9;
                border: 1px solid #4c566a;
                border-radius: 4px;
            }
            QToolBar {
                background-color: #3b4252;
                spacing: 10px;
            }
            QToolButton {
                background-color: #434c5e;
                border: none;
                padding: 5px;
                border-radius: 4px;
                color: #d8dee9;
            }
            QToolButton:hover {
                background-color: #4c566a;
            }
        """)

        # Создание панели инструментов
        toolbar = QToolBar("Основные действия")
        toolbar.setIconSize(QSize(16, 16))
        
        # Проверка наличия всех необходимых иконок
        required_icons = {
            'app_icon': 'icons/app_icon.png',
            'import': 'icons/import.png',    # Иконка для импорта
            'export': 'icons/export.png',    # Иконка для экспорта
            'high_priority': 'icons/high_priority.png',
            'medium_priority': 'icons/medium_priority.png',
            'low_priority': 'icons/low_priority.png'
        }

        missing_icons = []
        for key, path in required_icons.items():
            if not os.path.exists(path):
                missing_icons.append(path)
        
        if missing_icons:
            QMessageBox.critical(self, 'Критическая ошибка', f'Не найдены следующие иконки:\n' + '\n'.join(missing_icons))
            sys.exit(1)

        # Создание действий импорта и экспорта
        export_action = QAction(QIcon('icons/export.png'), "Экспортировать задачи", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.setToolTip("Экспортировать задачи в CSV файл (Ctrl+E)")
        export_action.triggered.connect(self.export_tasks)
        toolbar.addAction(export_action)

        import_action = QAction(QIcon('icons/import.png'), "Импортировать задачи", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.setToolTip("Импортировать задачи из CSV файла (Ctrl+I)")
        import_action.triggered.connect(self.import_tasks)
        toolbar.addAction(import_action)

        # Основные макеты
        main_layout = QVBoxLayout()
        main_layout.setMenuBar(toolbar)

        # Использование QSplitter для гибкой раскладки
        splitter = QSplitter(Qt.Horizontal)

        # Левая панель: списки задач
        lists_widget = QWidget()
        lists_layout = QHBoxLayout()

        # Создание списков для каждого статуса
        self.to_do_list = DraggableListWidget('Сделать', self)
        self.in_progress_list = DraggableListWidget('В работе', self)
        self.under_review_list = DraggableListWidget('На проверке', self)
        self.done_list = DraggableListWidget('Завершено', self)

        # Подключение сигналов для обновления статуса
        self.to_do_list.taskDropped.connect(self.update_task_status)
        self.in_progress_list.taskDropped.connect(self.update_task_status)
        self.under_review_list.taskDropped.connect(self.update_task_status)
        self.done_list.taskDropped.connect(self.update_task_status)

        # Добавление списков в макет
        lists_layout.addWidget(self.create_list_widget('Сделать', self.to_do_list))
        lists_layout.addWidget(self.create_list_widget('В работе', self.in_progress_list))
        lists_layout.addWidget(self.create_list_widget('На проверке', self.under_review_list))
        lists_layout.addWidget(self.create_list_widget('Завершено', self.done_list))

        lists_widget.setLayout(lists_layout)
        splitter.addWidget(lists_widget)

        # Правая панель: подробности задачи и элементы управления
        details_widget = QWidget()
        details_layout = QVBoxLayout()

        # Поисковая строка
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Поиск задач...')
        self.search_input.textChanged.connect(self.search_tasks)
        search_label = QLabel('Поиск:')
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)

        details_layout.addLayout(search_layout)

        # Поля для добавления задачи
        form_layout = QFormLayout()

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText('Введите новую задачу')
        form_layout.addRow('Задача:', self.task_input)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText('Введите описание задачи')
        self.description_input.setFixedHeight(60)
        form_layout.addRow('Описание:', self.description_input)

        self.priority_label = QLabel('Приоритет:')
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(['Низкий', 'Средний', 'Высокий'])
        form_layout.addRow(self.priority_label, self.priority_combo)

        self.status_label = QLabel('Статус:')
        self.status_group = QButtonGroup(self)
        self.status_group.setExclusive(True)
        self.status_buttons = {}
        statuses = ['Сделать', 'В работе', 'На проверке', 'Завершено']
        status_layout = QHBoxLayout()
        for status in statuses:
            radio_button = QRadioButton(status)
            if status == 'Сделать':
                radio_button.setChecked(True)
            self.status_group.addButton(radio_button)
            status_layout.addWidget(radio_button)
            self.status_buttons[status] = radio_button
        form_layout.addRow(self.status_label, status_layout)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form_layout.addRow('Дата выполнения:', self.date_edit)

        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime())
        form_layout.addRow('Время выполнения:', self.time_edit)

        details_layout.addLayout(form_layout)

        # Кнопки добавления, обновления и удаления
        button_layout = QHBoxLayout()
        self.add_button = QPushButton('Добавить')
        self.add_button.clicked.connect(self.add_task)
        self.add_button.setToolTip("Добавить новую задачу (Ctrl+N)")
        self.add_button.setIcon(QIcon('icons/add.png'))
        button_layout.addWidget(self.add_button)

        self.update_button = QPushButton('Обновить')
        self.update_button.clicked.connect(self.update_task)
        self.update_button.setToolTip("Обновить выбранную задачу (Ctrl+U)")
        self.update_button.setIcon(QIcon('icons/update.png'))
        button_layout.addWidget(self.update_button)

        self.delete_button = QPushButton('Удалить')
        self.delete_button.clicked.connect(self.delete_task)
        self.delete_button.setToolTip("Удалить выбранную задачу (Del)")
        self.delete_button.setIcon(QIcon('icons/delete.png'))
        button_layout.addWidget(self.delete_button)

        details_layout.addLayout(button_layout)

        # Отображение описания выбранной задачи
        self.description_display = QTextEdit()
        self.description_display.setReadOnly(True)
        self.description_display.setPlaceholderText('Описание выбранной задачи появится здесь...')
        self.description_display.setObjectName('description_display')
        details_layout.addWidget(QLabel('Описание задачи:'))
        details_layout.addWidget(self.description_display)

        # Добавление области фильтрации
        filter_layout = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['Все', 'Низкий', 'Средний', 'Высокий'])
        self.filter_combo.currentIndexChanged.connect(self.filter_tasks)
        filter_label = QLabel('Фильтр по приоритету:')
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_combo)
        details_layout.addLayout(filter_layout)

        details_widget.setLayout(details_layout)
        splitter.addWidget(details_widget)

        # Настройка разделителей
        splitter.setSizes([800, 400])

        # Добавление QSplitter в основной макет
        main_layout.addWidget(splitter)

        # Добавление панели инструментов в главное окно
        self.setLayout(main_layout)

        # Подключение сигналов для отображения описания задачи
        self.to_do_list.itemClicked.connect(self.display_task_description)
        self.in_progress_list.itemClicked.connect(self.display_task_description)
        self.under_review_list.itemClicked.connect(self.display_task_description)
        self.done_list.itemClicked.connect(self.display_task_description)

        self.load_tasks()

    def create_list_widget(self, title, list_widget):
        layout = QVBoxLayout()
        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(list_widget)
        container = QWidget()
        container.setLayout(layout)
        return container

    def load_tasks(self, filter_text='', priority_filter='Все'):
        # Очистка всех списков
        self.to_do_list.clear()
        self.in_progress_list.clear()
        self.under_review_list.clear()
        self.done_list.clear()

        try:
            conn = create_connection()
            cursor = conn.cursor()
            query = '''
                SELECT id, task, description, due_date, due_time, priority, status, completed_at FROM tasks
                WHERE (task LIKE ? OR description LIKE ?)
            '''
            params = (f'%{filter_text}%', f'%{filter_text}%')
            if priority_filter != 'Все':
                query += ' AND priority = ?'
                params += (priority_filter,)
            query += ' ORDER BY due_date, due_time'
            cursor.execute(query, params)
            tasks = cursor.fetchall()
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось загрузить задачи.\n{e}')
            return

        for task in tasks:
            task_id, task_text, description, due_date, due_time, priority, status, completed_at = task
            if status == 'Завершено' and completed_at:
                # Если задача завершена, добавляем время завершения
                display_text = f'{task_text} (Завершено: {completed_at})'
            else:
                if due_date and due_time:
                    display_text = f'{task_text} (До {due_date} {due_time})'
                elif due_date:
                    display_text = f'{task_text} (До {due_date})'
                elif due_time:
                    display_text = f'{task_text} (До {due_time})'
                else:
                    display_text = f'{task_text}'

            item = QListWidgetItem(display_text)
            # Установка цвета фона в зависимости от приоритета
            if priority == 'Высокий':
                item.setBackground(QColor('#bf616a'))  # Красный
                item.setForeground(QColor('#2e3440'))
            elif priority == 'Средний':
                item.setBackground(QColor('#ebcb8b'))  # Желтый
                item.setForeground(QColor('#2e3440'))
            elif priority == 'Низкий':
                item.setBackground(QColor('#a3be8c'))  # Зеленый
                item.setForeground(QColor('#2e3440'))

            # Добавление описания как подсказки
            if description:
                item.setToolTip(description)

            # Сохранение task_id и priority в данных элемента
            item.setData(Qt.UserRole, task_id)
            item.setData(Qt.UserRole + 1, priority)

            # Добавление в соответствующий список
            if status == 'Сделать':
                self.to_do_list.addItem(item)
            elif status == 'В работе':
                self.in_progress_list.addItem(item)
            elif status == 'На проверке':
                self.under_review_list.addItem(item)
            elif status == 'Завершено':
                self.done_list.addItem(item)

    def search_tasks(self):
        search_text = self.search_input.text().strip()
        priority_filter = self.filter_combo.currentText()
        self.load_tasks(filter_text=search_text, priority_filter=priority_filter)

    def filter_tasks(self):
        search_text = self.search_input.text().strip()
        priority_filter = self.filter_combo.currentText()
        self.load_tasks(filter_text=search_text, priority_filter=priority_filter)

    def update_task_status(self, task_id, new_status):
        print(f'Updating task_id: {task_id} to new_status: {new_status}')  # Отладка
        try:
            conn = create_connection()
            cursor = conn.cursor()
            if new_status == 'Завершено':
                # Устанавливаем текущую дату и время как время завершения
                completed_at = QDate.currentDate().toString('yyyy-MM-dd') + ' ' + QTime.currentTime().toString('HH:mm')
                cursor.execute('UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?', (new_status, completed_at, task_id))
            else:
                # Если статус изменяется с "Завершено" на другой, очищаем поле completed_at
                cursor.execute('UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?', (new_status, task_id))
            conn.commit()
            conn.close()
            self.load_tasks(filter_text=self.search_input.text().strip(), priority_filter=self.filter_combo.currentText())
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось обновить статус задачи.\n{e}')

    def add_task(self):
        task_text = self.task_input.text().strip()
        description = self.description_input.toPlainText().strip()
        due_date = self.date_edit.date().toString('yyyy-MM-dd')
        due_time = self.time_edit.time().toString('HH:mm')
        priority = self.priority_combo.currentText()

        # Получение выбранного статуса
        selected_status = 'Сделать'  # Дефолтный статус
        for status, button in self.status_buttons.items():
            if button.isChecked():
                selected_status = status
                break

        if task_text:
            try:
                conn = create_connection()
                cursor = conn.cursor()
                if selected_status == 'Завершено':
                    # Если задача сразу ставится в завершено, устанавливаем completed_at
                    completed_at = QDate.currentDate().toString('yyyy-MM-dd') + ' ' + QTime.currentTime().toString('HH:mm')
                    cursor.execute(
                        'INSERT INTO tasks (task, description, due_date, due_time, priority, status, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (task_text, description, due_date, due_time, priority, selected_status, completed_at)
                    )
                else:
                    cursor.execute(
                        'INSERT INTO tasks (task, description, due_date, due_time, priority, status) VALUES (?, ?, ?, ?, ?, ?)',
                        (task_text, description, due_date, due_time, priority, selected_status)
                    )
                conn.commit()
                conn.close()
                self.task_input.clear()
                self.description_input.clear()
                self.date_edit.setDate(QDate.currentDate())
                self.time_edit.setTime(QTime.currentTime())
                self.priority_combo.setCurrentIndex(1)  # Средний
                # Сбросить статус на дефолтный
                self.status_buttons['Сделать'].setChecked(True)
                self.load_tasks(filter_text=self.search_input.text().strip(), priority_filter=self.filter_combo.currentText())
            except Exception as e:
                QMessageBox.warning(self, 'Ошибка', f'Не удалось добавить задачу.\n{e}')
        else:
            QMessageBox.warning(self, 'Ошибка', 'Задача не может быть пустой.')

    def update_task(self):
        selected_item = (
            self.to_do_list.currentItem() or
            self.in_progress_list.currentItem() or
            self.under_review_list.currentItem() or
            self.done_list.currentItem()
        )
        if selected_item:
            # Извлекаем task_id и priority из данных элемента
            task_id = selected_item.data(Qt.UserRole)
            priority = selected_item.data(Qt.UserRole + 1)
            if task_id is None:
                QMessageBox.warning(self, 'Ошибка', 'Не удалось определить ID задачи.')
                return

            # Открываем диалог для обновления задачи
            dialog = UpdateTaskDialog(task_id, self)
            if dialog.exec_() == QDialog.Accepted:
                new_task_text, new_description, new_due_date, new_due_time, new_priority, new_status = dialog.get_values()
                if new_task_text:
                    try:
                        conn = create_connection()
                        cursor = conn.cursor()
                        if new_status == 'Завершено':
                            # Устанавливаем completed_at
                            completed_at = QDate.currentDate().toString('yyyy-MM-dd') + ' ' + QTime.currentTime().toString('HH:mm')
                            cursor.execute(
                                'UPDATE tasks SET task = ?, description = ?, due_date = ?, due_time = ?, priority = ?, status = ?, completed_at = ? WHERE id = ?',
                                (new_task_text, new_description, new_due_date, new_due_time, new_priority, new_status, completed_at, task_id)
                            )
                        else:
                            # Если статус изменяется с "Завершено" на другой, очищаем completed_at
                            cursor.execute(
                                'UPDATE tasks SET task = ?, description = ?, due_date = ?, due_time = ?, priority = ?, status = ?, completed_at = NULL WHERE id = ?',
                                (new_task_text, new_description, new_due_date, new_due_time, new_priority, new_status, task_id)
                            )
                        conn.commit()
                        conn.close()
                        self.load_tasks(filter_text=self.search_input.text().strip(), priority_filter=self.filter_combo.currentText())
                    except Exception as e:
                        QMessageBox.warning(self, 'Ошибка', f'Не удалось обновить задачу.\n{e}')
                else:
                    QMessageBox.warning(self, 'Ошибка', 'Задача не может быть пустой.')
        else:
            QMessageBox.warning(self, 'Ошибка', 'Задача не выбрана.')

    def delete_task(self):
        selected_item = (
            self.to_do_list.currentItem() or
            self.in_progress_list.currentItem() or
            self.under_review_list.currentItem() or
            self.done_list.currentItem()
        )
        if selected_item:
            task_id = selected_item.data(Qt.UserRole)
            if task_id is None:
                QMessageBox.warning(self, 'Ошибка', 'Не удалось определить ID задачи.')
                return

            reply = QMessageBox.question(
                self,
                'Удалить задачу',
                'Вы уверены, что хотите удалить эту задачу?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    conn = create_connection()
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                    conn.commit()
                    conn.close()
                    self.load_tasks(filter_text=self.search_input.text().strip(), priority_filter=self.filter_combo.currentText())
                except Exception as e:
                    QMessageBox.warning(self, 'Ошибка', f'Не удалось удалить задачу.\n{e}')
        else:
            QMessageBox.warning(self, 'Ошибка', 'Задача не выбрана.')

    def export_tasks(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Экспортировать задачи в CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_name:
            try:
                conn = create_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT id, task, description, due_date, due_time, priority, status, completed_at FROM tasks')
                tasks = cursor.fetchall()
                conn.close()
                with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['ID', 'Задача', 'Описание', 'Дата выполнения', 'Время выполнения', 'Приоритет', 'Статус', 'Завершено в'])
                    writer.writerows(tasks)
                QMessageBox.information(self, 'Успех', 'Задачи успешно экспортированы.')
            except Exception as e:
                QMessageBox.warning(self, 'Ошибка', f'Не удалось экспортировать задачи.\n{e}')

    def import_tasks(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Импортировать задачи из CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_name:
            try:
                with open(file_name, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    tasks = []
                    for row in reader:
                        task_text = row['Задача']
                        description = row['Описание']
                        due_date = row['Дата выполнения']
                        due_time = row['Время выполнения']
                        priority = row['Приоритет']
                        status = row['Статус']
                        completed_at = row.get('Завершено в')  # Новое поле
                        tasks.append((task_text, description, due_date, due_time, priority, status, completed_at))
                conn = create_connection()
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT INTO tasks (task, description, due_date, due_time, priority, status, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', tasks)
                conn.commit()
                conn.close()
                self.load_tasks(filter_text=self.search_input.text().strip(), priority_filter=self.filter_combo.currentText())
                QMessageBox.information(self, 'Успех', 'Задачи успешно импортированы.')
            except Exception as e:
                QMessageBox.warning(self, 'Ошибка', f'Не удалось импортировать задачи.\n{e}')

    def initTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(60000)  # Проверять каждую минуту

    def check_reminders(self):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, task, due_date, due_time FROM tasks WHERE status != "Завершено"')
            tasks = cursor.fetchall()
            conn.close()
            current_qdate = QDate.currentDate()
            current_qtime = QTime.currentTime()
            for task in tasks:
                task_id, task_text, due_date, due_time = task
                if due_date and due_time:
                    task_qdate = QDate.fromString(due_date, 'yyyy-MM-dd')
                    task_qtime = QTime.fromString(due_time, 'HH:mm')
                    if task_qdate == current_qdate:
                        seconds_until_due = current_qtime.secsTo(task_qtime)
                        if 0 < seconds_until_due <= 300:  # 5 минут
                            QMessageBox.information(self, 'Напоминание', f'Задача "{task_text}" должна быть выполнена через 5 минут.')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось проверить напоминания.\n{e}')

    def display_task_description(self, item):
        # Извлекаем task_id из данных элемента
        task_id = item.data(Qt.UserRole)
        if task_id is None:
            self.description_display.setText('')
            return

        try:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT description FROM tasks WHERE id = ?', (task_id,))
            result = cursor.fetchone()
            conn.close()
            if result and result[0]:
                self.description_display.setText(result[0])
            else:
                self.description_display.setText('Нет описания.')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось загрузить описание задачи.\n{e}')
            self.description_display.setText('')

class UpdateTaskDialog(QDialog):
    def __init__(self, task_id, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.setWindowTitle('Обновить задачу')
        self.setMinimumSize(400, 300)  # Устанавливаем минимальный размер окна
        self.initUI()

    def initUI(self):
        # Стилизация диалога
        self.setStyleSheet("""
            QWidget {
                background-color: #2e3440;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10pt;
            }
            QLabel {
                color: #d8dee9;
            }
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QTimeEdit {
                background-color: #434c5e;
                border: 1px solid #4c566a;
                border-radius: 4px;
                padding: 4px;
                color: #d8dee9;
            }
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #81a1c1;
            }
            QPushButton {
                background-color: #88c0d0;
                color: #2e3440;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #81a1c1;
            }
            QDialogButtonBox {
                button-layout: 0;
            }
        """)

        # Создаем макет формы
        self.layout = QFormLayout(self)

        # Поле для ввода текста задачи
        self.task_input = QLineEdit()
        self.layout.addRow('Задача:', self.task_input)

        # Поле для ввода описания задачи
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText('Введите описание задачи')
        self.layout.addRow('Описание:', self.description_input)

        # Виджет для выбора приоритета
        self.priority_label = QLabel('Приоритет:')
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(['Низкий', 'Средний', 'Высокий'])
        self.layout.addRow(self.priority_label, self.priority_combo)

        # Виджет для выбора статуса
        self.status_label = QLabel('Статус:')
        self.status_combo = QComboBox()
        self.status_combo.addItems(['Сделать', 'В работе', 'На проверке', 'Завершено'])
        self.layout.addRow(self.status_label, self.status_combo)

        # Виджет для выбора даты
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.layout.addRow('Дата выполнения:', self.date_edit)

        # Виджет для выбора времени
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime())
        self.layout.addRow('Время выполнения:', self.time_edit)

        # Кнопки OK и Отмена
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addRow(self.buttons)

        # Загрузка текущих данных задачи
        self.load_task_data()

    def load_task_data(self):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT task, description, due_date, due_time, priority, status FROM tasks WHERE id = ?', (self.task_id,))
            result = cursor.fetchone()
            conn.close()
            if result:
                task_text, description, due_date, due_time, priority, status = result
                self.task_input.setText(task_text)
                self.description_input.setText(description)
                if due_date:
                    self.date_edit.setDate(QDate.fromString(due_date, 'yyyy-MM-dd'))
                else:
                    self.date_edit.setDate(QDate.currentDate())
                if due_time:
                    self.time_edit.setTime(QTime.fromString(due_time, 'HH:mm'))
                else:
                    self.time_edit.setTime(QTime.currentTime())
                index = self.priority_combo.findText(priority)
                if index != -1:
                    self.priority_combo.setCurrentIndex(index)
                else:
                    self.priority_combo.setCurrentIndex(1)  # Средний
                index = self.status_combo.findText(status)
                if index != -1:
                    self.status_combo.setCurrentIndex(index)
                else:
                    self.status_combo.setCurrentIndex(0)  # Сделать
            else:
                QMessageBox.warning(self, 'Ошибка', 'Задача не найдена в базе данных.')
                self.reject()
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось загрузить данные задачи.\n{e}')
            self.reject()

    def get_values(self):
        task_text = self.task_input.text().strip()
        description = self.description_input.toPlainText().strip()
        due_date = self.date_edit.date().toString('yyyy-MM-dd')
        due_time = self.time_edit.time().toString('HH:mm')
        priority = self.priority_combo.currentText()
        status = self.status_combo.currentText()
        return task_text, description, due_date, due_time, priority, status

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        window = TaskManager()
        window.resize(1600, 700)  # Увеличиваем размер основного окна для удобства
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, 'Критическая ошибка', f'Произошла непредвиденная ошибка:\n{e}')
        sys.exit(1)
