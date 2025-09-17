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
        self.title("编辑商品" if self.product else "添加商品")
        self.geometry("400x450")
        self.transient(parent)
        self.grab_set()

        self.entries = {}
        for i, db_col in enumerate(DB_COLUMNS):
            header = HEADER_MAP[db_col]
            ttk.Label(self, text=f"{header}:").grid(row=i, column=0, padx=10, pady=10, sticky=tk.W)
            entry = ttk.Entry(self)
            entry.grid(row=i, column=1, padx=10, pady=10, sticky=tk.EW)
            self.entries[db_col] = entry

        self.grid_columnconfigure(1, weight=1)

        if self.product:
            for db_col in DB_COLUMNS:
                self.entries[db_col].insert(0, self.product.get(db_col, ''))
            self.entries['sku'].config(state='readonly')

        ttk.Button(self, text="保存", command=self.save, bootstyle=SUCCESS).grid(row=len(DB_COLUMNS), column=0, columnspan=2, pady=20)

    def save(self):
        try:
            product_data = {db_col: self.entries[db_col].get().strip() for db_col in DB_COLUMNS}
            if not product_data['sku'] or not product_data['name']:
                messagebox.showerror("错误", "规格编码和货品名称不能为空。", parent=self)
                return

            product_data['price'] = float(product_data['price'] or 0)
            product_data['quantity'] = int(product_data['quantity'] or 0)

            def db_task():
                if self.product:
                    database.update_product(product_data)
                else:
                    if database.get_product_by_sku(product_data['sku']):
                        self.after(0, lambda: messagebox.showerror("错误", f"规格编码 '{product_data['sku']}' 已存在。", parent=self))
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
        self.title("商品信息管理系统")
        self.geometry("1200x700")

        # --- State Management for Lazy Loading ---
        self.is_busy = False
        self.is_loading_more = False
        self.current_offset = 0
        self.total_items = 0
        self.current_query = ""
        self.all_data_loaded = False

        self._build_ui()
        self.start_new_load()

    def _build_ui(self):
        # --- Top Action Bar ---
        top_frame = ttk.Frame(self, padding=(20, 15, 20, 10))
        top_frame.pack(fill=X)
        
        self.action_buttons = []
        btn_configs = [
            {"text": "📥 导入表格", "cmd": self.import_data, "style": PRIMARY},
            {"text": "➕ 添加", "cmd": self.open_add_window, "style": SUCCESS},
            {"text": "✏️ 编辑", "cmd": self.open_edit_window, "style": "outline-info"},
            {"text": "🗑️ 删除", "cmd": self.delete_products, "style": "outline-danger"}
        ]
        for config in btn_configs:
            btn = ttk.Button(top_frame, text=config["text"], command=config["cmd"], bootstyle=config["style"])
            btn.pack(side=LEFT, padx=(0, 10))
            self.action_buttons.append(btn)

        self.generate_report_var = tk.BooleanVar()
        self.report_checkbutton = ttk.Checkbutton(top_frame, text="生成调试报告", variable=self.generate_report_var, bootstyle="round-toggle")
        self.report_checkbutton.pack(side=LEFT, padx=20)
        self.action_buttons.append(self.report_checkbutton)

        self.clear_search_button = ttk.Button(top_frame, text="❌", command=self.clear_search, bootstyle="outline-secondary")
        self.clear_search_button.pack(side=RIGHT, padx=(10, 0))
        self.search_button = ttk.Button(top_frame, text="🔍 搜索", command=self.search_products, bootstyle="outline-primary")
        self.search_button.pack(side=RIGHT, padx=(10, 0))
        self.action_buttons.extend([self.clear_search_button, self.search_button])

        self.search_entry = ttk.Entry(top_frame)
        self.search_entry.pack(side=RIGHT, fill=X, expand=True)
        self.search_entry.bind("<Return>", self.search_products)
        self.action_buttons.append(self.search_entry)

        self.placeholder_text = "按 SKU、名称、规格等搜索..."
        self.placeholder_color = 'grey'
        try: self.default_fg_color = self.search_entry.cget("foreground")
        except: self.default_fg_color = 'white'
        self.search_entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.search_entry.bind("<FocusOut>", self.on_entry_focus_out)
        self.on_entry_focus_out(None)

        # --- Treeview Frame ---
        tree_frame = ttk.Frame(self, padding=(20, 0, 20, 10))
        tree_frame.pack(expand=True, fill=BOTH)

        style = ttk.Style()
        style.configure('Treeview', rowheight=28)
        style.configure("Skeleton.Treeview", foreground="#555")

        self.tree = ttk.Treeview(tree_frame, columns=DISPLAY_COLUMNS, show="headings", bootstyle="secondary")
        for col in DISPLAY_COLUMNS:
            self.tree.heading(col, text=HEADER_MAP.get(col, col))
            self.tree.column(col, anchor=CENTER, width=100)
        
        self.tree.column('name', width=250); self.tree.column('spec_name', width=200); self.tree.column('sku', width=150)

        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview, bootstyle="round")
        self.tree.configure(yscrollcommand=self._on_scroll)
        v_scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, expand=True, fill=BOTH)

        # --- Status Bar ---
        self.status_label = ttk.Label(self, text="准备就绪", padding=(20, 5))
        self.status_label.pack(side=BOTTOM, fill=X)

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
        skeleton_item = ('████', '████████', '██████', '███████████', '██.██', '███', '██████████', '████████████████')
        for i in range(SKELETON_ROWS):
            self.tree.insert("", tk.END, values=skeleton_item, tags=('skeleton',))

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
            self.status_label.config(text=f"正在加载更多... (已显示 {self.current_offset}/{self.total_items})")
        else:
            self.status_label.config(text=f'正在搜索 "{self.current_query}"...' if self.current_query else "正在加载...")

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

        for product_row in products:
            reordered_values = [product_row[col] for col in DISPLAY_COLUMNS]
            self.tree.insert("", tk.END, values=tuple(reordered_values))
        
        self.current_offset += len(products)
        if self.current_offset >= self.total_items:
            self.all_data_loaded = True

        self.status_label.config(text=f"显示 {self.current_offset} / {self.total_items} 条记录")
        self.set_busy(False)

    # --- Event Handlers ---
    def _on_scroll(self, *args):
        """Called when the user scrolls the treeview."""
        first, last = args
        if float(last) > 0.9 and not self.is_busy and not self.all_data_loaded:
            self.load_next_page()

    def refresh_treeview(self): self.start_new_load(query="")
    def search_products(self, event=None): self.start_new_load()
    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.on_entry_focus_out(None)
        self.start_new_load(query="")

    def on_entry_focus_in(self, event):
        if self.search_entry.get() == self.placeholder_text:
            self.search_entry.delete(0, "end")
            self.search_entry.config(foreground=self.default_fg_color)

    def on_entry_focus_out(self, event):
        if not self.search_entry.get():
            self.search_entry.insert(0, self.placeholder_text)
            self.search_entry.config(foreground=self.placeholder_color)

    # --- Import, Delete, Edit Methods (with state handling) ---
    def import_data(self):
        file_path = filedialog.askopenfilename(title="选择Excel文件", filetypes=(("Excel 文件", "*.xlsx"), ("所有文件", "*.*")))
        if not file_path: return
        self.set_busy(True)
        self.status_label.config(text=f"正在导入: {file_path.split('/')[-1]}...")
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
            summary_message = f"""导入完成！

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
            self.status_label.config(text=f"正在删除 {len(selected_items)} 件商品...")
            def db_task():
                sku_index = DISPLAY_COLUMNS.index('sku')
                for item in selected_items: database.delete_product(self.tree.item(item, 'values')[sku_index])
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