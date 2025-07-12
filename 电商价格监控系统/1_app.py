import sys
import traceback
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG
from PyQt5.QtWidgets import (
    QWidget, QApplication, QDesktopWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLineEdit, QMessageBox,
    QTableWidget, QTableWidgetItem,QLabel,QCheckBox,QDialog, QFormLayout,QMenu,QTextEdit
)
import os
import json
import time
from util.thread import NewTaskThread
import smtplib
from email.mime.text import MIMEText
from util.dialogs import ProxyDialog
from util.scheduler import  SCHEDULER

#根据自身情况修改路径
BASE_DIR = r""

status_mapping = {
        0: "初始化中",
        1: "待执行",
        2: "正在执行",
        3: "完成并提醒",
        10: "异常并停止",
        11: "初始化失败"
    }


class LogDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.threads = {}  # 存储线程的字典
        self.table_widget = None  # 表格控件
        self.SCHEDULER = SCHEDULER

        # 确保配置目录存在
        config_dir = os.path.join(BASE_DIR, 'config')
        os.makedirs(config_dir, exist_ok=True)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 添加刷新按钮
        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("刷新日志")
        btn_refresh.clicked.connect(self.load_log)
        btn_layout.addWidget(btn_refresh)

        btn_clear = QPushButton("清除日志")
        btn_clear.clicked.connect(self.clear_log)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        # 日志显示区域
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFontFamily("Consolas")  # 使用等宽字体
        layout.addWidget(self.text_edit)

        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        self.setLayout(layout)
        self.load_log()

    def load_log(self):
        """加载日志内容"""
        log_path = self.get_log_path()

        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.text_edit.setText(content)
                    # 滚动到底部
                    self.text_edit.verticalScrollBar().setValue(
                        self.text_edit.verticalScrollBar().maximum()
                    )
            except Exception as e:
                self.text_edit.setText(f"⚠️ 读取日志失败: {str(e)}")
        else:
            self.text_edit.setText("⚠️ 该ASIN暂无日志记录")

    def clear_log(self):
        """清除日志文件"""
        log_path = self.get_log_path()
        if os.path.exists(log_path):
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
                QMessageBox.information(self, "成功", "日志已清空！")
                self.load_log()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"清除日志失败: {str(e)}")
        else:
            QMessageBox.warning(self, "提示", "日志文件不存在！")

    def get_log_path(self):
        """获取日志文件路径"""
        log_dir = "log"
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, f"{self.asin}.log")
class MainWindow(QWidget):
    status_mapping = {
        0: "初始化中",
        1: "待执行",
        2: "正在执行",
        3: "完成并提醒",
        10: "异常并停止",
        11: "初始化失败"
    }

    def __init__(self):
        super().__init__()
        self.threads = {}  # 存储线程的字典
        self.table_widget = None  # 表格控件
        self.SCHEDULER = SCHEDULER
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('亚马逊监测平台')
        self.resize(1228, 550)

        # 窗体居中
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        layout = QVBoxLayout()
        layout.addLayout(self.init_header())
        layout.addLayout(self.init_form())
        layout.addLayout(self.init_table())
        layout.addLayout(self.init_footer())
        layout.addStretch(1)
        self.setLayout(layout)
        self.show()

    def init_header(self):
        header = QHBoxLayout()
        btn_start = QPushButton('开始')
        btn_start.clicked.connect(self.event_start_click)
        header.addWidget(btn_start)
        btn_stop = QPushButton('结束')
        btn_stop.clicked.connect(self.event_stop_click)
        header.addWidget(btn_stop)
        header.addStretch(1)
        return header

    def init_form(self):
        form = QHBoxLayout()
        self.txt_asin = QLineEdit()
        self.txt_asin.setPlaceholderText('请输入商品ASIN并且多个用逗号进行分隔，如：B0815JJQQB=18,B0815JJQQ9=19')
        form.addWidget(self.txt_asin)
        btn_add = QPushButton('添加')
        btn_add.clicked.connect(self.event_add_click)
        form.addWidget(btn_add)
        return form

    def init_table(self):
        table_layout = QHBoxLayout()
        self.table_widget = QTableWidget(0, 8)  # 保存为实例变量

        table_header_list = [
            {"field": "asin", "text": "ASIN", "width": 120},
            {"field": "title", "text": "标题", "width": 150},
            {"field": "url", "text": "URL", "width": 400},
            {"field": "price", "text": "底价", "width": 100},
            {"field": "success", "text": "成功次数", "width": 100},
            {"field": "error", "text": "503次数", "width": 100},
            {"field": "status", "text": "状态", "width": 100},
            {"field": "frequency", "text": "频率（N秒/次）", "width": 100},
        ]

        for index, info in enumerate(table_header_list):
            self.table_widget.setColumnWidth(index, info['width'])
            item = QTableWidgetItem(info['text'])
            self.table_widget.setHorizontalHeaderItem(index, item)
            # 设置右键菜单策略
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.table_right_menu)
        # 加载数据
        try:
            db_path = os.path.join(BASE_DIR, 'db', 'db.json')
            if os.path.exists(db_path):
                with open(db_path, 'r', encoding='utf-8') as f:
                    data_list = json.load(f)
                for item in data_list:
                    row = self.table_widget.rowCount()
                    self.table_widget.insertRow(row)
                    self.create_row(self.table_widget, item, row)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据失败: {str(e)}")

        table_layout.addWidget(self.table_widget)
        return table_layout

    def table_right_menu(self, pos):
        """表格右键菜单逻辑"""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            return

        first_item = selected_items[0]
        row_index = first_item.row()
        asin = self.table_widget.item(row_index, 0).text().strip()

        # 创建右键菜单
        menu = QMenu()
        item_copy = menu.addAction("复制")
        item_log = menu.addAction("查看日志")
        item_log_clear = menu.addAction("清除日志")

        action = menu.exec_(self.table_widget.mapToGlobal(pos))

        if action == item_copy:
            clipboard = QApplication.clipboard()
            clipboard.setText(first_item.text())

        elif action == item_log:
            dialog = LogDialog(asin, self)
            dialog.exec_()

        elif action == item_log_clear:
            log_dir = "log"
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, f"{asin}.log")

            if os.path.exists(log_path):
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
                QMessageBox.information(self, "成功", "日志已清空！")
            else:
                QMessageBox.warning(self, "提示", "日志文件不存在！")

    def create_row(self, table_widget, item, row_idx):
        columns = ["asin", "title", "url", "price", "success", "error", "status", "frequency"]
        for col_idx, field in enumerate(columns):
            value = item.get(field, "")
            if field == "status":
                status_value = int(value) if isinstance(value, (int, float)) else 0
                text = self.status_mapping.get(status_value, "未知状态")
            else:
                text = str(value)
            cell = QTableWidgetItem(text)
            if field in ["asin", "success", "error", "status"]:
                cell.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            table_widget.setItem(row_idx, col_idx, cell)

    def init_footer(self):
        footer = QHBoxLayout()

        # 左侧状态标签
        self.lable_status = QLabel("未检测", self)
        footer.addWidget(self.lable_status)

        # 添加弹簧，使按钮靠右对齐
        footer.addStretch(1)

        # 右侧功能按钮
        btn_reinit = QPushButton("重新初始化", self)
        btn_reinit.clicked.connect(self.event_reset_click)
        footer.addWidget(btn_reinit)

        btn_reset_count = QPushButton("次数清零", self)
        btn_reset_count.clicked.connect(self.event_reset_count_click)
        footer.addWidget(btn_reset_count)

        btn_delete = QPushButton("删除检测", self)
        btn_delete.clicked.connect(self.event_delete_click)
        footer.addWidget(btn_delete)

        btn_alarm = QPushButton("SMTP报警配置", self)
        btn_alarm.clicked.connect(self.event_alarm_config_click)
        footer.addWidget(btn_alarm)

        btn_proxy = QPushButton("代理IP", self)
        btn_proxy.clicked.connect(self.event_proxy_config_click)
        footer.addWidget(btn_proxy)

        return footer

    def event_start_click(self):
        SCHEDULER.start(
            self,
            self.task_start_callback
        )

        self.update_status_message('执行中')
    def task_start_callback(self,row_index):
        cell_status=QTableWidgetItem(status_mapping[2])
        cell_status.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        self.table_widget.setItem(row_index,6,cell_status)

    def event_stop_click(self):
        SCHEDULER.stop()
        self.update_status_message('已停止')

    def update_status_message(self,message):
        self.lable_status.setText(message)
        self.lable_status.repaint()

    def event_add_click(self):
        text = self.txt_asin.text().strip()
        if not text:
            QMessageBox.warning(self, "错误", "请输入商品ASIN")
            return

        # 解析输入的ASIN和价格
        asin_pairs = []
        for pair in text.split(','):
            pair = pair.strip()
            if not pair:
                continue
            if '=' not in pair:
                QMessageBox.warning(self, "格式错误", f"格式不正确: {pair}")
                return
            asin, price_str = pair.split('=', 1)
            asin = asin.strip()
            try:
                price = float(price_str.strip())
            except ValueError:
                QMessageBox.warning(self, "价格错误", f"价格格式错误: {price_str}")
                return
            asin_pairs.append((asin, price))

        if not asin_pairs:
            QMessageBox.warning(self, "错误", "未找到有效的商品信息")
            return

        # 读取现有数据
        db_path = os.path.join(BASE_DIR, 'db', 'db.json')
        try:
            if os.path.exists(db_path):
                with open(db_path, 'r', encoding='utf-8') as f:
                    data_list = json.load(f)
            else:
                data_list = []
        except Exception as e:
            QMessageBox.warning(self, "错误", f"读取数据库失败: {str(e)}")
            data_list = []

        # 添加新商品
        added_count = 0
        for asin, price in asin_pairs:
            # 检查是否已存在
            if any(item["asin"] == asin for item in data_list):
                continue

            # 创建新记录
            new_item = {
                "asin": asin,
                "title": "",
                "url": f"https://www.amazon.com/dp/{asin}",
                "price": price,
                "success": 0,
                "error": 0,
                "status": 0,  # 初始化中
                "frequency": 5
            }
            self.log_message(asin, f"添加商品监控，底价: ${price}")

            # 添加到表格
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)
            self.create_row(self.table_widget, new_item, row)

            self.log_message(asin, "启动初始化线程")

            # 保存到数据库
            data_list.append(new_item)
            added_count += 1

            # 启动初始化线程
            thread = NewTaskThread(row, asin)
            thread.success.connect(self.on_crawl_success)
            thread.error.connect(self.on_crawl_error)
            thread.start()
            self.threads[row] = thread

        # 保存数据库
        try:
            with open(db_path, 'w', encoding='utf-8') as f:
                json.dump(data_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存数据库失败: {str(e)}")

        if added_count > 0:
            QMessageBox.information(self, "成功", f"已添加 {added_count} 个商品")
            self.txt_asin.clear()

    def on_crawl_success(self, row_index, asin, title, url):
        self.log_message(asin, f"初始化成功，标题: {title}")
        # 直接调用UI更新方法（确保在主线程中）
        QMetaObject.invokeMethod(
            self,
            "update_table_success",
            Qt.QueuedConnection,
            Q_ARG(int, row_index),
            Q_ARG(str, asin),
            Q_ARG(str, title),
            Q_ARG(str, url)
        )

    def on_crawl_error(self, row_index, asin, error_type, message):
        self.log_message(asin, f"初始化失败: {error_type} - {message}", "ERROR")
        # 直接调用UI更新方法（确保在主线程中）
        QMetaObject.invokeMethod(
            self,
            "update_table_error",
            Qt.QueuedConnection,
            Q_ARG(int, row_index),
            Q_ARG(str, asin),
            Q_ARG(str, error_type),
            Q_ARG(str, message)
        )

    def event_reset_click(self):
        row_list = self.table_widget.selectionModel().selectedRows()
        if not row_list:
            QMessageBox.warning(self, "错误", "请选择要重新初始化的行")
            return

        for row_object in row_list:
            index = row_object.row()
            print("选中的行：", index)

            # 获取ASIN
            asin_item = self.table_widget.item(index, 0)
            if not asin_item:
                continue
            asin = asin_item.text()

            # 更新状态为"初始化中"
            cell_status = QTableWidgetItem(self.status_mapping[0])
            cell_status.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_widget.setItem(index, 6, cell_status)

            # 创建并启动新线程
            thread = NewTaskThread(index, asin)  # 使用正确的行索引和ASIN
            thread.success.connect(self.on_crawl_success)
            thread.error.connect(self.on_crawl_error)  # 修正信号连接
            thread.start()
            self.threads[index] = thread  # 保存线程引用

    def event_delete_click(self):
        selected_rows = self.table_widget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请选择要操作的行")
            return

        #翻转
        selected_rows.reverse()

        for row_object in selected_rows:
            index = row_object.row()
            self.table_widget.removeRow(index)

    def event_reset_count_click(self):
        # 次数清零功能实现
        selected_rows = self.table_widget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请选择要操作的行")
            return

        for row_object in selected_rows:
            index=row_object.row()
            cell_status = QTableWidgetItem(str(0))
            cell_status.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_widget.setItem(index, 4, cell_status)

            cell_status = QTableWidgetItem(str(0))
            cell_status.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_widget.setItem(index, 5, cell_status)

    def event_alarm_config_click(self):
        # 创建报警配置对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("SMTP报警配置")
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)

        # SMTP服务器配置
        form_layout = QFormLayout()

        self.smtp_server = QLineEdit()
        self.smtp_port = QLineEdit()
        self.smtp_ssl = QCheckBox("使用SSL")
        self.smtp_ssl.setChecked(True)
        self.smtp_user = QLineEdit()
        self.smtp_password = QLineEdit()
        self.smtp_password.setEchoMode(QLineEdit.Password)
        self.smtp_from = QLineEdit()
        self.smtp_to = QLineEdit()

        form_layout.addRow("SMTP服务器:", self.smtp_server)
        form_layout.addRow("端口:", self.smtp_port)
        form_layout.addRow("", self.smtp_ssl)
        form_layout.addRow("用户名:", self.smtp_user)
        form_layout.addRow("密码:", self.smtp_password)
        form_layout.addRow("发件人:", self.smtp_from)
        form_layout.addRow("收件人:", self.smtp_to)

        layout.addLayout(form_layout)

        # 加载已保存的配置
        self.load_smtp_config()

        # 按钮区域
        btn_layout = QHBoxLayout()

        btn_test = QPushButton("测试连接")
        btn_test.clicked.connect(lambda: self.test_smtp_connection(dialog))
        btn_layout.addWidget(btn_test)

        btn_save = QPushButton("保存配置")
        btn_save.clicked.connect(lambda: self.save_smtp_config(dialog))
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(dialog.close)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

        dialog.exec_()

    def load_smtp_config(self):
        # 从配置文件加载SMTP设置
        config_path = os.path.join(BASE_DIR, 'config', 'smtp.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.smtp_server.setText(config.get('server', ''))
                self.smtp_port.setText(str(config.get('port', 465)))
                self.smtp_ssl.setChecked(config.get('use_ssl', True))
                self.smtp_user.setText(config.get('user', ''))
                self.smtp_password.setText(config.get('password', ''))
                self.smtp_from.setText(config.get('from', ''))
                self.smtp_to.setText(config.get('to', ''))
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载配置失败: {str(e)}")

    def save_smtp_config(self, dialog):
        # 保存SMTP配置
        config = {
            'server': self.smtp_server.text(),
            'port': int(self.smtp_port.text() or 465),
            'use_ssl': self.smtp_ssl.isChecked(),
            'user': self.smtp_user.text(),
            'password': self.smtp_password.text(),
            'from': self.smtp_from.text(),
            'to': self.smtp_to.text()
        }

        config_dir = os.path.join(BASE_DIR, 'config')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        config_path = os.path.join(config_dir, 'smtp.json')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "成功", "SMTP配置已保存")
            dialog.close()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存配置失败: {str(e)}")

    def test_smtp_connection(self, dialog):
        # 测试SMTP连接
        try:
            server = self.smtp_server.text()
            port = int(self.smtp_port.text() or 465)
            use_ssl = self.smtp_ssl.isChecked()
            user = self.smtp_user.text()
            password = self.smtp_password.text()
            from_addr = self.smtp_from.text()
            to_addr = self.smtp_to.text()

            if not server or not user or not password or not from_addr or not to_addr:
                QMessageBox.warning(self, "错误", "请填写完整的SMTP配置")
                return

            # 尝试连接SMTP服务器
            if use_ssl:
                smtp = smtplib.SMTP_SSL(server, port)
            else:
                smtp = smtplib.SMTP(server, port)
                smtp.starttls()

            smtp.login(user, password)

            # 发送测试邮件
            msg = MIMEText("这是一封测试邮件，用于验证SMTP报警配置是否正确。")
            msg['Subject'] = "亚马逊价格监控系统 - 测试邮件"
            msg['From'] = from_addr
            msg['To'] = to_addr

            smtp.sendmail(from_addr, [to_addr], msg.as_string())
            smtp.quit()

            QMessageBox.information(self, "成功", "SMTP连接测试成功！已发送测试邮件。")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"SMTP连接测试失败: {str(e)}")

    def event_proxy_config_click(self):
        """打开代理配置对话框"""
        dialog = ProxyDialog(self)
        dialog.exec_()

    def get_selected_rows(self):
        # 获取选中的行索引
        selected_rows = []
        for index in self.table_widget.selectionModel().selectedRows():
            selected_rows.append(index.row())
        return selected_rows

    # 使用QtCore.pyqtSlot装饰器明确方法签名
    from PyQt5.QtCore import pyqtSlot

    @pyqtSlot(int, str, str, str)
    def update_table_success(self, row_index, asin, title, url):
        # 检查行索引是否有效
        if row_index >= self.table_widget.rowCount():
            print(f"无效的行索引: {row_index}")
            return

        # 更新标题
        title_item = self.table_widget.item(row_index, 1)
        if title_item:
            title_item.setText(title)
        else:
            self.table_widget.setItem(row_index, 1, QTableWidgetItem(title))

        # 更新URL
        url_item = self.table_widget.item(row_index, 2)
        if url_item:
            url_item.setText(url)
        else:
            self.table_widget.setItem(row_index, 2, QTableWidgetItem(url))

        # 更新状态为"待执行"
        status_item = self.table_widget.item(row_index, 6)
        if status_item:
            status_item.setText(self.status_mapping[1])
        else:
            self.table_widget.setItem(row_index, 6, QTableWidgetItem(self.status_mapping[1]))

        # 更新成功次数
        success_item = self.table_widget.item(row_index, 4)
        if success_item:
            count = int(success_item.text() or "0") + 1
            success_item.setText(str(count))
        else:
            self.table_widget.setItem(row_index, 4, QTableWidgetItem("1"))

        # 更新JSON数据
        self.update_json_data(row_index, {
            "title": title,
            "url": url,
            "status": 1,
            "success": int(success_item.text() or "0") + 1
        })

    @pyqtSlot(int, str, str, str)
    def update_table_error(self, row_index, asin, error_type, message):
        # 检查行索引是否有效
        if row_index >= self.table_widget.rowCount():
            print(f"无效的行索引: {row_index}")
            return

        # 更新状态
        status_code = 11 if error_type == "503" else 10
        status_text = self.status_mapping[status_code]

        status_item = self.table_widget.item(row_index, 6)
        if status_item:
            status_item.setText(status_text)
        else:
            self.table_widget.setItem(row_index, 6, QTableWidgetItem(status_text))

        # 更新错误次数（503错误）
        if error_type == "503":
            error_item = self.table_widget.item(row_index, 5)
            if error_item:
                count = int(error_item.text() or "0") + 1
                error_item.setText(str(count))
            else:
                self.table_widget.setItem(row_index, 5, QTableWidgetItem("1"))

        # 更新JSON数据
        updates = {"status": status_code}
        if error_type == "503":
            updates["error"] = int(error_item.text() or "0") + 1
        self.update_json_data(row_index, updates)

        # 显示错误消息
        if error_type != "503":  # 只显示非503错误
            QMessageBox.warning(self, "错误", f"商品 {asin} 初始化失败: {message}")

    def update_json_data(self, row_index, updates):
        db_path = os.path.join(BASE_DIR, 'db', 'db.json')
        try:
            if os.path.exists(db_path):
                with open(db_path, 'r', encoding='utf-8') as f:
                    data_list = json.load(f)
                if 0 <= row_index < len(data_list):
                    data_list[row_index].update(updates)
                    with open(db_path, 'w', encoding='utf-8') as f:
                        json.dump(data_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"更新数据失败: {str(e)}")

    def log_message(self, asin, message, level="INFO"):
        """记录日志消息"""
        log_dir = "log"
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{asin}.log")

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            print(f"记录日志失败: {str(e)}")

    def handle_price_alert(self, asin, title, current_price, threshold_price, url):
        """处理价格提醒"""
        # 记录日志
        self.log_message(asin, f"价格低于阈值！当前价格: ${current_price:.2f}, 阈值: ${threshold_price:.2f}")

        # 显示提示框
        QMessageBox.information(
            self,
            "价格提醒",
            f"商品 {title} 价格低于设定阈值！\n\n"
            f"当前价格: ${current_price:.2f}\n"
            f"设定阈值: ${threshold_price:.2f}\n"
            f"ASIN: {asin}"
        )

        # 尝试发送邮件提醒
        self.send_price_alert_email(asin, title, current_price, threshold_price, url)

    def send_price_alert_email(self, asin, title, current_price, threshold_price, url):
        """发送价格提醒邮件"""
        # 检查配置文件是否存在
        config_path = os.path.join(BASE_DIR, 'config', 'smtp.json')
        if not os.path.exists(config_path):
            self.log_message(asin, "无法发送提醒邮件：未配置SMTP设置", "WARNING")

            # 提示用户配置SMTP
            QMessageBox.warning(
                self,
                "SMTP配置缺失",
                "检测到价格低于阈值，但未配置SMTP邮件提醒功能。\n\n"
                "请点击'SMTP报警配置'按钮配置邮件提醒功能。"
            )
            return

        try:
            # 加载SMTP配置
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            self.log_message(asin, f"读取SMTP配置失败: {str(e)}", "ERROR")
            return

        # 构建邮件内容
        subject = f"价格提醒: {title} 低于设定阈值!"
        body = (
            f"监控到以下商品价格低于您设定的阈值：\n\n"
            f"商品标题: {title}\n"
            f"ASIN: {asin}\n"
            f"当前价格: ${current_price:.2f}\n"
            f"设定阈值: ${threshold_price:.2f}\n"
            f"商品链接: {url}\n\n"
            f"请尽快查看！"
        )

        try:
            # 发送邮件
            server = config['server']
            port = config['port']
            use_ssl = config.get('use_ssl', True)
            user = config['user']
            password = config['password']
            from_addr = config['from']
            to_addr = config['to']

            # 创建邮件
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = from_addr
            msg['To'] = to_addr

            # 连接SMTP服务器
            if use_ssl:
                smtp = smtplib.SMTP_SSL(server, port)
            else:
                smtp = smtplib.SMTP(server, port)
                smtp.starttls()

            smtp.login(user, password)
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
            smtp.quit()

            # 记录日志
            self.log_message(asin, f"已发送价格提醒邮件到 {to_addr}")

        except Exception as e:
            self.log_message(asin, f"发送邮件失败: {str(e)}", "ERROR")

    def event_alarm_config_click(self):
        # 确保配置目录存在
        config_dir = os.path.join(BASE_DIR, 'config')
        os.makedirs(config_dir, exist_ok=True)

        # 配置路径
        config_path = os.path.join(config_dir, 'smtp.json')

        # 如果配置文件不存在，创建默认配置
        if not os.path.exists(config_path):
            default_config = {
                "server": "smtp.example.com",
                "port": 465,
                "use_ssl": True,
                "user": "your_email@example.com",
                "password": "your_password",
                "from": "your_email@example.com",
                "to": "recipient@example.com"
            }
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建默认配置失败: {str(e)}")

        # 创建报警配置对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("SMTP报警配置")
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)

        # SMTP服务器配置
        form_layout = QFormLayout()

        self.smtp_server = QLineEdit()
        self.smtp_port = QLineEdit()
        self.smtp_ssl = QCheckBox("使用SSL")
        self.smtp_ssl.setChecked(True)
        self.smtp_user = QLineEdit()
        self.smtp_password = QLineEdit()
        self.smtp_password.setEchoMode(QLineEdit.Password)
        self.smtp_from = QLineEdit()
        self.smtp_to = QLineEdit()

        form_layout.addRow("SMTP服务器:", self.smtp_server)
        form_layout.addRow("端口:", self.smtp_port)
        form_layout.addRow("", self.smtp_ssl)
        form_layout.addRow("用户名:", self.smtp_user)
        form_layout.addRow("密码:", self.smtp_password)
        form_layout.addRow("发件人:", self.smtp_from)
        form_layout.addRow("收件人:", self.smtp_to)

        layout.addLayout(form_layout)

        # 加载已保存的配置
        self.load_smtp_config()

        # 按钮区域
        btn_layout = QHBoxLayout()

        btn_test = QPushButton("测试连接")
        btn_test.clicked.connect(lambda: self.test_smtp_connection(dialog))
        btn_layout.addWidget(btn_test)

        btn_save = QPushButton("保存配置")
        btn_save.clicked.connect(lambda: self.save_smtp_config(dialog))
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(dialog.close)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

        dialog.exec_()

    def load_smtp_config(self):
        """从配置文件加载SMTP设置"""
        config_path = os.path.join(BASE_DIR, 'config', 'smtp.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.smtp_server.setText(config.get('server', ''))
                self.smtp_port.setText(str(config.get('port', 465)))
                self.smtp_ssl.setChecked(config.get('use_ssl', True))
                self.smtp_user.setText(config.get('user', ''))
                self.smtp_password.setText(config.get('password', ''))
                self.smtp_from.setText(config.get('from', ''))
                self.smtp_to.setText(config.get('to', ''))
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载配置失败: {str(e)}")
                # 创建默认配置
                default_config = {
                    "server": "smtp.example.com",
                    "port": 465,
                    "use_ssl": True,
                    "user": "your_email@example.com",
                    "password": "your_password",
                    "from": "your_email@example.com",
                    "to": "recipient@example.com"
                }
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(default_config, f, indent=2)
                    # 重新加载
                    self.load_smtp_config()
                except Exception as e2:
                    QMessageBox.critical(self, "严重错误", f"创建默认配置失败: {str(e2)}")
        else:
            # 如果配置文件不存在，创建默认配置
            try:
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                default_config = {
                    "server": "smtp.example.com",
                    "port": 465,
                    "use_ssl": True,
                    "user": "your_email@example.com",
                    "password": "your_password",
                    "from": "your_email@example.com",
                    "to": "recipient@example.com"
                }
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                # 重新加载
                self.load_smtp_config()
            except Exception as e:
                QMessageBox.critical(self, "严重错误", f"创建默认配置失败: {str(e)}")


if __name__ == '__main__':
    # 捕获全局异常
    def excepthook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(f"未处理的异常: {tb}")
        QMessageBox.critical(None, "严重错误", f"程序遇到未处理的异常:\n{str(exc_value)}")
        sys.exit(1)


    sys.excepthook = excepthook

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())