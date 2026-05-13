"""
图形界面客户端
"""

import os
import threading
from tkinter import *
from tkinter import ttk, messagebox, filedialog

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from client.connection_manager import ConnectionManager
from client.downloader import StreamDownloader
from shared.logger import setup_logger


class FileP2PClientGUI:
    """文件下载客户端GUI"""
    
    def __init__(self):
        self.root = Tk()
        self.root.title("FileP2P - 文件接收客户端")
        self.root.geometry("900x650")
        
        # 连接管理器
        self.conn_mgr = ConnectionManager()
        self.logger = setup_logger('ClientGUI', 'logs/client_gui.log')
        
        # 下载目录
        self.download_dir = os.path.expanduser("~/Downloads")
        
        # 下载任务管理
        self.download_tasks = {}
        
        self._setup_ui()
        self._center_window()
    
    def _setup_ui(self):
        """设置界面"""
        # 连接区域
        conn_frame = LabelFrame(self.root, text="服务器连接", padx=10, pady=10)
        conn_frame.pack(fill=X, padx=10, pady=5)
        
        Label(conn_frame, text="服务器地址:").grid(row=0, column=0, sticky=E, padx=5)
        self.host_entry = Entry(conn_frame, width=25)
        self.host_entry.grid(row=0, column=1, padx=5)
        self.host_entry.insert(0, "127.0.0.1")
        
        Label(conn_frame, text="端口:").grid(row=0, column=2, sticky=E, padx=5)
        self.port_entry = Entry(conn_frame, width=8)
        self.port_entry.grid(row=0, column=3, padx=5)
        self.port_entry.insert(0, "8848")
        
        self.connect_btn = Button(
            conn_frame, text="连接", command=self._connect,
            bg="#4CAF50", fg="white", width=10
        )
        self.connect_btn.grid(row=0, column=4, padx=10)
        
        self.status_label = Label(conn_frame, text="未连接", fg="red")
        self.status_label.grid(row=0, column=5, padx=10)
        
        # 文件列表区域
        list_frame = LabelFrame(self.root, text="可用文件", padx=10, pady=10)
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # 工具栏
        toolbar = Frame(list_frame)
        toolbar.pack(fill=X, pady=5)
        
        Button(toolbar, text="刷新", command=self._refresh_files, width=8).pack(side=LEFT, padx=2)
        Button(toolbar, text="全选", command=self._select_all, width=8).pack(side=LEFT, padx=2)
        Button(toolbar, text="取消", command=self._deselect_all, width=8).pack(side=LEFT, padx=2)
        Button(
            toolbar, text="下载选中", command=self._download_selected,
            bg="#2196F3", fg="white", width=10
        ).pack(side=RIGHT, padx=2)
        
        Button(
            toolbar, text="更改目录", command=self._change_download_dir, width=10
        ).pack(side=RIGHT, padx=2)
        
        # 文件列表
        columns = ("选择", "文件名", "大小", "修改时间")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")
        
        self.tree.heading("选择", text="☐")
        self.tree.heading("文件名", text="文件名")
        self.tree.heading("大小", text="大小")
        self.tree.heading("修改时间", text="修改时间")
        
        self.tree.column("选择", width=40, anchor=CENTER)
        self.tree.column("文件名", width=350)
        self.tree.column("大小", width=100, anchor=E)
        self.tree.column("修改时间", width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 双击下载
        self.tree.bind("<Double-1>", self._on_double_click)
        
        # 进度区域
        progress_frame = LabelFrame(self.root, text="下载进度", padx=10, pady=10)
        progress_frame.pack(fill=X, padx=10, pady=5)
        
        self.progress_var = DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=X, pady=5)
        
        self.progress_label = Label(progress_frame, text="就绪")
        self.progress_label.pack()
        
        self.speed_label = Label(progress_frame, text="", fg="gray")
        self.speed_label.pack()
        
        # 状态栏
        self.statusbar = Label(
            self.root,
            text=f"下载目录: {self.download_dir}",
            relief=SUNKEN, anchor=W
        )
        self.statusbar.pack(side=BOTTOM, fill=X)
    
    def _center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')
    
    def _connect(self):
        """连接到服务器"""
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not host or not port:
            messagebox.showwarning("提示", "请输入服务器地址和端口")
            return
        
        try:
            port = int(port)
        except ValueError:
            messagebox.showwarning("提示", "端口必须是数字")
            return
        
        self.connect_btn.config(text="连接中...", state=DISABLED)
        self.root.update()
        
        def do_connect():
            success, msg = self.conn_mgr.connect(host, port)
            self.root.after(0, lambda: self._on_connect_result(success, msg))
        
        threading.Thread(target=do_connect, daemon=True).start()
    
    def _on_connect_result(self, success, message):
        """连接结果回调"""
        self.connect_btn.config(text="连接", state=NORMAL)
        
        if success:
            self.status_label.config(text="已连接", fg="green")
            self._refresh_files()
        else:
            self.status_label.config(text="连接失败", fg="red")
            messagebox.showerror("连接失败", message)
    
    def _refresh_files(self):
        """刷新文件列表"""
        if not self.conn_mgr.connected:
            messagebox.showinfo("提示", "请先连接到服务器")
            return
        
        # 清空列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 获取文件列表
        files = self.conn_mgr.get_file_list()
        
        for f in files:
            size_str = self._format_size(f.get('size', 0))
            self.tree.insert("", END, values=("☐", f['name'], size_str, f.get('modified', '')))
        
        self.statusbar.config(text=f"共 {len(files)} 个文件")
    
    def _select_all(self):
        """全选"""
        for item in self.tree.get_children():
            values = list(self.tree.item(item)['values'])
            values[0] = "☑"
            self.tree.item(item, values=values)
    
    def _deselect_all(self):
        """取消全选"""
        for item in self.tree.get_children():
            values = list(self.tree.item(item)['values'])
            values[0] = "☐"
            self.tree.item(item, values=values)
    
    def _on_double_click(self, event):
        """双击下载文件"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            filename = self.tree.item(item)['values'][1]
            self._download_file(filename)
    
    def _download_selected(self):
        """下载选中的文件"""
        selected = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values[0] == "☑":
                selected.append(values[1])
        
        if not selected:
            messagebox.showinfo("提示", "请先选择要下载的文件")
            return
        
        for filename in selected:
            self._download_file(filename)
    
    def _download_file(self, filename):
        """下载单个文件"""
        # 更新UI
        self.progress_var.set(0)
        self.progress_label.config(text=f"正在下载: {filename}")
        self.speed_label.config(text="")
        
        def progress_callback(downloaded, total, speed):
            """进度更新回调"""
            if total > 0:
                percent = (downloaded / total) * 100
                self.progress_var.set(percent)
            
            downloaded_str = self._format_size(downloaded)
            total_str = self._format_size(total) if total > 0 else "未知"
            speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed > 0 else ""
            
            self.progress_label.config(
                text=f"{filename}: {downloaded_str} / {total_str}"
            )
            self.speed_label.config(text=speed_str)
        
        def do_download():
            from client.downloader import StreamDownloader
            downloader = StreamDownloader()
            
            success, msg, file_path = downloader.download(
                url=f"{self.conn_mgr.server_url}/api/download/{filename}",
                save_path=self.download_dir,
                progress_callback=progress_callback
            )
            
            self.root.after(0, lambda: self._on_download_complete(success, msg, file_path))
        
        threading.Thread(target=do_download, daemon=True).start()
    
    def _on_download_complete(self, success, message, file_path):
        """下载完成回调"""
        self.progress_label.config(text="就绪")
        self.speed_label.config(text="")
        self.progress_var.set(0)
        
        if success:
            if messagebox.askyesno("下载完成", f"{message}\n\n是否打开文件所在文件夹?"):
                os.startfile(os.path.dirname(file_path))
        else:
            messagebox.showerror("下载失败", message)
    
    def _change_download_dir(self):
        """更改下载目录"""
        new_dir = filedialog.askdirectory(initialdir=self.download_dir)
        if new_dir:
            self.download_dir = new_dir
            self.statusbar.config(text=f"下载目录: {self.download_dir}")
    
    @staticmethod
    def _format_size(size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def run(self):
        """启动GUI"""
        self.root.mainloop()


def main():
    gui = FileP2PClientGUI()
    gui.run()


if __name__ == '__main__':
    main()