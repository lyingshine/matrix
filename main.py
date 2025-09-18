import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
import database
from database import DB_COLUMNS
import threading
import json

# --- Constants ---
HEADER_MAP = {
    'sku': '规格编码',
    'product_id': '货品ID',
    'spec_id': '规格ID',
    'name': '货品名称',
    'spec_name': '规格名称',
    'price': '价格',
    'final_price': '到手价',
    'quantity': '平台库存',
    'shop': '店铺',
    'category': '分类',
    'warehouse': '仓库',
    'short_name': '简称',
    'min_price': '最低价',
    'purchase_price': '采购价'
}
DISPLAY_COLUMNS = [
    'shop', 'product_id', 'spec_id', 'sku', 'price', 
    'final_price', 'quantity', 'spec_name', 'name',
    'category', 'warehouse', 'short_name', 'min_price', 'purchase_price'
]

# 优惠券相关常量
COUPON_HEADER_MAP = {
    'id': 'ID',
    'shop': '店铺',
    'coupon_type': '类型',
    'amount': '面额/折扣',
    'min_price': '最低消费',
    'start_date': '开始日期',
    'end_date': '结束日期',
    'description': '描述',
    'is_active': '状态',
    'product_ids': '适用货品'
}

# 优惠券类型映射
COUPON_TYPE_MAP = {
    'instant': '立减券',
    'threshold': '满减券', 
    'discount': '折扣券'
}
PAGE_SIZE = 100  # Number of items to load per page - 增加页面大小减少加载次数
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
        self.geometry("1600x900")
        self.minsize(1300, 750)
        
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
        
        # 当前选中的页面
        self.current_page = "overview"
        
        # 生成调试报告变量
        self.generate_report_var = tk.BooleanVar()
        
        # 初始化action_buttons列表
        self.action_buttons = []

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

    def _build_ui(self):
        # --- 主容器 ---
        main_container = ttk.Frame(self, padding=(0, 0, 0, 0))
        main_container.pack(fill=BOTH, expand=True)
        
        # --- 顶部标题栏 ---
        header_frame = ttk.Frame(main_container, padding=(30, 25, 30, 20))
        header_frame.pack(fill=X)
        
        # 创建渐变效果的标题区域
        title_container = ttk.Frame(header_frame)
        title_container.pack(side=LEFT, fill=X, expand=True)
        
        # 主标题
        title_label = ttk.Label(title_container, text="Matrix", 
                               font=("Microsoft YaHei UI", 26, "bold"))
        title_label.pack(side=LEFT)
        
        # 副标题
        subtitle_label = ttk.Label(title_container, text="商品信息管理系统", 
                                 font=("Microsoft YaHei UI", 14),
                                 foreground="#B0B0B0")
        subtitle_label.pack(side=LEFT, padx=(20, 0), pady=(5, 0))
        
        # 右侧信息区域
        info_container = ttk.Frame(header_frame)
        info_container.pack(side=RIGHT)
        
        # 版本标签
        version_label = ttk.Label(info_container, text="v2.0", 
                                font=("Microsoft YaHei UI", 10),
                                foreground="#888")
        version_label.pack(anchor=tk.E)
        
        # 当前用户（示例）
        user_label = ttk.Label(info_container, text="管理员", 
                             font=("Microsoft YaHei UI", 9),
                             foreground="#666")
        user_label.pack(anchor=tk.E, pady=(2, 0))
        
        # 优雅的分隔线
        separator_frame = ttk.Frame(main_container, height=2)
        separator_frame.pack(fill=X, padx=30, pady=(10, 0))
        ttk.Separator(separator_frame, orient=HORIZONTAL).pack(fill=X)
        
        # --- 主内容区域 ---
        content_frame = ttk.Frame(main_container, padding=(30, 20, 30, 20))
        content_frame.pack(fill=BOTH, expand=True)
        
        # --- 左侧导航栏 ---
        sidebar_container = ttk.Frame(content_frame)
        sidebar_container.pack(side=LEFT, fill=Y, padx=(0, 25))
        
        self.sidebar = ttk.Frame(sidebar_container, width=220)
        self.sidebar.pack(fill=BOTH, expand=True)
        self.sidebar.pack_propagate(False)  # 固定宽度
        
        self._build_sidebar()
        
        # --- 右侧内容区域 ---
        content_container = ttk.Frame(content_frame)
        content_container.pack(side=RIGHT, fill=BOTH, expand=True)
        
        self.content_area = ttk.Frame(content_container, padding=(25, 20, 25, 20))
        self.content_area.pack(fill=BOTH, expand=True)
        
        # 创建各个页面
        self._create_pages()
        
        # 显示默认页面
        self.show_page("overview")
        
        # --- 状态栏 ---
        self._build_status_bar(main_container)
        
        # 启动时间更新
        self.update_time()
        
        # 滚动优化设置
        self._scroll_timer = None
        self._last_scroll_time = 0
        self._smooth_scroll_active = False
        
        # 配置自定义样式
        self._configure_custom_styles()
    
    def _configure_custom_styles(self):
        """配置自定义样式"""
        style = ttk.Style()
        
        # 表格样式增强
        style.configure('Enhanced.Treeview', 
                       rowheight=45,
                       font=("Microsoft YaHei UI", 11),
                       borderwidth=0,
                       relief="flat")
        
        style.configure('Enhanced.Treeview.Heading', 
                       font=("Microsoft YaHei UI", 11, "bold"),
                       padding=(15, 12),
                       relief="flat",
                       borderwidth=1)
        
        # 选中行样式
        style.map('Enhanced.Treeview',
                 background=[('selected', '#4A90E2')],
                 foreground=[('selected', '#FFFFFF')])
        
        # 搜索框样式
        style.configure("Search.TEntry",
                       fieldbackground="#3A3A3A",
                       borderwidth=1,
                       relief="solid",
                       padding=(10, 8))
    
    def _build_status_bar(self, parent):
        """构建状态栏"""
        status_frame = ttk.Frame(parent, padding=(25, 10, 25, 15))
        status_frame.pack(side=BOTTOM, fill=X)
        
        # 分隔线
        ttk.Separator(status_frame, orient=HORIZONTAL).pack(fill=X, pady=(0, 10))
        
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
    
    def _build_sidebar(self):
        """构建左侧导航栏"""
        # 导航标题区域
        nav_header = ttk.Frame(self.sidebar, padding=(20, 15, 20, 10))
        nav_header.pack(fill=X)
        
        nav_title = ttk.Label(nav_header, text="导航", 
                             font=("Microsoft YaHei UI", 14, "bold"))
        nav_title.pack(anchor=tk.W)
        
        nav_subtitle = ttk.Label(nav_header, text="Navigation", 
                               font=("Microsoft YaHei UI", 9),
                               foreground="#888")
        nav_subtitle.pack(anchor=tk.W, pady=(2, 0))
        
        # 导航按钮区域
        nav_content = ttk.Frame(self.sidebar, padding=(15, 10, 15, 15))
        nav_content.pack(fill=X)
        
        # 导航按钮配置
        nav_buttons = [
            {"text": "📊  总览", "page": "overview", "desc": "数据概览与统计"},
            {"text": "📦  SKU列表", "page": "sku_list", "desc": "商品管理与编辑"},
            {"text": "🎫  优惠券", "page": "coupons", "desc": "优惠券配置管理"}
        ]
        
        self.nav_buttons = {}
        
        for i, btn_config in enumerate(nav_buttons):
            # 按钮容器
            btn_container = ttk.Frame(nav_content)
            btn_container.pack(fill=X, pady=(0, 12))
            
            # 主按钮 - 更现代的样式
            btn = ttk.Button(btn_container, 
                           text=btn_config["text"],
                           command=lambda p=btn_config["page"]: self.show_page(p),
                           bootstyle="outline-secondary",
                           width=28)
            btn.pack(fill=X)
            
            # 描述文字
            desc_label = ttk.Label(btn_container, 
                                 text=btn_config["desc"],
                                 font=("Microsoft YaHei UI", 8),
                                 foreground="#999")
            desc_label.pack(pady=(4, 0), padx=(5, 0), anchor=tk.W)
            
            self.nav_buttons[btn_config["page"]] = btn
            
            # 添加悬停效果
            self.add_nav_hover_effect(btn)
        
        # 优雅的分隔区域
        separator_area = ttk.Frame(self.sidebar, padding=(20, 15, 20, 15))
        separator_area.pack(fill=X)
        ttk.Separator(separator_area, orient=HORIZONTAL).pack(fill=X)
        
        # 快捷操作区域
        quick_area = ttk.Frame(self.sidebar, padding=(15, 10, 15, 20))
        quick_area.pack(fill=X)
        
        quick_title = ttk.Label(quick_area, text="快捷操作", 
                               font=("Microsoft YaHei UI", 12, "bold"))
        quick_title.pack(anchor=tk.W, pady=(0, 10))
        
        quick_buttons = [
            {"text": "📥  导入数据", "cmd": self.import_data, "style": "info-outline"},
            {"text": "📤  导出数据", "cmd": self.export_data, "style": "secondary-outline"},
            {"text": "🔄  刷新数据", "cmd": self.refresh_data, "style": "primary-outline"}
        ]
        
        for btn_config in quick_buttons:
            btn = ttk.Button(quick_area,
                           text=btn_config["text"],
                           command=btn_config["cmd"],
                           bootstyle=btn_config["style"],
                           width=28)
            btn.pack(fill=X, pady=(0, 8))
            self.add_button_hover_effect(btn)
    
    def add_nav_hover_effect(self, button):
        """添加导航按钮悬停效果"""
        def on_enter(e):
            button.configure(cursor="hand2")
        def on_leave(e):
            button.configure(cursor="")
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
    
    def _create_pages(self):
        """创建各个页面"""
        self.pages = {}
        
        # 总览页面
        self.pages["overview"] = self._create_overview_page()
        
        # SKU列表页面
        self.pages["sku_list"] = self._create_sku_list_page()
        
        # 优惠券页面
        self.pages["coupons"] = self._create_coupons_page()
    
    def show_page(self, page_name):
        """显示指定页面"""
        # 隐藏所有页面
        for page in self.pages.values():
            page.pack_forget()
        
        # 显示指定页面
        if page_name in self.pages:
            self.pages[page_name].pack(fill=BOTH, expand=True)
            self.current_page = page_name
            
            # 更新导航按钮样式
            for btn_page, btn in self.nav_buttons.items():
                if btn_page == page_name:
                    btn.configure(bootstyle="primary")
                else:
                    btn.configure(bootstyle="outline-secondary")
            
            # 页面特定的初始化
            if page_name == "overview":
                self._refresh_overview()
            elif page_name == "sku_list":
                # 确保tree已经创建后再加载数据
                if hasattr(self, 'tree') and self.tree:
                    self.start_new_load(force=True)
            elif page_name == "coupons":
                self._refresh_coupons()

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
        self.placeholder_text = "按 SKU、货品ID、名称、规格、分类、仓库、简称等搜索..."
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
    
    def _create_product_table(self, parent):
        """创建商品表格"""
        # 表格框架
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True)

        # 样式配置
        style = ttk.Style()
        
        # 表格样式 - 优化滚动性能
        style.configure('Custom.Treeview', 
                       rowheight=42,
                       font=("Microsoft YaHei UI", 11),
                       fieldbackground="#2b2b2b",
                       borderwidth=0,
                       relief="flat",
                       selectmode="extended")
        
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
        
        # 滚动条样式
        style.configure("Vertical.TScrollbar", width=16)
        style.configure("Horizontal.TScrollbar", height=16)

        self.tree = ttk.Treeview(tree_frame, columns=DISPLAY_COLUMNS, show="headings", 
                               style="Enhanced.Treeview", height=18)
        
        # 配置列
        column_configs = {
            'shop': {'width': 120, 'anchor': CENTER},
            'product_id': {'width': 130, 'anchor': CENTER},
            'spec_id': {'width': 130, 'anchor': CENTER},
            'sku': {'width': 160, 'anchor': CENTER},
            'price': {'width': 100, 'anchor': CENTER},
            'final_price': {'width': 100, 'anchor': CENTER},
            'quantity': {'width': 100, 'anchor': CENTER},
            'spec_name': {'width': 220, 'anchor': CENTER},
            'name': {'width': 400, 'anchor': CENTER},
            'category': {'width': 120, 'anchor': CENTER},
            'warehouse': {'width': 120, 'anchor': CENTER},
            'short_name': {'width': 150, 'anchor': CENTER},
            'min_price': {'width': 100, 'anchor': CENTER},
            'purchase_price': {'width': 100, 'anchor': CENTER}
        }
        
        # 列图标映射
        column_icons = {
            'shop': '🏪',
            'product_id': '🆔',
            'spec_id': '🔖',
            'sku': '📦',
            'price': '💰',
            'final_price': '🎯',
            'quantity': '📊',
            'spec_name': '📝',
            'name': '🏷️',
            'category': '📂',
            'warehouse': '🏭',
            'short_name': '🏷️',
            'min_price': '💸',
            'purchase_price': '💵'
        }
        
        for col in DISPLAY_COLUMNS:
            header_text = HEADER_MAP.get(col, col)
            icon = column_icons.get(col, '')
            full_header = f"{icon} {header_text}" if icon else header_text
            
            self.tree.heading(col, text=full_header, anchor=CENTER)
            config = column_configs.get(col, {'width': 100, 'anchor': CENTER})
            min_width = max(60, config['width'] // 2)
            self.tree.column(col, **config, minwidth=min_width)
            
            self.tree.heading(col, command=lambda c=col: self.sort_column(c))

        # 滚动条
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.tree.xview)
        
        self.v_scrollbar = v_scrollbar
        self.h_scrollbar = h_scrollbar
        
        self.tree.configure(yscrollcommand=self._on_y_scroll, xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 事件绑定
        self.tree.bind("<Control-c>", self.copy_to_clipboard)
        self.tree.bind("<Button-1>", self.on_cell_click)
        self.tree.bind("<Double-Button-1>", self.on_row_double_click)
        self.tree.bind("<Motion>", self.on_tree_motion)
        self.tree.bind("<MouseWheel>", self._on_mouse_wheel)
        self.tree.bind("<Shift-MouseWheel>", self._on_horizontal_scroll)
        self.tree.bind("<Up>", self._on_key_scroll)
        self.tree.bind("<Down>", self._on_key_scroll)
        self.tree.bind("<Page_Up>", self._on_key_scroll)
        self.tree.bind("<Page_Down>", self._on_key_scroll)
        self.tree.bind("<Home>", self._on_key_scroll)
        self.tree.bind("<End>", self._on_key_scroll)
    
    def _create_coupon_table(self, parent):
        """创建优惠券表格"""
        # 表格框架
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True)
        
        columns = ['id', 'shop', 'coupon_type', 'amount', 'min_price', 
                  'start_date', 'end_date', 'description', 'product_ids', 'is_active']
        
        self.coupon_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", 
                                       style="Enhanced.Treeview", height=15)
        
        # 配置列
        column_configs = {
            'id': {'width': 50, 'anchor': CENTER},
            'shop': {'width': 100, 'anchor': CENTER},
            'coupon_type': {'width': 80, 'anchor': CENTER},
            'amount': {'width': 90, 'anchor': CENTER},
            'min_price': {'width': 80, 'anchor': CENTER},
            'start_date': {'width': 100, 'anchor': CENTER},
            'end_date': {'width': 100, 'anchor': CENTER},
            'description': {'width': 150, 'anchor': tk.W},
            'product_ids': {'width': 120, 'anchor': CENTER},
            'is_active': {'width': 60, 'anchor': CENTER}
        }
        
        for col in columns:
            header_text = COUPON_HEADER_MAP.get(col, col)
            self.coupon_tree.heading(col, text=header_text, anchor=CENTER)
            config = column_configs.get(col, {'width': 100, 'anchor': CENTER})
            self.coupon_tree.column(col, **config, minwidth=50)
        
        # 滚动条
        v_scrollbar2 = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.coupon_tree.yview)
        h_scrollbar2 = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.coupon_tree.xview)
        
        self.coupon_tree.configure(yscrollcommand=v_scrollbar2.set, xscrollcommand=h_scrollbar2.set)
        
        # 布局
        self.coupon_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar2.grid(row=0, column=1, sticky="ns")
        h_scrollbar2.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # 双击编辑
        self.coupon_tree.bind("<Double-Button-1>", lambda e: self._edit_coupon())
    
    def _refresh_overview(self):
        """刷新总览页面数据"""
        try:
            # 获取统计数据
            total_products = database.get_all_products_count()
            
            # 获取店铺数量
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(DISTINCT shop) FROM products WHERE shop IS NOT NULL AND shop != ""')
            total_shops = cursor.fetchone()[0]
            
            # 获取优惠券数量
            cursor.execute('SELECT COUNT(*) FROM coupons WHERE is_active = 1')
            total_coupons = cursor.fetchone()[0]
            
            # 获取平均价格
            cursor.execute('SELECT AVG(price) FROM products WHERE price > 0')
            avg_price_result = cursor.fetchone()[0]
            avg_price = round(avg_price_result, 2) if avg_price_result else 0
            
            conn.close()
            
            # 更新统计卡片
            self.stats_cards["total_products"].value_label.config(text=str(total_products))
            self.stats_cards["total_shops"].value_label.config(text=str(total_shops))
            self.stats_cards["total_coupons"].value_label.config(text=str(total_coupons))
            self.stats_cards["avg_price"].value_label.config(text=f"¥{avg_price}")
            
        except Exception as e:
            print(f"刷新总览数据时出错: {e}")
    
    def _refresh_coupons(self):
        """刷新优惠券页面数据"""
        # 清空现有数据
        for item in self.coupon_tree.get_children():
            self.coupon_tree.delete(item)
        
        # 更新统计数据
        self._update_coupon_stats()
        
        # 加载数据
        coupons = database.get_all_coupons()
        for coupon in coupons:
            coupon_dict = dict(zip(database.COUPON_COLUMNS, coupon))
            
            # 格式化显示数据
            display_data = []
            for col in ['id', 'shop', 'coupon_type', 'amount', 'min_price', 
                       'start_date', 'end_date', 'description', 'product_ids', 'is_active']:
                value = coupon_dict[col]
                
                if col == 'coupon_type':
                    value = COUPON_TYPE_MAP.get(value, value)
                elif col == 'amount':
                    coupon_type = coupon_dict['coupon_type']
                    if coupon_type == 'discount':
                        value = f"{int(value * 100)}%"  # 折扣显示为百分比
                    else:
                        value = f"¥{value}"  # 立减券和满减券显示金额
                elif col == 'product_ids':
                    if value:
                        try:
                            product_ids = json.loads(value)
                            value = f"指定货品({len(product_ids)}个)"
                        except:
                            value = "指定货品"
                    else:
                        value = "全店通用"
                elif col == 'is_active':
                    value = '启用' if value else '禁用'
                
                display_data.append(str(value))
            
            self.coupon_tree.insert("", tk.END, values=display_data)
    
    def _update_coupon_stats(self):
        """更新优惠券统计数据"""
        try:
            stats = database.get_coupon_stats()
            
            # 更新统计卡片
            if hasattr(self, 'coupon_stats_cards'):
                self.coupon_stats_cards['total'].value_label.config(text=str(stats['total']))
                self.coupon_stats_cards['active'].value_label.config(text=str(stats['active']))
                self.coupon_stats_cards['expired'].value_label.config(text=str(stats['expired']))
        except Exception as e:
            print(f"更新优惠券统计数据时出错: {e}")
    
    def _add_coupon(self):
        """添加优惠券"""
        CouponEditorWindow(self)
    
    def _edit_coupon(self):
        """编辑优惠券"""
        selected = self.coupon_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要编辑的优惠券", parent=self)
            return
        
        item = selected[0]
        values = self.coupon_tree.item(item, 'values')
        coupon_id = values[0]
        
        coupon = database.get_coupon_by_id(coupon_id)
        if coupon:
            coupon_dict = dict(zip(database.COUPON_COLUMNS, coupon))
            CouponEditorWindow(self, coupon_dict)
    
    def _delete_coupon(self):
        """删除优惠券"""
        selected = self.coupon_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要删除的优惠券", parent=self)
            return
        
        if messagebox.askyesno("确认删除", "确定要删除选中的优惠券吗？", parent=self):
            for item in selected:
                values = self.coupon_tree.item(item, 'values')
                coupon_id = values[0]
                database.delete_coupon(coupon_id)
            
            self._refresh_coupons()
            # 刷新SKU列表的到手价
            if hasattr(self, 'tree'):
                self.start_new_load(force=True)
            messagebox.showinfo("成功", "优惠券删除成功", parent=self)
    
    def export_data(self):
        """导出数据功能"""
        try:
            # 选择保存文件路径
            file_path = filedialog.asksaveasfilename(
                title="导出数据",
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
            
            # 获取所有数据
            all_products = database.get_all_products(limit=999999)  # 获取所有数据
            
            if not all_products:
                messagebox.showwarning("警告", "没有数据可导出")
                return
            
            # 转换为DataFrame
            df = pd.DataFrame(all_products, columns=database.DB_COLUMNS)
            
            # 重命名列为中文
            df_renamed = df.rename(columns=HEADER_MAP)
            
            # 导出到Excel
            df_renamed.to_excel(file_path, index=False, sheet_name='商品数据')
            
            messagebox.showinfo("成功", f"数据已导出到: {file_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def _create_overview_page(self):
        """创建总览页面"""
        page = ttk.Frame(self.content_area)
        
        # 页面标题区域
        header_area = ttk.Frame(page, padding=(0, 0, 0, 25))
        header_area.pack(fill=X)
        
        title_container = ttk.Frame(header_area)
        title_container.pack(fill=X)
        
        # 主标题
        main_title = ttk.Label(title_container, text="数据总览", 
                             font=("Microsoft YaHei UI", 20, "bold"))
        main_title.pack(side=LEFT)
        
        # 副标题
        sub_title = ttk.Label(title_container, text="Dashboard Overview", 
                            font=("Microsoft YaHei UI", 11),
                            foreground="#888")
        sub_title.pack(side=LEFT, padx=(15, 0), pady=(5, 0))
        
        # 刷新按钮
        refresh_btn = ttk.Button(title_container, text="🔄 刷新", 
                               command=self._refresh_overview,
                               bootstyle="outline-primary", width=10)
        refresh_btn.pack(side=RIGHT)
        
        # 统计卡片区域
        stats_container = ttk.Frame(page, padding=(0, 0, 0, 30))
        stats_container.pack(fill=X)
        
        # 创建统计卡片
        self.stats_cards = {}
        
        card_configs = [
            {"title": "商品总数", "key": "total_products", "icon": "📦", "color": "#4A90E2", "desc": "Total Products"},
            {"title": "店铺数量", "key": "total_shops", "icon": "🏪", "color": "#7ED321", "desc": "Active Shops"},
            {"title": "优惠券数", "key": "total_coupons", "icon": "🎫", "color": "#F5A623", "desc": "Active Coupons"},
            {"title": "平均价格", "key": "avg_price", "icon": "💰", "color": "#BD10E0", "desc": "Average Price"}
        ]
        
        for i, config in enumerate(card_configs):
            card = self._create_modern_stat_card(stats_container, config)
            card.grid(row=0, column=i, padx=(0, 20) if i < 3 else (0, 0), sticky="ew")
            self.stats_cards[config["key"]] = card
        
        # 配置网格权重
        for i in range(4):
            stats_container.grid_columnconfigure(i, weight=1)
        
        # 内容区域
        content_area = ttk.Frame(page)
        content_area.pack(fill=BOTH, expand=True)
        
        # 左侧图表区域
        chart_container = ttk.Frame(content_area)
        chart_container.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 15))
        
        chart_frame = ttk.LabelFrame(chart_container, text="📈 数据趋势分析", 
                                   padding=(25, 20))
        chart_frame.pack(fill=BOTH, expand=True)
        
        # 图表占位内容
        chart_content = ttk.Frame(chart_frame)
        chart_content.pack(fill=BOTH, expand=True)
        
        chart_title = ttk.Label(chart_content, text="数据可视化", 
                              font=("Microsoft YaHei UI", 14, "bold"))
        chart_title.pack(pady=(20, 10))
        
        chart_desc = ttk.Label(chart_content, 
                             text="📊 商品价格分布图\n📈 店铺销量对比\n🎯 优惠券使用统计\n📉 库存变化趋势",
                             font=("Microsoft YaHei UI", 11),
                             foreground="#666",
                             justify=LEFT)
        chart_desc.pack(pady=(10, 20))
        
        # 右侧快速信息
        info_container = ttk.Frame(content_area)
        info_container.pack(side=RIGHT, fill=Y)
        
        # 快速操作卡片
        quick_frame = ttk.LabelFrame(info_container, text="⚡ 快速操作", 
                                   padding=(20, 15), width=280)
        quick_frame.pack(fill=X, pady=(0, 15))
        quick_frame.pack_propagate(False)
        
        quick_actions = [
            {"text": "📥 导入商品数据", "cmd": self.import_data, "style": "info"},
            {"text": "🎫 管理优惠券", "cmd": lambda: self.show_page("coupons"), "style": "warning"},
            {"text": "📦 查看商品列表", "cmd": lambda: self.show_page("sku_list"), "style": "primary"}
        ]
        
        for action in quick_actions:
            btn = ttk.Button(quick_frame, text=action["text"], 
                           command=action["cmd"], bootstyle=action["style"],
                           width=30)
            btn.pack(fill=X, pady=(0, 8))
        
        # 系统信息卡片
        system_frame = ttk.LabelFrame(info_container, text="ℹ️ 系统信息", 
                                    padding=(20, 15), width=280)
        system_frame.pack(fill=X)
        system_frame.pack_propagate(False)
        
        # 系统状态信息
        status_items = [
            ("数据库状态", "✅ 正常"),
            ("最后更新", "刚刚"),
            ("系统版本", "v2.0"),
            ("运行时间", "正在计算...")
        ]
        
        for label, value in status_items:
            item_frame = ttk.Frame(system_frame)
            item_frame.pack(fill=X, pady=(0, 5))
            
            ttk.Label(item_frame, text=label, 
                     font=("Microsoft YaHei UI", 9),
                     foreground="#666").pack(side=LEFT)
            ttk.Label(item_frame, text=value, 
                     font=("Microsoft YaHei UI", 9, "bold")).pack(side=RIGHT)
        
        return page
    
    def _create_modern_stat_card(self, parent, config):
        """创建现代化统计卡片"""
        # 卡片容器
        card_container = ttk.Frame(parent)
        
        # 卡片主体
        card = ttk.Frame(card_container, padding=(20, 18))
        card.pack(fill=BOTH, expand=True)
        
        # 顶部区域 - 图标和数值
        top_area = ttk.Frame(card)
        top_area.pack(fill=X, pady=(0, 12))
        
        # 图标
        icon_label = ttk.Label(top_area, text=config["icon"], 
                              font=("Microsoft YaHei UI", 24))
        icon_label.pack(side=LEFT)
        
        # 数值
        value_label = ttk.Label(top_area, text="0", 
                               font=("Microsoft YaHei UI", 28, "bold"),
                               foreground=config["color"])
        value_label.pack(side=RIGHT)
        
        # 中间区域 - 标题
        title_label = ttk.Label(card, text=config["title"],
                               font=("Microsoft YaHei UI", 12, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 4))
        
        # 底部区域 - 描述
        desc_label = ttk.Label(card, text=config["desc"],
                              font=("Microsoft YaHei UI", 9),
                              foreground="#888")
        desc_label.pack(anchor=tk.W)
        
        # 添加悬停效果
        self.add_card_hover_effect(card)
        
        # 保存引用以便更新
        card_container.value_label = value_label
        
        return card_container
    
    def add_card_hover_effect(self, card):
        """添加卡片悬停效果"""
        def on_enter(e):
            card.configure(cursor="hand2")
        def on_leave(e):
            card.configure(cursor="")
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
    
    def _create_sku_list_page(self):
        """创建SKU列表页面"""
        page = ttk.Frame(self.content_area)
        
        # 页面标题区域
        header_area = ttk.Frame(page, padding=(0, 0, 0, 25))
        header_area.pack(fill=X)
        
        # 标题容器
        title_container = ttk.Frame(header_area)
        title_container.pack(fill=X)
        
        # 主标题
        main_title = ttk.Label(title_container, text="商品管理", 
                             font=("Microsoft YaHei UI", 20, "bold"))
        main_title.pack(side=LEFT)
        
        # 副标题
        sub_title = ttk.Label(title_container, text="Product Management", 
                            font=("Microsoft YaHei UI", 11),
                            foreground="#888")
        sub_title.pack(side=LEFT, padx=(15, 0), pady=(5, 0))
        
        # 操作按钮组
        action_container = ttk.Frame(title_container)
        action_container.pack(side=RIGHT)
        
        action_buttons = [
            {"text": "➕ 新增", "cmd": self.open_add_window, "style": "success", "width": 10},
            {"text": "✏️ 编辑", "cmd": self.open_edit_window, "style": "warning", "width": 10},
            {"text": "🗑️ 删除", "cmd": self.delete_products, "style": "danger", "width": 10}
        ]
        
        for i, btn_config in enumerate(action_buttons):
            btn = ttk.Button(action_container, 
                           text=btn_config["text"], 
                           command=btn_config["cmd"],
                           bootstyle=btn_config["style"], 
                           width=btn_config["width"])
            btn.pack(side=LEFT, padx=(8, 0) if i > 0 else (0, 0))
            self.add_button_hover_effect(btn)
        
        # 搜索和筛选区域
        search_area = ttk.Frame(page, padding=(0, 0, 0, 20))
        search_area.pack(fill=X)
        
        # 搜索容器
        search_container = ttk.Frame(search_area, padding=(20, 15))
        search_container.pack(fill=X)
        
        # 搜索标题
        search_title = ttk.Label(search_container, text="🔍 搜索与筛选", 
                               font=("Microsoft YaHei UI", 12, "bold"))
        search_title.pack(anchor=tk.W, pady=(0, 10))
        
        # 搜索输入区域
        search_input_frame = ttk.Frame(search_container)
        search_input_frame.pack(fill=X)
        
        # 搜索框
        self.search_entry = ttk.Entry(search_input_frame, 
                                    font=("Microsoft YaHei UI", 11), 
                                    width=40,
                                    style="Search.TEntry")
        self.search_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        self.search_entry.bind("<Return>", self.search_products)
        self.search_entry.bind("<FocusIn>", self.on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self.on_search_focus_out)
        
        # 搜索按钮
        search_btn = ttk.Button(search_input_frame, text="搜索", 
                              command=self.search_products, 
                              bootstyle="primary", width=10)
        search_btn.pack(side=LEFT, padx=(0, 6))
        
        # 清除按钮
        clear_btn = ttk.Button(search_input_frame, text="清除", 
                             command=self.clear_search, 
                             bootstyle="secondary-outline", width=8)
        clear_btn.pack(side=LEFT)
        
        # 设置搜索框占位符
        self.setup_search_placeholder()
        
        # 数据表格区域
        table_area = ttk.Frame(page)
        table_area.pack(fill=BOTH, expand=True)
        
        # 表格标题栏
        table_header = ttk.Frame(table_area, padding=(0, 0, 0, 15))
        table_header.pack(fill=X)
        
        # 表格标题
        table_title_frame = ttk.Frame(table_header)
        table_title_frame.pack(side=LEFT)
        
        table_title = ttk.Label(table_title_frame, text="商品列表", 
                              font=("Microsoft YaHei UI", 14, "bold"))
        table_title.pack(side=LEFT)
        
        # 数据统计
        self.data_stats_label = ttk.Label(table_title_frame, text="", 
                                        font=("Microsoft YaHei UI", 10),
                                        foreground="#888")
        self.data_stats_label.pack(side=LEFT, padx=(15, 0))
        
        # 表格工具
        table_tools = ttk.Frame(table_header)
        table_tools.pack(side=RIGHT)
        
        # 刷新按钮
        refresh_btn = ttk.Button(table_tools, text="🔄 刷新", 
                               command=self.refresh_data,
                               bootstyle="outline-primary", width=10)
        refresh_btn.pack(side=LEFT)
        
        # 表格容器
        table_container = ttk.Frame(table_area)
        table_container.pack(fill=BOTH, expand=True)
        
        # 创建表格
        self._create_product_table(table_container)
        
        return page
    
    def _create_coupons_page(self):
        """创建优惠券页面"""
        page = ttk.Frame(self.content_area)
        
        # 页面标题区域
        header_area = ttk.Frame(page, padding=(0, 0, 0, 25))
        header_area.pack(fill=X)
        
        # 标题容器
        title_container = ttk.Frame(header_area)
        title_container.pack(fill=X)
        
        # 主标题
        main_title = ttk.Label(title_container, text="优惠券管理", 
                             font=("Microsoft YaHei UI", 20, "bold"))
        main_title.pack(side=LEFT)
        
        # 副标题
        sub_title = ttk.Label(title_container, text="Coupon Management", 
                            font=("Microsoft YaHei UI", 11),
                            foreground="#888")
        sub_title.pack(side=LEFT, padx=(15, 0), pady=(5, 0))
        
        # 操作按钮组
        action_container = ttk.Frame(title_container)
        action_container.pack(side=RIGHT)
        
        action_buttons = [
            {"text": "➕ 新增优惠券", "cmd": self._add_coupon, "style": "success", "width": 15},
            {"text": "✏️ 编辑", "cmd": self._edit_coupon, "style": "warning", "width": 10},
            {"text": "🗑️ 删除", "cmd": self._delete_coupon, "style": "danger", "width": 10}
        ]
        
        for i, btn_config in enumerate(action_buttons):
            btn = ttk.Button(action_container, 
                           text=btn_config["text"], 
                           command=btn_config["cmd"],
                           bootstyle=btn_config["style"], 
                           width=btn_config["width"])
            btn.pack(side=LEFT, padx=(8, 0) if i > 0 else (0, 0))
            self.add_button_hover_effect(btn)
        
        # 优惠券统计区域
        stats_area = ttk.Frame(page, padding=(0, 0, 0, 20))
        stats_area.pack(fill=X)
        
        # 统计卡片容器
        stats_container = ttk.Frame(stats_area)
        stats_container.pack(fill=X)
        
        # 优惠券统计卡片
        coupon_stats = [
            {"title": "总优惠券", "value": "0", "icon": "🎫", "color": "#F5A623", "key": "total"},
            {"title": "启用中", "value": "0", "icon": "✅", "color": "#7ED321", "key": "active"},
            {"title": "已过期", "value": "0", "icon": "⏰", "color": "#D0021B", "key": "expired"}
        ]
        
        # 存储统计卡片引用
        self.coupon_stats_cards = {}
        
        for i, stat in enumerate(coupon_stats):
            card = self._create_coupon_stat_card(stats_container, stat)
            card.grid(row=0, column=i, padx=(0, 15) if i < 2 else (0, 0), sticky="ew")
            self.coupon_stats_cards[stat["key"]] = card
        
        # 配置网格权重
        for i in range(3):
            stats_container.grid_columnconfigure(i, weight=1)
        
        # 优惠券列表区域
        list_area = ttk.Frame(page)
        list_area.pack(fill=BOTH, expand=True)
        
        # 列表标题栏
        list_header = ttk.Frame(list_area, padding=(0, 0, 0, 15))
        list_header.pack(fill=X)
        
        # 列表标题
        list_title = ttk.Label(list_header, text="优惠券列表", 
                             font=("Microsoft YaHei UI", 14, "bold"))
        list_title.pack(side=LEFT)
        
        # 列表工具
        list_tools = ttk.Frame(list_header)
        list_tools.pack(side=RIGHT)
        
        # 刷新按钮
        refresh_btn = ttk.Button(list_tools, text="🔄 刷新", 
                               command=self._refresh_coupons,
                               bootstyle="outline-primary", width=10)
        refresh_btn.pack(side=LEFT)
        
        # 表格容器
        table_container = ttk.Frame(list_area)
        table_container.pack(fill=BOTH, expand=True)
        
        # 创建优惠券表格
        self._create_coupon_table(table_container)
        
        # 初始化数据加载
        self.after(100, self._refresh_coupons)  # 延迟加载以确保UI完全创建
        
        return page
    
    def _create_coupon_stat_card(self, parent, config):
        """创建优惠券统计卡片"""
        card_container = ttk.Frame(parent)
        
        card = ttk.Frame(card_container, padding=(15, 12))
        card.pack(fill=BOTH, expand=True)
        
        # 图标和数值
        top_frame = ttk.Frame(card)
        top_frame.pack(fill=X, pady=(0, 8))
        
        icon_label = ttk.Label(top_frame, text=config["icon"], 
                              font=("Microsoft YaHei UI", 20))
        icon_label.pack(side=LEFT)
        
        value_label = ttk.Label(top_frame, text=config["value"], 
                               font=("Microsoft YaHei UI", 24, "bold"),
                               foreground=config["color"])
        value_label.pack(side=RIGHT)
        
        # 标题
        title_label = ttk.Label(card, text=config["title"],
                               font=("Microsoft YaHei UI", 11, "bold"))
        title_label.pack(anchor=tk.W)
        
        self.add_card_hover_effect(card)
        
        # 将value_label附加到card_container以便后续访问
        card_container.value_label = value_label
        
        return card_container
    
    def open_coupon_manager(self):
        """打开优惠券管理窗口（保持兼容性）"""
        self.show_page("coupons")
    
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
                try: 
                    widget.config(state=tk.DISABLED if busy else tk.NORMAL)
                except: 
                    pass
        
        # 只在SKU列表页面且tree存在时设置光标
        if hasattr(self, 'tree') and self.tree:
            try:
                self.tree.config(cursor="wait" if busy else "")
            except:
                pass
        
        self.update_idletasks()

    def show_skeleton_loader(self):
        # 只在SKU列表页面且tree存在时显示骨架加载
        if hasattr(self, 'tree') and self.tree:
            try:
                self.tree.delete(*self.tree.get_children())
                self.tree.configure(style="Skeleton.Treeview")
                skeleton_item = ('▓▓▓', '▓▓▓▓▓▓▓▓', '▓▓▓▓▓▓', '▓▓▓▓▓▓▓▓▓▓▓', '▓▓.▓▓', '▓▓▓', '▓▓▓▓▓▓▓▓▓▓', '▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓')
                for i in range(SKELETON_ROWS):
                    self.tree.insert("", tk.END, values=skeleton_item, tags=('skeleton',))
            except:
                pass
        
        self.update_status("正在加载数据...", "⏳", True)
        if hasattr(self, 'info_label'):
            self.info_label.config(text="")
        if hasattr(self, 'data_stats_label'):
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
        # 只在SKU列表页面且tree存在时处理
        if not (hasattr(self, 'tree') and self.tree):
            return
            
        try:
            # 暂时禁用重绘以提高性能
            self.tree.configure(cursor="wait")
            
            if is_new_query:
                # 批量删除以提高性能
                children = self.tree.get_children()
                if children:
                    self.tree.delete(*children)
                self.tree.configure(style="Custom.Treeview") # Restore normal style
                # Clear selection when loading new data
                self.last_clicked_row = None
                self.last_clicked_column_index = -1

            # 批量插入数据以提高性能
            if products:
                items_to_insert = []
                for product_row in products:
                    # 计算到手价
                    product_dict = dict(zip(database.DB_COLUMNS, product_row))
                    final_price = database.calculate_final_price(
                        product_dict.get('price', 0), 
                        product_dict.get('shop', ''),
                        product_dict.get('product_id', '')
                    )
                    
                    # 构建显示数据，包含到手价
                    display_data = {}
                    for col in database.DB_COLUMNS:
                        display_data[col] = product_dict[col]
                    display_data['final_price'] = final_price
                    
                    reordered_values = [display_data.get(col, '') for col in DISPLAY_COLUMNS]
                    items_to_insert.append(tuple(reordered_values))
                
                # 分批插入，避免界面卡顿
                batch_size = 20
                for i in range(0, len(items_to_insert), batch_size):
                    batch = items_to_insert[i:i+batch_size]
                    for values in batch:
                        self.tree.insert("", tk.END, values=values)
                    
                    # 每批次后更新界面，保持响应性
                    if i + batch_size < len(items_to_insert):
                        self.update_idletasks()
            
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
            if hasattr(self, 'info_label'):
                self.info_label.config(text=info_text)
            if hasattr(self, 'data_stats_label'):
                self.data_stats_label.config(text=f"({self.current_offset}/{self.total_items})")
            
            # 恢复正常光标
            self.tree.configure(cursor="")
            
        except Exception as e:
            print(f"页面加载完成时出错: {e}")
        
        self.set_busy(False)

    # --- Event Handlers ---
    def _on_y_scroll(self, *args):
        """处理垂直滚动条更新和懒加载"""
        # 更新垂直滚动条显示
        self.v_scrollbar.set(*args)
        
        # 检查是否需要懒加载更多数据
        if len(args) >= 2:
            first, last = args[0], args[1]
            if float(last) > 0.85 and not self.is_busy and not self.all_data_loaded:
                # 提前触发加载，让滚动更顺畅
                self.after_idle(self.load_next_page)
    
    def _on_mouse_wheel(self, event):
        """处理鼠标滚轮垂直滚动 - 优化滚动速度和节流"""
        import time
        current_time = time.time()
        
        # 滚动节流 - 避免过于频繁的滚动
        if current_time - self._last_scroll_time < 0.016:  # 约60fps
            return "break"
        
        self._last_scroll_time = current_time
        
        # 计算滚动量 - 调整为更顺畅的滚动
        delta = int(-1 * (event.delta / 120))
        scroll_amount = delta * 2  # 适中的滚动量
        
        # 执行滚动
        self.tree.yview_scroll(scroll_amount, "units")
        
        # 延迟检查懒加载，避免滚动时卡顿
        if self._scroll_timer:
            self.after_cancel(self._scroll_timer)
        
        self._scroll_timer = self.after(100, self._check_lazy_load)
        
        return "break"  # 阻止默认滚动行为
    
    def _on_horizontal_scroll(self, event):
        """处理横向滚动（Shift+鼠标滚轮）- 优化滚动速度"""
        delta = int(-1 * (event.delta / 120))
        scroll_amount = delta * 3  # 调整横向滚动速度，让横向滚动更明显
        self.tree.xview_scroll(scroll_amount, "units")
        return "break"
    
    def _check_lazy_load(self):
        """检查是否需要懒加载 - 延迟执行避免滚动卡顿"""
        try:
            visible_range = self.tree.yview()
            if len(visible_range) >= 2 and visible_range[1] > 0.85:
                if not self.is_busy and not self.all_data_loaded:
                    self.load_next_page()
        except:
            pass
    
    def smooth_scroll_to(self, target_position, steps=10):
        """平滑滚动到指定位置"""
        if self._smooth_scroll_active:
            return
            
        try:
            current_pos = self.tree.yview()[0]
            step_size = (target_position - current_pos) / steps
            
            def scroll_step(step):
                if step <= 0:
                    self._smooth_scroll_active = False
                    return
                    
                new_pos = current_pos + step_size * (steps - step + 1)
                self.tree.yview_moveto(new_pos)
                self.after(16, lambda: scroll_step(step - 1))  # 约60fps
            
            self._smooth_scroll_active = True
            scroll_step(steps)
        except:
            self._smooth_scroll_active = False
    
    def _on_key_scroll(self, event):
        """处理键盘滚动 - 优化响应速度"""
        key = event.keysym
        
        if key == "Up":
            self.tree.yview_scroll(-1, "units")
        elif key == "Down":
            self.tree.yview_scroll(1, "units")
        elif key == "Page_Up":
            self.tree.yview_scroll(-15, "units")  # 增加页面滚动量
        elif key == "Page_Down":
            self.tree.yview_scroll(15, "units")   # 增加页面滚动量
        elif key == "Home":
            self.tree.yview_moveto(0)
        elif key == "End":
            self.tree.yview_moveto(1)
            # End键时立即检查懒加载
            if not self.is_busy and not self.all_data_loaded:
                self.after_idle(self.load_next_page)
            
        # 延迟检查懒加载
        if key in ["Down", "Page_Down"]:
            if self._scroll_timer:
                self.after_cancel(self._scroll_timer)
            self._scroll_timer = self.after(50, self._check_lazy_load)
            
        return "break"
    
    def _on_scroll(self, *args):
        """原始滚动处理方法（保持兼容性）"""
        first, last = args
        if float(last) > 0.85 and not self.is_busy and not self.all_data_loaded:
            self.after_idle(self.load_next_page)

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
            sheet1_dtypes = { '规格ID': str, '规格编码': str }
            sheet2_dtypes = { '无效的规格ID': str }
            sheet3_dtypes = { '启用的规格编码': str, '分类': str, '仓库': str, '简称': str, '最低价': str }
            sheet4_dtypes = { '简称': str, '采购价': str }
            
            df = pd.read_excel(file_path, sheet_name='Sheet1', dtype=sheet1_dtypes)
            df_sheet2 = pd.read_excel(file_path, sheet_name='Sheet2', dtype=sheet2_dtypes)
            df_sheet3 = pd.read_excel(file_path, sheet_name='Sheet3', dtype=sheet3_dtypes)
            
            # 尝试读取Sheet4，如果不存在则创建空DataFrame
            try:
                df_sheet4 = pd.read_excel(file_path, sheet_name='Sheet4', dtype=sheet4_dtypes)
            except:
                df_sheet4 = pd.DataFrame(columns=['简称', '采购价'])
            
            # 处理Sheet3的额外字段数据
            sheet3_extra_data = {}
            if not df_sheet3.empty:
                for _, row in df_sheet3.iterrows():
                    sku_code = str(row.get('启用的规格编码', '')).strip()
                    if sku_code and sku_code != '':
                        sheet3_extra_data[sku_code] = {
                            'category': str(row.get('分类', '')).strip(),
                            'warehouse': str(row.get('仓库', '')).strip(), 
                            'short_name': str(row.get('简称', '')).strip(),
                            'min_price': str(row.get('最低价', '')).strip()
                        }
            
            # 处理Sheet4的采购价数据
            sheet4_purchase_data = {}
            if not df_sheet4.empty:
                for _, row in df_sheet4.iterrows():
                    short_name = str(row.get('简称', '')).strip()
                    if short_name and short_name != '':
                        sheet4_purchase_data[short_name] = str(row.get('采购价', '')).strip()
            
            report_df = df.copy(); total_rows = len(report_df)
            invalid_ids = set(df_sheet2['无效的规格ID'].dropna().astype(str).str.strip().str.lower())
            enabled_codes = set(df_sheet3['启用的规格编码'].dropna().astype(str).str.strip())
            
            # 更新数据库中的筛选条件
            database.update_invalid_spec_ids(invalid_ids)
            database.update_enabled_skus(enabled_codes)
            
            # 添加新字段到主数据
            report_df['分类'] = ''
            report_df['仓库'] = ''
            report_df['简称'] = ''
            report_df['最低价'] = ''
            report_df['采购价'] = ''
            
            # 根据规格编码合并Sheet3的数据
            for index, row in report_df.iterrows():
                sku_code = str(row.get('规格编码', '')).strip()
                if sku_code in sheet3_extra_data:
                    extra_data = sheet3_extra_data[sku_code]
                    report_df.at[index, '分类'] = extra_data['category']
                    report_df.at[index, '仓库'] = extra_data['warehouse']
                    report_df.at[index, '简称'] = extra_data['short_name']
                    report_df.at[index, '最低价'] = extra_data['min_price']
                    
                    # 根据简称从Sheet4获取采购价
                    short_name = extra_data['short_name']
                    if short_name in sheet4_purchase_data:
                        report_df.at[index, '采购价'] = sheet4_purchase_data[short_name]
            
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

