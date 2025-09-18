import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
import database
from database import DB_COLUMNS
import threading

# --- Constants ---
HEADER_MAP = {
    'sku': '规格编码',
    'product_id': '货品ID',
    'spec_id': '规格ID',
    'name': '货品名称',
    'spec_name': '规格名称',
    'price': '价格',
    'quantity': '平台库存',
    'shop': '店铺'
}
DISPLAY_COLUMNS = [
    'shop', 'product_id', 'spec_id', 'sku', 'price', 
    'quantity', 'spec_name', 'name'
]
PAGE_SIZE = 50  # Number of items to load per page
SKELETON_ROWS = 15 # Number of placeholder rows to show

# --- Editor Window (largely unchanged) ---
class ProductEditorWindow(ttk.Toplevel):
    def __init__(self, parent, product=None):
        super().__init__(parent)
        self.parent = parent
        self.product = product
        self.title("编辑商品" if self.product else "新增商品")
        self.geometry("520x580")
        self.minsize(500, 550)
        self.transient(parent)
        self.grab_set()
        
        # 居中显示
        self.center_window()

        # 主容器
        main_frame = ttk.Frame(self, padding=(30, 25, 30, 25))
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        title_text = "编辑商品信息" if self.product else "新增商品信息"
        title_label = ttk.Label(main_frame, text=title_text, 
                               font=("Microsoft YaHei UI", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 25), sticky=tk.W)
        
        # 表单字段
        self.entries = {}
        for i, db_col in enumerate(DB_COLUMNS):
            row = i + 1
            header = HEADER_MAP[db_col]
            
            # 标签
            label = ttk.Label(main_frame, text=f"{header}", 
                            font=("Microsoft YaHei UI", 11))
            label.grid(row=row, column=0, padx=(0, 20), pady=(0, 18), sticky=tk.W)
            
            # 输入框
            entry = ttk.Entry(main_frame, font=("Microsoft YaHei UI", 11), width=28)
            entry.grid(row=row, column=1, pady=(0, 18), sticky=tk.EW)
            self.entries[db_col] = entry

        main_frame.grid_columnconfigure(1, weight=1)

        # 填充现有数据
        if self.product:
            for db_col in DB_COLUMNS:
                self.entries[db_col].insert(0, self.product.get(db_col, ''))
            self.entries['spec_id'].config(state='readonly')

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=len(DB_COLUMNS)+2, column=0, columnspan=2, pady=(25, 0), sticky=tk.EW)
        
        ttk.Button(button_frame, text="取消", command=self.destroy, 
                  bootstyle="secondary", width=12).pack(side=RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="保存", command=self.save, 
                  bootstyle="success", width=12).pack(side=RIGHT)
    
    def center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def save(self):
        try:
            product_data = {db_col: self.entries[db_col].get().strip() for db_col in DB_COLUMNS}
            if not product_data['spec_id'] or not product_data['name']:
                messagebox.showerror("错误", "规格ID和货品名称不能为空。", parent=self)
                return

            product_data['price'] = float(product_data['price'] or 0)
            product_data['quantity'] = int(product_data['quantity'] or 0)

            def db_task():
                if self.product:
                    database.update_product(product_data)
                else:
                    if database.get_product_by_spec_id(product_data['spec_id']):
                        self.after(0, lambda: messagebox.showerror("错误", f"规格ID '{product_data['spec_id']}' 已存在。", parent=self))
                        return
                    database.add_product(product_data)
                self.after(0, lambda: self.parent.start_new_load(force=True))
                self.after(0, self.destroy)

            threading.Thread(target=db_task, daemon=True).start()

        except ValueError:
            messagebox.showerror("错误", "价格和平台库存必须是有效的数字。", parent=self)
        except Exception as e:
            messagebox.showerror("保存失败", f"发生错误: {e}", parent=self)

