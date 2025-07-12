import re
import time
import random
import requests
import bs4
from PyQt5.QtCore import QThread, pyqtSignal


class NewTaskThread(QThread):
    success = pyqtSignal(int, str, str, str)
    error = pyqtSignal(int, str, str, str)

    def __init__(self, row_index, asin, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.row_index = row_index
        self.asin = asin

    def run(self):
        try:
            time.sleep(random.uniform(1.5, 3.5))
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache"
            }

            url_formats = [
                f'https://www.amazon.com/gp/product/{self.asin}/'  # 备用格式
            ]

            resp = None
            for url in url_formats:
                try:
                    resp = requests.get(
                        url=url,
                        headers=headers,
                        timeout=15,
                        allow_redirects=True  # 允许重定向
                    )

                    if resp.status_code == 200:
                        break
                except:
                    continue

            if not resp or resp.status_code != 200:
                raise Exception(f"无法获取商品页面 (HTTP {resp.status_code if resp else '无响应'})")

            # 解析页面内容
            soup = bs4.BeautifulSoup(resp.text, 'lxml')

            title=soup.find(id='productTitle').text.strip()

            tpl="https://www.amazon.com/gp/product/{}"
            url=tpl.format(self.asin)

            self.success.emit(self.row_index, self.asin, title, url)
        except Exception as e:
            title="监控项{}添加失败".format(self.asin)
            self.error.emit(self.row_index, self.asin, "监控项{}添加失败".format(self.asin), str(e))

class TaskThread(QThread):
    start_signal=pyqtSignal(int)
    finished_signal = pyqtSignal(int, str, float)
    def __init__(self,row_index,asin,window,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.row_index=row_index
        self.asin=asin
        self.window=window
        self.terminate = False

    def run(self):
        self.start_signal.emit(self.row_index)
        count = 0
        while not self.terminate and not self.window.SCHEDULER.terminate:
            # 模拟监控工作
            count += 1
            print(f"监控线程 {self.row_index} - ASIN: {self.asin} - 循环 {count}")
            time.sleep(1)  # 模拟工作间隔

        print(f"监控线程 {self.row_index} 已停止")