# --- 优惠券管理窗口 ---
class CouponManagerWindow(ttk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("优惠券管理")
        self.geometry("900x600")
        self.minsize(800, 500)
        self.transient(parent)
        self.grab_set()
        
        self.center_window()
        self._build_ui()
        self.load_coupons()
    
    def center_window(self):
        """窗口居中显示"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _build_ui(self):
        # 主容器
        main_frame = ttk.Frame(self, padding=(20, 20, 20, 20))
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🎫 优惠券管理", 
                               font=("Microsoft YaHei UI", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 操作按钮栏
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Button(button_frame, text="➕ 新增优惠券", command=self.add_coupon,
                  bootstyle="success", width=15).pack(side=LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="✏️ 编辑", command=self.edit_coupon,
                  bootstyle="warning", width=10).pack(side=LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑️ 删除", command=self.delete_coupon,
                  bootstyle="danger", width=10).pack(side=LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 刷新", command=self.load_coupons,
                  bootstyle="secondary", width=10).pack(side=RIGHT)
        
        # 优惠券列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=BOTH, expand=True)
        
        # 表格
        columns = ['id', 'shop', 'coupon_type', 'amount', 'min_price', 
                  'start_date', 'end_date', 'description', 'is_active']
        
        self.coupon_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # 配置列
        column_configs = {
            'id': {'width': 50, 'anchor': CENTER},
            'shop': {'width': 100, 'anchor': CENTER},
            'coupon_type': {'width': 80, 'anchor': CENTER},
            'amount': {'width': 80, 'anchor': CENTER},
            'min_price': {'width': 80, 'anchor': CENTER},
            'start_date': {'width': 100, 'anchor': CENTER},
            'end_date': {'width': 100, 'anchor': CENTER},
            'description': {'width': 150, 'anchor': tk.W},
            'is_active': {'width': 60, 'anchor': CENTER}
        }
        
        for col in columns:
            header_text = COUPON_HEADER_MAP.get(col, col)
            self.coupon_tree.heading(col, text=header_text, anchor=CENTER)
            config = column_configs.get(col, {'width': 100, 'anchor': CENTER})
            self.coupon_tree.column(col, **config, minwidth=50)
        
        # 滚动条
        v_scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.coupon_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=HORIZONTAL, command=self.coupon_tree.xview)
        
        self.coupon_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.coupon_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 双击编辑
        self.coupon_tree.bind("<Double-Button-1>", lambda e: self.edit_coupon())
    
    def load_coupons(self):
        """加载优惠券数据"""
        # 清空现有数据
        for item in self.coupon_tree.get_children():
            self.coupon_tree.delete(item)
        
        # 加载数据
        coupons = database.get_all_coupons()
        for coupon in coupons:
            coupon_dict = dict(zip(database.COUPON_COLUMNS, coupon))
            
            # 格式化显示数据
            display_data = []
            for col in ['id', 'shop', 'coupon_type', 'amount', 'min_price', 
                       'start_date', 'end_date', 'description', 'is_active']:
                value = coupon_dict[col]
                
                if col == 'coupon_type':
                    value = '固定金额' if value == 'fixed' else '百分比'
                elif col == 'amount':
                    coupon_type = coupon_dict['coupon_type']
                    if coupon_type == 'fixed':
                        value = f"¥{value}"
                    else:
                        value = f"{value}%"
                elif col == 'is_active':
                    value = '启用' if value else '禁用'
                
                display_data.append(str(value))
            
            self.coupon_tree.insert("", tk.END, values=display_data)
    
    def add_coupon(self):
        """添加优惠券"""
        CouponEditorWindow(self)
    
    def edit_coupon(self):
        """编辑优惠券"""
        selected = self.coupon_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要编辑的优惠券", parent=self)
            return
        
        item = selected[0]
        values = self.coupon_tree.item(item, 'values')
        coupon_id = values[0]
        
        coupon = database.get_coupon_by_id(coupon_id)
        if coupon:
            coupon_dict = dict(zip(database.COUPON_COLUMNS, coupon))
            CouponEditorWindow(self, coupon_dict)
    
    def delete_coupon(self):
        """删除优惠券"""
        selected = self.coupon_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要删除的优惠券", parent=self)
            return
        
        if messagebox.askyesno("确认删除", "确定要删除选中的优惠券吗？", parent=self):
            for item in selected:
                values = self.coupon_tree.item(item, 'values')
                coupon_id = values[0]
                database.delete_coupon(coupon_id)
            
            self.load_coupons()
            messagebox.showinfo("成功", "优惠券删除成功", parent=self)

# --- 优惠券编辑窗口 ---
class CouponEditorWindow(ttk.Toplevel):
    def __init__(self, parent, coupon=None):
        super().__init__(parent)
        self.parent = parent
        self.coupon = coupon
        self.title("编辑优惠券" if coupon else "新增优惠券")
        self.geometry("500x600")
        self.minsize(450, 550)
        self.transient(parent)
        self.grab_set()
        
        self.center_window()
        self._build_ui()
    
    def center_window(self):
        """窗口居中显示"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _build_ui(self):
        # 主容器
        main_frame = ttk.Frame(self, padding=(30, 25, 30, 25))
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        title_text = "编辑优惠券" if self.coupon else "新增优惠券"
        title_label = ttk.Label(main_frame, text=title_text, 
                               font=("Microsoft YaHei UI", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 25), sticky=tk.W)
        
        # 表单字段
        self.entries = {}
        row = 1
        
        # 店铺下拉选择
        ttk.Label(main_frame, text="店铺", font=("Microsoft YaHei UI", 11)).grid(
            row=row, column=0, padx=(0, 20), pady=(0, 18), sticky=tk.W)
        
        self.shop_var = tk.StringVar()
        self.shop_combobox = ttk.Combobox(main_frame, textvariable=self.shop_var,
                                        font=("Microsoft YaHei UI", 11), width=26,
                                        state="readonly")
        self.shop_combobox.grid(row=row, column=1, pady=(0, 18), sticky=tk.EW)
        self.shop_combobox.bind("<<ComboboxSelected>>", self.on_shop_changed)
        
        # 加载店铺列表
        shops = database.get_all_shops()
        self.shop_combobox['values'] = shops
        row += 1
        
        # 优惠券类型
        ttk.Label(main_frame, text="类型", font=("Microsoft YaHei UI", 11)).grid(
            row=row, column=0, padx=(0, 20), pady=(0, 18), sticky=tk.W)
        self.coupon_type_var = tk.StringVar(value="instant")
        type_frame = ttk.Frame(main_frame)
        type_frame.grid(row=row, column=1, pady=(0, 18), sticky=tk.W)
        
        ttk.Radiobutton(type_frame, text="立减券", variable=self.coupon_type_var, 
                       value="instant", command=self.on_type_changed).pack(side=LEFT, padx=(0, 15))
        ttk.Radiobutton(type_frame, text="满减券", variable=self.coupon_type_var, 
                       value="threshold", command=self.on_type_changed).pack(side=LEFT, padx=(0, 15))
        ttk.Radiobutton(type_frame, text="折扣券", variable=self.coupon_type_var, 
                       value="discount", command=self.on_type_changed).pack(side=LEFT)
        row += 1
        
        # 面额/折扣
        self.amount_label = ttk.Label(main_frame, text="面额", font=("Microsoft YaHei UI", 11))
        self.amount_label.grid(row=row, column=0, padx=(0, 20), pady=(0, 18), sticky=tk.W)
        
        amount_frame = ttk.Frame(main_frame)
        amount_frame.grid(row=row, column=1, pady=(0, 18), sticky=tk.EW)
        
        self.entries['amount'] = ttk.Entry(amount_frame, font=("Microsoft YaHei UI", 11), width=20)
        self.entries['amount'].pack(side=LEFT, fill=X, expand=True)
        
        self.amount_unit_label = ttk.Label(amount_frame, text="元", font=("Microsoft YaHei UI", 11))
        self.amount_unit_label.pack(side=LEFT, padx=(5, 0))
        row += 1
        
        # 最低消费（满减券专用）
        self.min_price_label = ttk.Label(main_frame, text="最低消费", font=("Microsoft YaHei UI", 11))
        self.min_price_label.grid(row=row, column=0, padx=(0, 20), pady=(0, 18), sticky=tk.W)
        self.entries['min_price'] = ttk.Entry(main_frame, font=("Microsoft YaHei UI", 11), width=28)
        self.entries['min_price'].grid(row=row, column=1, pady=(0, 18), sticky=tk.EW)
        row += 1
        
        # 开始日期
        ttk.Label(main_frame, text="开始日期", font=("Microsoft YaHei UI", 11)).grid(
            row=row, column=0, padx=(0, 20), pady=(0, 18), sticky=tk.W)
        self.entries['start_date'] = ttk.Entry(main_frame, font=("Microsoft YaHei UI", 11), width=28)
        self.entries['start_date'].grid(row=row, column=1, pady=(0, 18), sticky=tk.EW)
        row += 1
        
        # 结束日期
        ttk.Label(main_frame, text="结束日期", font=("Microsoft YaHei UI", 11)).grid(
            row=row, column=0, padx=(0, 20), pady=(0, 18), sticky=tk.W)
        self.entries['end_date'] = ttk.Entry(main_frame, font=("Microsoft YaHei UI", 11), width=28)
        self.entries['end_date'].grid(row=row, column=1, pady=(0, 18), sticky=tk.EW)
        row += 1
        
        # 适用商品选择
        ttk.Label(main_frame, text="适用范围", font=("Microsoft YaHei UI", 11)).grid(
            row=row, column=0, padx=(0, 20), pady=(0, 18), sticky=tk.NW)
        
        product_frame = ttk.Frame(main_frame)
        product_frame.grid(row=row, column=1, pady=(0, 18), sticky=tk.EW)
        
        # 全店/指定货品选择
        self.product_scope_var = tk.StringVar(value="all")
        ttk.Radiobutton(product_frame, text="全店通用", variable=self.product_scope_var, 
                       value="all", command=self.on_scope_changed).pack(anchor=tk.W)
        ttk.Radiobutton(product_frame, text="指定货品", variable=self.product_scope_var, 
                       value="specific", command=self.on_scope_changed).pack(anchor=tk.W, pady=(5, 0))
        
        # 说明文字
        hint_label = ttk.Label(product_frame, text="注：选择货品后，优惠券将对该货品下的所有SKU生效", 
                             font=("Microsoft YaHei UI", 8), foreground="#666")
        hint_label.pack(anchor=tk.W, pady=(2, 0))
        
        # 详细说明
        detail_label = ttk.Label(product_frame, text="例如：选择货品A，则货品A的所有规格（SKU）都可使用此优惠券", 
                               font=("Microsoft YaHei UI", 8), foreground="#888")
        detail_label.pack(anchor=tk.W, pady=(2, 0))
        
        # 商品搜索和选择区域
        self.product_listbox_frame = ttk.Frame(product_frame)
        self.product_listbox_frame.pack(fill=BOTH, expand=True, pady=(10, 0))
        
        # 商品搜索框
        search_frame = ttk.Frame(self.product_listbox_frame)
        search_frame.pack(fill=X, pady=(0, 8))
        
        ttk.Label(search_frame, text="🔍 搜索货品:", 
                 font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.product_search_var = tk.StringVar()
        self.product_search_entry = ttk.Entry(search_frame, 
                                            textvariable=self.product_search_var,
                                            font=("Microsoft YaHei UI", 9),
                                            width=25)
        self.product_search_entry.pack(side=tk.LEFT, fill=X, expand=True, padx=(0, 5))
        self.product_search_var.trace('w', self.on_product_search)
        
        # 设置搜索框占位符
        self.setup_product_search_placeholder()
        
        # 清除搜索按钮
        clear_search_btn = ttk.Button(search_frame, text="清除", 
                                    command=self.clear_product_search,
                                    bootstyle="secondary-outline", width=6)
        clear_search_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 全选/取消全选按钮
        select_all_btn = ttk.Button(search_frame, text="全选", 
                                  command=self.select_all_products,
                                  bootstyle="info-outline", width=6)
        select_all_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        select_none_btn = ttk.Button(search_frame, text="取消", 
                                   command=self.select_none_products,
                                   bootstyle="warning-outline", width=6)
        select_none_btn.pack(side=tk.LEFT)
        
        # 商品计数显示
        count_frame = ttk.Frame(self.product_listbox_frame)
        count_frame.pack(fill=X, pady=(5, 0))
        
        self.product_count_label = ttk.Label(count_frame, text="", 
                                           font=("Microsoft YaHei UI", 8),
                                           foreground="#888")
        self.product_count_label.pack(side=tk.LEFT)
        
        # 选择状态显示
        self.selection_status_label = ttk.Label(count_frame, text="", 
                                              font=("Microsoft YaHei UI", 8),
                                              foreground="#4A90E2")
        self.selection_status_label.pack(side=tk.RIGHT)
        
        # 商品列表框容器
        listbox_container = ttk.Frame(self.product_listbox_frame)
        listbox_container.pack(fill=BOTH, expand=True)
        
        try:
            self.product_listbox = tk.Listbox(listbox_container, 
                                            font=("Microsoft YaHei UI", 10),
                                            height=6, selectmode=tk.MULTIPLE)
            product_scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL, 
                                            command=self.product_listbox.yview)
            self.product_listbox.configure(yscrollcommand=product_scrollbar.set)
            
            self.product_listbox.pack(side=tk.LEFT, fill=BOTH, expand=True)
            product_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 绑定选择变化事件
            self.product_listbox.bind("<<ListboxSelect>>", self.on_product_selection_changed)
        except Exception as e:
            print(f"创建product_listbox时出错: {e}")
            # 创建一个空的占位符
            self.product_listbox = None
        
        # 存储所有商品数据用于搜索
        self.all_products = []
        
        # 初始状态禁用货品选择
        self.product_listbox.configure(state=tk.DISABLED)
        self.product_search_entry.configure(state=tk.DISABLED)
        self.product_count_label.config(text="请先选择店铺")
        row += 1
        
        # 描述
        ttk.Label(main_frame, text="描述", font=("Microsoft YaHei UI", 11)).grid(
            row=row, column=0, padx=(0, 20), pady=(0, 18), sticky=tk.NW)
        self.entries['description'] = tk.Text(main_frame, font=("Microsoft YaHei UI", 11), 
                                            width=28, height=3)
        self.entries['description'].grid(row=row, column=1, pady=(0, 18), sticky=tk.EW)
        row += 1
        
        # 是否启用
        self.is_active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="启用优惠券", variable=self.is_active_var,
                       bootstyle="round-toggle").grid(row=row, column=0, columnspan=2, 
                                                     pady=(10, 20), sticky=tk.W)
        row += 1
        
        main_frame.grid_columnconfigure(1, weight=1)
        
        # 填充现有数据
        if self.coupon:
            self.shop_var.set(self.coupon.get('shop', ''))
            self.on_shop_changed()  # 加载商品列表
            
            coupon_type = self.coupon.get('coupon_type', 'instant')
            self.coupon_type_var.set(coupon_type)
            self.on_type_changed()  # 更新界面
            
            amount = self.coupon.get('amount', '')
            if coupon_type == 'discount':
                # 折扣券显示百分比
                self.entries['amount'].insert(0, str(int(float(amount) * 100)))
            else:
                self.entries['amount'].insert(0, str(amount))
                
            self.entries['min_price'].insert(0, str(self.coupon.get('min_price', '0')))
            self.entries['start_date'].insert(0, self.coupon.get('start_date', ''))
            self.entries['end_date'].insert(0, self.coupon.get('end_date', ''))
            self.entries['description'].insert('1.0', self.coupon.get('description', ''))
            self.is_active_var.set(bool(self.coupon.get('is_active', 1)))
            
            # 处理商品选择
            product_ids_str = self.coupon.get('product_ids', '')
            if product_ids_str:
                try:
                    product_ids = json.loads(product_ids_str)
                    self.product_scope_var.set("specific")
                    self.on_scope_changed()
                    
                    # 等待商品列表加载完成后选中对应的商品
                    self.after(100, lambda: self.select_products_by_ids(product_ids))
                except:
                    pass
        else:
            # 默认日期
            from datetime import datetime, timedelta
            today = datetime.now()
            self.entries['start_date'].insert(0, today.strftime('%Y-%m-%d'))
            self.entries['end_date'].insert(0, (today + timedelta(days=30)).strftime('%Y-%m-%d'))
            
        # 初始化界面状态
        self.on_type_changed()
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=(25, 0), sticky=tk.EW)
        
        ttk.Button(button_frame, text="取消", command=self.destroy, 
                  bootstyle="secondary", width=12).pack(side=RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="保存", command=self.save, 
                  bootstyle="success", width=12).pack(side=RIGHT)
    
    def on_shop_changed(self, event=None):
        """店铺选择改变时加载货品列表"""
        shop = self.shop_var.get()
        if not shop:
            self.all_products = []
            if hasattr(self, 'product_listbox') and self.product_listbox is not None:
                self.product_listbox.delete(0, tk.END)
            return
            
        # 加载该店铺的货品（按货品ID去重）
        products = database.get_products_by_shop(shop)
        self.all_products = [(product_id, name) for product_id, name in products]
        
        # 更新货品列表显示
        self.update_product_list()
        
        # 清空搜索框
        self.product_search_var.set("")
    
    def on_type_changed(self):
        """优惠券类型改变时更新界面"""
        coupon_type = self.coupon_type_var.get()
        
        if coupon_type == 'instant':
            # 立减券
            self.amount_label.config(text="立减金额")
            self.amount_unit_label.config(text="元")
            self.min_price_label.grid_remove()
            self.entries['min_price'].grid_remove()
            
        elif coupon_type == 'threshold':
            # 满减券
            self.amount_label.config(text="减免金额")
            self.amount_unit_label.config(text="元")
            self.min_price_label.grid()
            self.entries['min_price'].grid()
            
        elif coupon_type == 'discount':
            # 折扣券
            self.amount_label.config(text="折扣")
            self.amount_unit_label.config(text="%")
            self.min_price_label.grid_remove()
            self.entries['min_price'].grid_remove()
    
    def on_scope_changed(self):
        """适用范围改变时更新界面"""
        if not hasattr(self, 'product_listbox') or self.product_listbox is None:
            return
            
        if self.product_scope_var.get() == "all":
            self.product_listbox.configure(state=tk.DISABLED)
            self.product_search_entry.configure(state=tk.DISABLED)
            self.product_listbox.selection_clear(0, tk.END)
            self.product_count_label.config(text="全店通用，无需选择货品")
            self.selection_status_label.config(text="")
        else:
            self.product_listbox.configure(state=tk.NORMAL)
            self.product_search_entry.configure(state=tk.NORMAL)
            # 如果有货品数据，更新计数显示
            if self.all_products:
                self.update_product_list()
                self.on_product_selection_changed(None)  # 更新选择状态
            else:
                self.product_count_label.config(text="请先选择店铺")
                self.selection_status_label.config(text="")
    
    def update_product_list(self, search_term=""):
        """更新货品列表显示"""
        # 检查product_listbox是否存在
        if not hasattr(self, 'product_listbox') or self.product_listbox is None:
            print("警告: product_listbox 不存在，跳过更新")
            return
            
        # 清空当前列表
        self.product_listbox.delete(0, tk.END)
        
        # 根据搜索条件筛选货品
        filtered_products = []
        search_term = search_term.lower().strip()
        
        for product_id, name in self.all_products:
            if not search_term or (search_term in product_id.lower() or search_term in name.lower()):
                filtered_products.append((product_id, name))
        
        # 添加筛选后的货品到列表
        for product_id, name in filtered_products:
            display_text = f"{product_id} - {name}"
            self.product_listbox.insert(tk.END, display_text)
        
        # 更新货品计数显示
        total_count = len(self.all_products)
        filtered_count = len(filtered_products)
        
        if search_term:
            self.product_count_label.config(text=f"🔍 找到 {filtered_count} 个货品（共 {total_count} 个）")
            if filtered_count == 0:
                self.product_count_label.config(text=f"🔍 未找到匹配的货品（共 {total_count} 个）")
        else:
            self.product_count_label.config(text=f"📦 共 {total_count} 个货品")
    
    def on_product_search(self, *args):
        """商品搜索框内容改变时触发"""
        # 检查必要的属性是否存在
        if not hasattr(self, 'product_search_var') or not hasattr(self, 'product_search_placeholder'):
            return
            
        search_term = self.product_search_var.get()
        # 如果是占位符文本，则不进行搜索
        if search_term == self.product_search_placeholder:
            search_term = ""
        self.update_product_list(search_term)
    
    def clear_product_search(self):
        """清除商品搜索"""
        self.product_search_entry.delete(0, tk.END)
        self.product_search_entry.insert(0, self.product_search_placeholder)
        self.product_search_entry.configure(foreground=self.product_search_placeholder_color)
        self.update_product_list()
    
    def select_products_by_ids(self, product_ids):
        """根据货品ID列表选中对应的货品"""
        if not product_ids or not hasattr(self, 'product_listbox') or self.product_listbox is None:
            return
            
        try:
            # 清除当前选择
            self.product_listbox.selection_clear(0, tk.END)
            
            # 选中对应的货品
            for i in range(self.product_listbox.size()):
                product_text = self.product_listbox.get(i)
                product_id = product_text.split(' - ')[0]
                if product_id in product_ids:
                    self.product_listbox.selection_set(i)
        except Exception as e:
            print(f"选择货品时出错: {e}")
    
    def setup_product_search_placeholder(self):
        """设置货品搜索框占位符"""
        self.product_search_placeholder = "输入货品ID或名称..."
        self.product_search_placeholder_color = '#888'
        
        # 设置初始占位符
        self.product_search_entry.insert(0, self.product_search_placeholder)
        self.product_search_entry.configure(foreground=self.product_search_placeholder_color)
        
        # 绑定焦点事件
        self.product_search_entry.bind("<FocusIn>", self.on_product_search_focus_in)
        self.product_search_entry.bind("<FocusOut>", self.on_product_search_focus_out)
    
    def on_product_search_focus_in(self, event):
        """货品搜索框获得焦点"""
        if self.product_search_entry.get() == self.product_search_placeholder:
            self.product_search_entry.delete(0, tk.END)
            self.product_search_entry.configure(foreground='white')
    
    def on_product_search_focus_out(self, event):
        """货品搜索框失去焦点"""
        if not self.product_search_entry.get().strip():
            self.product_search_entry.delete(0, tk.END)
            self.product_search_entry.insert(0, self.product_search_placeholder)
            self.product_search_entry.configure(foreground=self.product_search_placeholder_color)
    
    def select_all_products(self):
        """全选当前显示的货品"""
        if hasattr(self, 'product_listbox') and self.product_listbox is not None:
            if self.product_listbox.cget('state') == tk.NORMAL:
                self.product_listbox.selection_set(0, tk.END)
    
    def select_none_products(self):
        """取消选择所有货品"""
        if hasattr(self, 'product_listbox') and self.product_listbox is not None:
            if self.product_listbox.cget('state') == tk.NORMAL:
                self.product_listbox.selection_clear(0, tk.END)
    
    def on_product_selection_changed(self, event):
        """货品选择变化时更新状态显示"""
        if not hasattr(self, 'product_listbox') or self.product_listbox is None:
            return
            
        if self.product_scope_var.get() == "specific":
            selected_count = len(self.product_listbox.curselection())
            if selected_count > 0:
                self.selection_status_label.config(text=f"✓ 已选择 {selected_count} 个货品")
            else:
                self.selection_status_label.config(text="请选择货品")
        else:
            self.selection_status_label.config(text="")
    
    def save(self):
        """保存优惠券"""
        try:
            # 收集基本数据
            shop = self.shop_var.get().strip()
            coupon_type = self.coupon_type_var.get()
            amount_str = self.entries['amount'].get().strip()
            min_price = float(self.entries['min_price'].get() or 0)
            
            # 验证基本数据
            if not shop:
                messagebox.showerror("错误", "请选择店铺", parent=self)
                return
            
            if not amount_str:
                messagebox.showerror("错误", "面额/折扣不能为空", parent=self)
                return
            
            # 处理金额/折扣
            if coupon_type == 'discount':
                # 折扣券：输入的是百分比，存储为小数
                discount_percent = float(amount_str)
                if discount_percent <= 0 or discount_percent >= 100:
                    messagebox.showerror("错误", "折扣必须在0-100之间", parent=self)
                    return
                amount = discount_percent / 100
            else:
                # 立减券和满减券：直接使用金额
                amount = float(amount_str)
                if amount <= 0:
                    messagebox.showerror("错误", "金额必须大于0", parent=self)
                    return
            
            # 处理货品选择
            product_ids = []
            if self.product_scope_var.get() == "specific":
                if not hasattr(self, 'product_listbox') or self.product_listbox is None:
                    messagebox.showerror("错误", "货品列表未正确初始化", parent=self)
                    return
                    
                selected_indices = self.product_listbox.curselection()
                if not selected_indices:
                    messagebox.showerror("错误", "请选择适用的货品", parent=self)
                    return
                
                for index in selected_indices:
                    product_text = self.product_listbox.get(index)
                    product_id = product_text.split(' - ')[0]
                    product_ids.append(product_id)
            
            # 构建优惠券数据
            coupon_data = {
                'shop': shop,
                'coupon_type': coupon_type,
                'amount': amount,
                'min_price': min_price,
                'start_date': self.entries['start_date'].get().strip(),
                'end_date': self.entries['end_date'].get().strip(),
                'description': self.entries['description'].get('1.0', tk.END).strip(),
                'is_active': 1 if self.is_active_var.get() else 0,
                'product_ids': json.dumps(product_ids) if product_ids else ''
            }
            
            # 验证日期
            if not coupon_data['start_date'] or not coupon_data['end_date']:
                messagebox.showerror("错误", "开始日期和结束日期不能为空", parent=self)
                return
            
            # 保存到数据库
            if self.coupon:
                coupon_data['id'] = self.coupon['id']
                database.update_coupon(coupon_data)
                messagebox.showinfo("成功", "优惠券更新成功", parent=self)
            else:
                database.add_coupon(coupon_data)
                messagebox.showinfo("成功", "优惠券添加成功", parent=self)
            
            # 刷新数据
            if hasattr(self.parent, '_refresh_coupons'):
                # 如果是主窗口调用
                self.parent._refresh_coupons()
                # 刷新SKU列表的到手价
                if hasattr(self.parent, 'tree'):
                    self.parent.start_new_load(force=True)
            elif hasattr(self.parent, 'load_coupons'):
                # 如果是优惠券管理窗口调用
                self.parent.load_coupons()
                if hasattr(self.parent, 'parent'):
                    self.parent.parent.start_new_load(force=True)
            
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("错误", "请输入有效的数字", parent=self)
        except Exception as e:
            messagebox.showerror("保存失败", f"发生错误: {e}", parent=self)

if __name__ == "__main__":
    database.init_db()
    app = App()
    app.mainloop()