# --- Main Application ---
class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Matrix · 商品信息管理系统")
        self.geometry("1500x850")
        self.minsize(1200, 700)
        
        # 设置窗口图标和样式
        try:
            self.iconbitmap(default="")  # 可以添加图标文件
        except:
            pass
        
        # 设置窗口居中
        self.center_window()
        
        # 添加窗口阴影效果（Windows）
        try:
            self.wm_attributes("-alpha", 0.98)  # 轻微透明度
        except:
            pass

        # --- State Management for Lazy Loading ---
        self.is_busy = False
        self.is_loading_more = False
        self.current_offset = 0
        self.total_items = 0
        self.current_query = ""
        self.all_data_loaded = False
        self.last_clicked_row = None
        self.last_clicked_column_index = -1

        self._build_ui()
        self.start_new_load()

    def _build_ui(self):
        # --- 主容器 ---
        main_container = ttk.Frame(self, padding=(0, 0, 0, 0))
        main_container.pack(fill=BOTH, expand=True)
        
        # --- 顶部标题栏 ---
        header_frame = ttk.Frame(main_container, padding=(30, 25, 30, 20))
        header_frame.pack(fill=X)
        
        # 左侧标题区域
        title_container = ttk.Frame(header_frame)
        title_container.pack(side=LEFT, fill=X, expand=True)
        
        title_label = ttk.Label(title_container, text="Matrix", 
                               font=("Microsoft YaHei UI", 22, "bold"))
        title_label.pack(side=LEFT)
        
        subtitle_label = ttk.Label(title_container, text="商品信息管理系统", 
                                 font=("Microsoft YaHei UI", 13))
        subtitle_label.pack(side=LEFT, padx=(15, 0))
        
        # 右侧版本信息
        version_label = ttk.Label(header_frame, text="v1.0", 
                                font=("Microsoft YaHei UI", 9),
                                foreground="#888")
        version_label.pack(side=RIGHT)
        
        # 分隔线
        ttk.Separator(main_container, orient=HORIZONTAL).pack(fill=X, padx=30)
        
        # --- 操作栏 ---
        top_frame = ttk.Frame(main_container, padding=(30, 20, 30, 25))
        top_frame.pack(fill=X)
        
        # --- 左侧操作按钮组 ---
        left_buttons_frame = ttk.Frame(top_frame)
        left_buttons_frame.pack(side=LEFT)
        
        # 操作标签
        action_label = ttk.Label(left_buttons_frame, text="操作", 
                               font=("Microsoft YaHei UI", 11, "bold"))
        action_label.pack(side=LEFT, padx=(0, 15))
        
        self.action_buttons = []
        btn_configs = [
            {"text": "📥 导入数据", "cmd": self.import_data, "style": "info-outline", "width": 14},
            {"text": "➕ 新增", "cmd": self.open_add_window, "style": "success-outline", "width": 10},
            {"text": "✏️ 编辑", "cmd": self.open_edit_window, "style": "warning-outline", "width": 10},
            {"text": "🗑️ 删除", "cmd": self.delete_products, "style": "danger-outline", "width": 10}
        ]
        
        for i, config in enumerate(btn_configs):
            btn = ttk.Button(left_buttons_frame, text=config["text"], command=config["cmd"], 
                           bootstyle=config["style"], width=config["width"])
            btn.pack(side=LEFT, padx=(0, 8) if i < len(btn_configs)-1 else (0, 0))
            self.action_buttons.append(btn)
            
            # 添加按钮悬停效果
            self.add_button_hover_effect(btn)

        # --- 中间设置区域 ---
        middle_frame = ttk.Frame(top_frame)
        middle_frame.pack(side=LEFT, padx=(30, 30))
        
        # 分隔线
        ttk.Separator(middle_frame, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=(0, 20))
        
        settings_label = ttk.Label(middle_frame, text="设置", 
                                 font=("Microsoft YaHei UI", 11, "bold"))
        settings_label.pack(side=LEFT, padx=(0, 15))
        
        self.generate_report_var = tk.BooleanVar()
        self.report_checkbutton = ttk.Checkbutton(middle_frame, text="📊 生成调试报告", 
                                                variable=self.generate_report_var, 
                                                bootstyle="round-toggle")
        self.report_checkbutton.pack(side=LEFT)
        self.action_buttons.append(self.report_checkbutton)

        # --- 右侧搜索区域 ---
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=RIGHT, fill=X, expand=True)
        
        # 搜索容器
        search_container = ttk.Frame(search_frame)
        search_container.pack(side=RIGHT)
        
        search_label = ttk.Label(search_container, text="🔍 搜索", 
                               font=("Microsoft YaHei UI", 11, "bold"))
        search_label.pack(side=LEFT, padx=(0, 15))
        
        # 搜索输入框容器
        entry_container = ttk.Frame(search_container)
        entry_container.pack(side=LEFT, padx=(0, 8))
        
        self.search_entry = ttk.Entry(entry_container, font=("Microsoft YaHei UI", 11), 
                                    width=28, style="Search.TEntry")
        self.search_entry.pack(side=LEFT)
        self.search_entry.bind("<Return>", self.search_products)
        self.search_entry.bind("<FocusIn>", self.on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self.on_search_focus_out)
        self.action_buttons.append(self.search_entry)
        
        # 搜索按钮组
        button_container = ttk.Frame(search_container)
        button_container.pack(side=LEFT)
        
        self.search_button = ttk.Button(button_container, text="搜索", command=self.search_products, 
                                      bootstyle="primary", width=8)
        self.search_button.pack(side=LEFT, padx=(0, 4))
        
        self.clear_search_button = ttk.Button(button_container, text="清除", command=self.clear_search, 
                                            bootstyle="secondary-outline", width=6)
        self.clear_search_button.pack(side=LEFT)
        self.action_buttons.extend([self.search_button, self.clear_search_button])
        
        # 设置搜索框占位符
        self.setup_search_placeholder()



        # --- 数据表格区域 ---
        table_container = ttk.Frame(main_container, padding=(30, 5, 30, 20))
        table_container.pack(expand=True, fill=BOTH)
        
        # 表格标题栏
        table_header = ttk.Frame(table_container)
        table_header.pack(fill=X, pady=(0, 15))
        
        # 左侧标题
        title_frame = ttk.Frame(table_header)
        title_frame.pack(side=LEFT)
        
        table_title = ttk.Label(title_frame, text="📋 数据列表", 
                               font=("Microsoft YaHei UI", 13, "bold"))
        table_title.pack(side=LEFT)
        
        # 数据统计标签
        self.data_stats_label = ttk.Label(title_frame, text="", 
                                        font=("Microsoft YaHei UI", 10),
                                        foreground="#888")
        self.data_stats_label.pack(side=LEFT, padx=(15, 0))
        
        # 右侧工具
        tools_frame = ttk.Frame(table_header)
        tools_frame.pack(side=RIGHT)
        
        # 刷新按钮
        refresh_btn = ttk.Button(tools_frame, text="🔄 刷新", command=self.refresh_data,
                               bootstyle="secondary-outline", width=8)
        refresh_btn.pack(side=RIGHT, padx=(8, 0))
        self.action_buttons.append(refresh_btn)
        
        # 导出按钮
        export_btn = ttk.Button(tools_frame, text="📤 导出", command=self.export_data,
                              bootstyle="info-outline", width=8)
        export_btn.pack(side=RIGHT)
        self.action_buttons.append(export_btn)

        # 表格框架
        tree_frame = ttk.Frame(table_container)
        tree_frame.pack(expand=True, fill=BOTH)

        # 样式配置
        style = ttk.Style()
        
        # 表格样式
        style.configure('Custom.Treeview', 
                       rowheight=42,
                       font=("Microsoft YaHei UI", 11),
                       fieldbackground="#2b2b2b",
                       borderwidth=0,
                       relief="flat")
        
        # 表头样式
        style.configure('Custom.Treeview.Heading', 
                       font=("Microsoft YaHei UI", 11, "bold"),
                       padding=(15, 12),
                       relief="flat",
                       borderwidth=1)
        
        # 选中行样式
        style.map('Custom.Treeview',
                 background=[('selected', '#404040')],
                 foreground=[('selected', '#ffffff')])
        
        # 骨架加载样式
        style.configure("Skeleton.Treeview", 
                       foreground="#555",
                       font=("Microsoft YaHei UI", 11),
                       rowheight=42)
        
        # 搜索框样式
        style.configure("Search.TEntry",
                       fieldbackground="#3a3a3a",
                       borderwidth=1,
                       relief="solid",
                       padding=(8, 6))

        self.tree = ttk.Treeview(tree_frame, columns=DISPLAY_COLUMNS, show="headings", 
                               style="Custom.Treeview")
        
        # 配置列 - 所有数据居中显示，确保总宽度足够触发横向滚动
        column_configs = {
            'shop': {'width': 120, 'anchor': CENTER},          # 店铺名
            'product_id': {'width': 130, 'anchor': CENTER},    # 货品ID
            'spec_id': {'width': 130, 'anchor': CENTER},       # 规格ID
            'sku': {'width': 160, 'anchor': CENTER},           # SKU编码
            'price': {'width': 100, 'anchor': CENTER},         # 价格
            'quantity': {'width': 100, 'anchor': CENTER},      # 库存数量
            'spec_name': {'width': 220, 'anchor': CENTER},     # 规格名称
            'name': {'width': 400, 'anchor': CENTER}           # 商品名称
        }
        
        # 列图标映射
        column_icons = {
            'shop': '🏪',
            'product_id': '🆔',
            'spec_id': '🔖',
            'sku': '📦',
            'price': '💰',
            'quantity': '📊',
            'spec_name': '📝',
            'name': '🏷️'
        }
        
        for col in DISPLAY_COLUMNS:
            header_text = HEADER_MAP.get(col, col)
            icon = column_icons.get(col, '')
            full_header = f"{icon} {header_text}" if icon else header_text
            
            # 所有表头居中对齐
            self.tree.heading(col, text=full_header, anchor=CENTER)
            
            config = column_configs.get(col, {'width': 100, 'anchor': CENTER})
            # 设置最小宽度，确保内容可见
            min_width = max(60, config['width'] // 2)
            self.tree.column(col, **config, minwidth=min_width)
            
            # 添加列排序功能
            self.tree.heading(col, command=lambda c=col: self.sort_column(c))

        # 滚动条
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.tree.xview)
        
        # 保存滚动条引用
        self.v_scrollbar = v_scrollbar
        self.h_scrollbar = h_scrollbar
        
        # 配置滚动条
        self.tree.configure(yscrollcommand=self._on_y_scroll, xscrollcommand=h_scrollbar.set)
        
        # 布局 - 确保滚动条正确显示
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 配置网格权重
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # 确保滚动条样式
        style.configure("Vertical.TScrollbar", width=16)
        style.configure("Horizontal.TScrollbar", height=16)

        # 事件绑定
        self.tree.bind("<Control-c>", self.copy_to_clipboard)
        self.tree.bind("<Button-1>", self.on_cell_click)
        self.tree.bind("<Double-Button-1>", self.on_row_double_click)
        self.tree.bind("<Motion>", self.on_tree_motion)
        
        # 鼠标滚轮支持横向滚动
        self.tree.bind("<Shift-MouseWheel>", self._on_horizontal_scroll)

        # --- 状态栏 ---
        status_frame = ttk.Frame(main_container, padding=(30, 15, 30, 20))
        status_frame.pack(side=BOTTOM, fill=X)
        
        # 分隔线
        ttk.Separator(status_frame, orient=HORIZONTAL).pack(fill=X, pady=(0, 15))
        
        status_container = ttk.Frame(status_frame)
        status_container.pack(fill=X)
        
        # 左侧状态
        left_status = ttk.Frame(status_container)
        left_status.pack(side=LEFT, fill=X, expand=True)
        
        self.status_icon = ttk.Label(left_status, text="✅", font=("Microsoft YaHei UI", 11))
        self.status_icon.pack(side=LEFT, padx=(0, 8))
        
        self.status_label = ttk.Label(left_status, text="准备就绪", 
                                    font=("Microsoft YaHei UI", 10))
        self.status_label.pack(side=LEFT)
        
        # 中间进度条（隐藏状态）
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_container, variable=self.progress_var,
                                          mode='indeterminate', length=200)
        # 初始隐藏
        
        # 右侧状态信息
        right_status = ttk.Frame(status_container)
        right_status.pack(side=RIGHT)
        
        self.info_label = ttk.Label(right_status, text="", 
                                   font=("Microsoft YaHei UI", 10),
                                   foreground="#888")
        self.info_label.pack(side=RIGHT, padx=(0, 15))
        
        # 时间标签
        self.time_label = ttk.Label(right_status, text="", 
                                  font=("Microsoft YaHei UI", 9),
                                  foreground="#666")
        self.time_label.pack(side=RIGHT)
        
        # 启动时间更新
        self.update_time()

    def copy_to_clipboard(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        # Condition for single cell copy: one row selected, it's the last one clicked, and a valid cell was clicked.
        if (len(selected_items) == 1 and 
            selected_items[0] == self.last_clicked_row and 
            self.last_clicked_column_index >= 0):
            
            try:
                # Single cell copy logic
                cell_value = self.tree.item(self.last_clicked_row, 'values')[self.last_clicked_column_index]
                self.clipboard_clear()
                self.clipboard_append(str(cell_value))

                # Status bar feedback
                column_name = DISPLAY_COLUMNS[self.last_clicked_column_index]
                header_name = HEADER_MAP.get(column_name, column_name)
                original_text = self.status_label.cget("text")
                self.update_status(f'已复制单元格 ({header_name}): "{cell_value}"', "📋")
                self.after(3000, lambda: self.update_status("准备就绪", "✅"))
            except (IndexError, tk.TclError):
                pass # Fail silently on this specific copy type
            return # IMPORTANT: End execution after attempting single-cell copy

        # Fallback to multi-row copy logic
        try:
            headers = [self.tree.heading(col)['text'] for col in DISPLAY_COLUMNS]
            clipboard_data = "\t".join(headers) + "\n"
            
            for item in selected_items:
                values = self.tree.item(item, 'values')
                str_values = [str(v) for v in values]
                clipboard_data += "\t".join(str_values) + "\n"
            
            self.clipboard_clear()
            self.clipboard_append(clipboard_data)
            
            original_text = self.status_label.cget("text")
            self.update_status(f"已复制 {len(selected_items)} 行数据到剪贴板", "📋")
            self.after(2500, lambda: self.update_status("准备就绪", "✅"))
        except tk.TclError:
            messagebox.showwarning("复制失败", "无法访问系统剪贴板。", parent=self)

    def copy_cell_to_clipboard(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        
        if not row_id or not column_id: return

        column_index = int(column_id.replace('#', '')) - 1

        if column_index < 0:
            return

        try:
            cell_value = self.tree.item(row_id, 'values')[column_index]
            
            self.clipboard_clear()
            self.clipboard_append(str(cell_value))
            messagebox.showinfo("复制成功", "单元格内容已复制到剪贴板。", parent=self)
        except (IndexError, tk.TclError):
            messagebox.showwarning("复制失败", "无法复制此单元格。", parent=self)

    def on_cell_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            self.last_clicked_row = self.tree.identify_row(event.y)
            column_id = self.tree.identify_column(event.x)
            if column_id:
                self.last_clicked_column_index = int(column_id.replace('#', '')) - 1
            else:
                self.last_clicked_column_index = -1
        else:
            # Reset if user clicks outside a cell (e.g., on the header or empty space)
            self.last_clicked_row = None
            self.last_clicked_column_index = -1
    
    def center_window(self):
        """窗口居中显示"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def add_button_hover_effect(self, button):
        """添加按钮悬停效果"""
        def on_enter(e):
            button.configure(cursor="hand2")
        def on_leave(e):
            button.configure(cursor="")
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
    
    def setup_search_placeholder(self):
        """设置搜索框占位符"""
        self.placeholder_text = "按 SKU、名称、规格等搜索..."
        self.placeholder_color = '#888'
        try: 
            self.default_fg_color = self.search_entry.cget("foreground")
        except: 
            self.default_fg_color = 'white'
        self.on_search_focus_out(None)
    
    def on_search_focus_in(self, event):
        """搜索框获得焦点"""
        if self.search_entry.get() == self.placeholder_text:
            self.search_entry.delete(0, "end")
            self.search_entry.config(foreground=self.default_fg_color)
    
    def on_search_focus_out(self, event):
        """搜索框失去焦点"""
        if not self.search_entry.get():
            self.search_entry.insert(0, self.placeholder_text)
            self.search_entry.config(foreground=self.placeholder_color)
    
    def on_row_double_click(self, event):
        """双击行事件"""
        self.open_edit_window()
    
    def on_tree_motion(self, event):
        """鼠标移动事件 - 添加行悬停效果"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.configure(cursor="hand2")
        else:
            self.tree.configure(cursor="")
    
    def sort_column(self, col):
        """列排序功能"""
        # 这里可以实现排序逻辑
        pass
    
    def refresh_data(self):
        """刷新数据"""
        self.start_new_load(force=True)
    
    def export_data(self):
        """导出数据功能"""
        messagebox.showinfo("提示", "导出功能开发中...", parent=self)
    
    def update_time(self):
        """更新时间显示"""
        import datetime
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        self.after(1000, self.update_time)
    
    def show_progress(self, show=True):
        """显示/隐藏进度条"""
        if show:
            self.progress_bar.pack(side=LEFT, padx=(20, 20))
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
    
    def update_status(self, message, icon="✅", show_progress=False):
        """更新状态显示"""
        self.status_icon.config(text=icon)
        self.status_label.config(text=message)
        self.show_progress(show_progress)

    # --- UI State & Skeleton ---
    def set_busy(self, busy, is_loading_more=False):
        self.is_busy = busy
        self.is_loading_more = is_loading_more
        if not is_loading_more:
            for widget in self.action_buttons:
                try: widget.config(state=tk.DISABLED if busy else tk.NORMAL)
                except: pass
        self.tree.config(cursor="wait" if busy else "")
        self.update_idletasks()

    def show_skeleton_loader(self):
        self.tree.delete(*self.tree.get_children())
        self.tree.configure(style="Skeleton.Treeview")
        skeleton_item = ('▓▓▓', '▓▓▓▓▓▓▓▓', '▓▓▓▓▓▓', '▓▓▓▓▓▓▓▓▓▓▓', '▓▓.▓▓', '▓▓▓', '▓▓▓▓▓▓▓▓▓▓', '▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓')
        for i in range(SKELETON_ROWS):
            self.tree.insert("", tk.END, values=skeleton_item, tags=('skeleton',))
        
        self.update_status("正在加载数据...", "⏳", True)
        self.info_label.config(text="")
        self.data_stats_label.config(text="")

    # --- Core Lazy Loading Logic ---
    def start_new_load(self, query=None, force=False):
        if not force and self.is_busy and not self.is_loading_more: return
        self.current_query = self.search_entry.get() if query is None else query
        if self.current_query == self.placeholder_text: self.current_query = ""
        self.current_offset = 0
        self.total_items = 0
        self.all_data_loaded = False
        self.set_busy(True)
        self.show_skeleton_loader()
        self.load_next_page(is_new_query=True)

    def load_next_page(self, is_new_query=False):
        if self.is_busy and not is_new_query: return
        if self.all_data_loaded: return
        
        self.set_busy(True, is_loading_more=not is_new_query)
        if not is_new_query:
            self.update_status("正在加载更多数据...", "⏳", True)
            self.info_label.config(text=f"已显示 {self.current_offset} / {self.total_items}")
        else:
            if self.current_query:
                self.update_status(f'正在搜索 "{self.current_query}"...', "🔍", True)
            else:
                self.update_status("正在加载数据...", "⏳", True)
            self.info_label.config(text="")
            self.data_stats_label.config(text="")

        threading.Thread(target=self._threaded_fetch_page, args=(is_new_query,), daemon=True).start()

    def _threaded_fetch_page(self, is_new_query):
        try:
            if self.current_query:
                if is_new_query: self.total_items = database.search_products_count(self.current_query)
                products = database.search_products(self.current_query, limit=PAGE_SIZE, offset=self.current_offset)
            else:
                if is_new_query: self.total_items = database.get_all_products_count()
                products = database.get_all_products(limit=PAGE_SIZE, offset=self.current_offset)
            self.after(0, self._on_page_load_complete, products, is_new_query)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("数据库错误", f"加载数据时出错: {e}"))
            self.after(0, self.set_busy, False)

    def _on_page_load_complete(self, products, is_new_query):
        if is_new_query:
            self.tree.delete(*self.tree.get_children())
            self.tree.configure(style="Treeview") # Restore normal style
            # Clear selection when loading new data
            self.last_clicked_row = None
            self.last_clicked_column_index = -1

        for product_row in products:
            reordered_values = [product_row[col] for col in DISPLAY_COLUMNS]
            self.tree.insert("", tk.END, values=tuple(reordered_values))
        
        self.current_offset += len(products)
        if self.current_offset >= self.total_items:
            self.all_data_loaded = True

        if self.current_query:
            status_text = f"搜索 \"{self.current_query}\" 找到 {self.total_items} 条结果"
            info_text = f"已显示 {self.current_offset} / {self.total_items}"
            icon = "🔍"
        else:
            status_text = "数据加载完成"
            info_text = f"共 {self.total_items} 条记录，已显示 {self.current_offset} 条"
            icon = "✅"
        
        self.update_status(status_text, icon)
        self.info_label.config(text=info_text)
        self.data_stats_label.config(text=f"({self.current_offset}/{self.total_items})")
        self.set_busy(False)

    # --- Event Handlers ---
    def _on_y_scroll(self, *args):
        """处理垂直滚动条更新和懒加载"""
        # 更新垂直滚动条显示
        self.v_scrollbar.set(*args)
        
        # 检查是否需要懒加载更多数据
        if len(args) >= 2:
            first, last = args[0], args[1]
            if float(last) > 0.9 and not self.is_busy and not self.all_data_loaded:
                self.load_next_page()
    
    def _on_horizontal_scroll(self, event):
        """处理横向滚动（Shift+鼠标滚轮）"""
        self.tree.xview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_scroll(self, *args):
        """原始滚动处理方法（保持兼容性）"""
        first, last = args
        if float(last) > 0.9 and not self.is_busy and not self.all_data_loaded:
            self.load_next_page()

    def refresh_treeview(self): self.start_new_load(query="")
    def search_products(self, event=None): self.start_new_load()
    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.on_entry_focus_out(None)
        self.start_new_load(query="")



    # --- Import, Delete, Edit Methods (with state handling) ---
    def import_data(self):
        file_path = filedialog.askopenfilename(title="选择Excel文件", filetypes=(("Excel 文件", "*.xlsx"), ("所有文件", "*.*")))
        if not file_path: return
        self.set_busy(True)
        filename = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
        self.status_label.config(text=f"正在导入文件: {filename}")
        self.info_label.config(text="请稍候...")
        threading.Thread(target=self._threaded_import, args=(file_path,), daemon=True).start()

    def _threaded_import(self, file_path):
        try:
            sheet1_dtypes = { '规格ID': str, '规格编码': str }; sheet2_dtypes = { '无效的规格ID': str }; sheet3_dtypes = { '启用的规格编码': str }
            df = pd.read_excel(file_path, sheet_name='Sheet1', dtype=sheet1_dtypes)
            df_sheet2 = pd.read_excel(file_path, sheet_name='Sheet2', dtype=sheet2_dtypes)
            df_sheet3 = pd.read_excel(file_path, sheet_name='Sheet3', dtype=sheet3_dtypes)
            report_df = df.copy(); total_rows = len(report_df)
            invalid_ids = set(df_sheet2['无效的规格ID'].dropna().astype(str).str.strip().str.lower())
            enabled_codes = set(df_sheet3['启用的规格编码'].dropna().astype(str).str.strip())
            report_df['_clean_spec_id'] = report_df['规格ID'].astype(str).str.strip().str.lower()
            report_df['_clean_sku'] = report_df['规格编码'].astype(str).str.strip()
            reasons = [('无效的规格ID' if row['_clean_spec_id'] in invalid_ids else ('规格编码未启用' if row['_clean_sku'] != '*' and row['_clean_sku'] not in enabled_codes else '')) for _, row in report_df.iterrows()]
            report_df['_filter_reason'] = reasons; report_df['_is_imported'] = ['是' if not r else '否' for r in reasons]
            if self.generate_report_var.get():
                with pd.ExcelWriter('debug_report.xlsx') as writer: report_df.to_excel(writer, sheet_name='Filter_Debug_Report', index=False)
            df_filtered = report_df[report_df['_is_imported'] == '是']
            user_header_to_db_col = {v: k for k, v in HEADER_MAP.items()}
            df_renamed = df_filtered.rename(columns=user_header_to_db_col).fillna('')
            products_to_process = [tuple(row) for row in df_renamed[DB_COLUMNS].itertuples(index=False)]
            
            db_stats = {'added': 0, 'updated': 0}
            if products_to_process:
                db_stats = database.add_product_batch(products_to_process)

            result = {
                'success': True, 
                'total': total_rows, 
                'processed': len(products_to_process),
                'filtered': total_rows - len(products_to_process),
                'db_stats': db_stats
            }
            self.after(0, self._on_import_complete, result)
        except Exception as e:
            self.after(0, self._on_import_complete, {'success': False, 'error': e})

    def _on_import_complete(self, result):
        if result['success']:
            db_stats = result['db_stats']
            summary_message = f"""
导入完成！

--- Excel 文件分析 ---
总行数: {result['total']}
有效行 (用于处理): {result['processed']}
被过滤 (无效ID/未启用): {result['filtered']}

--- 数据库操作 ---
新增记录: {db_stats['added']}
更新现有记录: {db_stats['updated']}

(提示: 导入操作会基于“规格编码”更新已有记录)"""
            messagebox.showinfo("导入结果", summary_message)
        else:
            err_msg = {KeyError: "Excel文件中缺少必要的Sheet或列", FileNotFoundError: "找不到文件"}.get(type(result['error']), "处理Excel文件时发生未知错误")
            messagebox.showerror("错误", f"{err_msg}: {result['error']}")
        
        self.start_new_load(force=True)

    def delete_products(self):
        if self.is_busy: return
        selected_items = self.tree.selection()
        if not selected_items: return messagebox.showwarning("警告", "请先选择要删除的商品。")
        if messagebox.askyesno("确认删除", f"你确定要删除选中的 {len(selected_items)} 件商品吗？"):
            self.set_busy(True)
            self.status_label.config(text=f"正在删除 {len(selected_items)} 件商品")
            self.info_label.config(text="请稍候...")
            def db_task():
                spec_id_index = DISPLAY_COLUMNS.index('spec_id')
                for item in selected_items: database.delete_product_by_spec_id(self.tree.item(item, 'values')[spec_id_index])
                def on_delete_done():
                    messagebox.showinfo("成功", f"成功删除了 {len(selected_items)} 件商品。")
                    self.start_new_load(force=True)
                self.after(0, on_delete_done)
            threading.Thread(target=db_task, daemon=True).start()

    def open_add_window(self):
        if self.is_busy and not self.is_loading_more: return
        ProductEditorWindow(self)

    def open_edit_window(self):
        if self.is_busy and not self.is_loading_more: return
        selected_items = self.tree.selection()
        if not selected_items: return messagebox.showwarning("警告", "请选择一个要编辑的商品。")
        if len(selected_items) > 1: return messagebox.showwarning("警告", "一次只能编辑一个商品。")
        product_data = dict(zip(DISPLAY_COLUMNS, self.tree.item(selected_items[0], 'values')))
        ProductEditorWindow(self, product=product_data)

if __name__ == "__main__":
    database.init_db()
    app = App()
    app.mainloop()
