from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QMessageBox
)
import os


class ProxyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("代理IP配置")
        self.resize(500, 300)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # 1. 代理输入区域
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("""
            每个代理IP占一行，格式为：IP:端口（如 31.40.225.250:3128）  
            支持多个代理（换行分隔），爬虫会自动轮询使用
        """)
        # 加载已有代理
        self.load_proxy()
        main_layout.addWidget(self.text_edit)

        # 2. 底部按钮区域
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()  # 弹簧让按钮右对齐

        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self.save_proxy)
        footer_layout.addWidget(self.btn_save)

        main_layout.addLayout(footer_layout)
        self.setLayout(main_layout)

    def load_proxy(self):
        """从本地文件加载代理IP"""
        proxy_path = os.path.join("db", "proxy.txt")
        # 确保目录存在
        os.makedirs(os.path.dirname(proxy_path), exist_ok=True)

        if os.path.exists(proxy_path):
            with open(proxy_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.text_edit.setText(content)

    def save_proxy(self):
        """将代理IP保存到本地文件"""
        proxy_content = self.text_edit.toPlainText().strip()
        proxy_path = os.path.join("db", "proxy.txt")

        try:
            with open(proxy_path, "w", encoding="utf-8") as f:
                f.write(proxy_content)
            QMessageBox.information(self, "成功", "代理IP配置已保存！")
            self.close()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败：{str(e)}")