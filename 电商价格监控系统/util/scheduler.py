import time
import json
import os
import traceback
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

BASE_DIR = r""


class TaskThread(QThread):
    # 添加新信号用于价格提醒
    price_alert = pyqtSignal(str, str, float, float, str)  # asin, title, current_price, threshold, url

    def __init__(self, row_index, asin, window):
        super().__init__()
        self.row_index = row_index
        self.asin = asin
        self.window = window
        self.terminate = False
        self.threshold_price = 0.0

    def run(self):
        # 获取阈值价格
        price_item = self.window.table_widget.item(self.row_index, 3)
        if price_item:
            try:
                self.threshold_price = float(price_item.text())
            except ValueError:
                self.threshold_price = 0.0

        # 获取商品URL
        url = ""
        url_item = self.window.table_widget.item(self.row_index, 2)
        if url_item:
            url = url_item.text()

        # 获取频率
        frequency = 5
        frequency_item = self.window.table_widget.item(self.row_index, 7)
        if frequency_item:
            try:
                frequency = int(frequency_item.text())
            except ValueError:
                frequency = 5

        # 监控循环
        while not self.terminate:
            try:
                # 模拟价格获取
                current_price = self.get_current_price()

                # 更新成功次数
                success_item = self.window.table_widget.item(self.row_index, 4)
                if success_item:
                    count = int(success_item.text() or "0") + 1
                    success_item.setText(str(count))

                # 检查价格是否低于阈值
                if current_price < self.threshold_price:
                    # 获取商品标题
                    title = ""
                    title_item = self.window.table_widget.item(self.row_index, 1)
                    if title_item:
                        title = title_item.text()

                    # 发出价格提醒信号
                    self.price_alert.emit(
                        self.asin,
                        title,
                        current_price,
                        self.threshold_price,
                        url
                    )

                    # 更新状态为"完成并提醒"
                    status_item = self.window.table_widget.item(self.row_index, 6)
                    if status_item:
                        status_item.setText("完成并提醒")

                # 保存数据到JSON文件
                self.save_to_json(current_price)

                # 等待下一次执行
                time.sleep(frequency)

            except Exception as e:
                # 更新错误次数
                error_item = self.window.table_widget.item(self.row_index, 5)
                if error_item:
                    count = int(error_item.text() or "0") + 1
                    error_item.setText(str(count))

                # 记录错误日志
                self.window.log_message(self.asin, f"监控错误: {str(e)}", "ERROR")
                time.sleep(10)

    def get_current_price(self):
        """模拟获取当前价格（实际应用中应替换为真实爬取逻辑）"""
        # 这里应该实现真实的爬取逻辑
        # 返回一个随机价格用于演示
        import random
        return round(random.uniform(10, 50), 2)

    def save_to_json(self, current_price):
        """保存数据到JSON文件"""
        db_path = os.path.join(BASE_DIR, 'db', 'db.json')
        try:
            if os.path.exists(db_path):
                with open(db_path, 'r', encoding='utf-8') as f:
                    data_list = json.load(f)
            else:
                data_list = []

            # 查找并更新当前商品的数据
            updated = False
            for item in data_list:
                if item.get("asin") == self.asin:
                    item["success"] = int(self.window.table_widget.item(self.row_index, 4).text() or "0")
                    item["error"] = int(self.window.table_widget.item(self.row_index, 5).text() or "0")
                    item["status"] = "完成并提醒" if current_price < self.threshold_price else "待执行"
                    item["current_price"] = current_price
                    updated = True
                    break

            # 如果未找到，创建新条目
            if not updated:
                new_item = {
                    "asin": self.asin,
                    "title": self.window.table_widget.item(self.row_index, 1).text(),
                    "url": self.window.table_widget.item(self.row_index, 2).text(),
                    "price": self.threshold_price,
                    "success": int(self.window.table_widget.item(self.row_index, 4).text() or "0"),
                    "error": int(self.window.table_widget.item(self.row_index, 5).text() or "0"),
                    "status": "完成并提醒" if current_price < self.threshold_price else "待执行",
                    "frequency": int(self.window.table_widget.item(self.row_index, 7).text() or "5"),
                    "current_price": current_price
                }
                data_list.append(new_item)

            # 保存数据
            with open(db_path, 'w', encoding='utf-8') as f:
                json.dump(data_list, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.window.log_message(self.asin, f"保存数据失败: {str(e)}", "ERROR")


class Scheduler(object):
    def __init__(self):
        self.thread_list = []
        self.window = None
        self.terminate = False  # 点击停止

    def start(self, window, fn_start):
        self.window = window
        self.terminate = False

        # 清空之前的线程列表
        self.thread_list.clear()

        # 1.获取表格中的所有数据，每一行创建一个线程去执行监控
        for row_index in range(window.table_widget.rowCount()):
            asin = window.table_widget.item(row_index, 0).text().strip()
            status_text = window.table_widget.item(row_index, 6).text().strip()

            if status_text == '待执行':
                # 2.每个线程执行&状态实时的显示在表格中 信号+回调
                t = TaskThread(row_index, asin, window)
                t.start_signal.connect(fn_start)

                # 连接价格提醒信号
                t.price_alert.connect(window.handle_price_alert)

                t.start()
                self.thread_list.append(t)  # 保存线程引用

    def stop(self):
        self.terminate = True
        for thread in self.thread_list:
            thread.terminate = True  # 通知线程停止
            thread.wait(1000)  # 等待线程结束


SCHEDULER = Scheduler()