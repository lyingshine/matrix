import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
import database
from database import DB_COLUMNS

# Mapping from internal DB column names to user-facing headers
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

# User-defined display order
DISPLAY_COLUMNS = [
    'shop', 'product_id', 'spec_id', 'sku', 'price', 
    'quantity', 'spec_name', 'name'
]

class ProductEditorWindow(ttk.Toplevel):
    def __init__(self, parent, product=None):
        super().__init__(parent)
        self.parent = parent
        self.product = product

        if self.product:
            self.title("编辑商品")
        else:
            self.title("添加商品")

        self.geometry("400x450")
        self.transient(parent)
        self.grab_set()

        self.entries = {}
        for i, db_col in enumerate(DB_COLUMNS):
            header = HEADER_MAP[db_col]
            label = ttk.Label(self, text=f"{header}:")
            label.grid(row=i, column=0, padx=10, pady=10, sticky=tk.W)
            entry = ttk.Entry(self)
            entry.grid(row=i, column=1, padx=10, pady=10, sticky=tk.EW)
            self.entries[db_col] = entry

        self.grid_columnconfigure(1, weight=1)

        if self.product:
            for db_col in DB_COLUMNS:
                self.entries[db_col].insert(0, self.product.get(db_col, ''))
            self.entries['sku'].config(state='readonly')

        save_button = ttk.Button(self, text="保存", command=self.save, bootstyle=SUCCESS)
        save_button.grid(row=len(DB_COLUMNS), column=0, columnspan=2, pady=20)

    def save(self):
        try:
            product_data = {db_col: self.entries[db_col].get().strip() for db_col in DB_COLUMNS}

            if not product_data['sku'] or not product_data['name']:
                messagebox.showerror("错误", "规格编码和货品名称不能为空。", parent=self)
                return

            product_data['price'] = float(product_data['price'] or 0)
            product_data['quantity'] = int(product_data['quantity'] or 0)

            if self.product: # Edit mode
                database.update_product(product_data)
            else: # Add mode
                if database.get_product_by_sku(product_data['sku']):
                    messagebox.showerror("错误", f"规格编码 '{product_data['sku']}' 已存在。", parent=self)
                    return
                database.add_product(product_data)
            
            self.parent.refresh_treeview()
            self.destroy()

        except ValueError:
            messagebox.showerror("错误", "价格和平台库存必须是有效的数字。", parent=self)
        except Exception as e:
            messagebox.showerror("保存失败", f"发生错误: {e}", parent=self)

class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="litera") # Using a ttkbootstrap theme
        self.title("商品信息管理系统")
        self.geometry("1200x700")

        top_frame = ttk.Frame(self, padding=(10, 5))
        top_frame.pack(fill=X)

        self.import_button = ttk.Button(top_frame, text="导入表格", command=self.import_data, bootstyle=PRIMARY)
        self.import_button.pack(side=LEFT, padx=(0, 5))
        self.add_button = ttk.Button(top_frame, text="添加商品", command=self.open_add_window, bootstyle=SUCCESS)
        self.add_button.pack(side=LEFT, padx=5)
        self.edit_button = ttk.Button(top_frame, text="编辑商品", command=self.open_edit_window, bootstyle=INFO)
        self.edit_button.pack(side=LEFT, padx=5)
        self.delete_button = ttk.Button(top_frame, text="删除商品", command=self.delete_products, bootstyle=DANGER)
        self.delete_button.pack(side=LEFT, padx=5)

        self.generate_report_var = tk.BooleanVar()
        self.report_checkbutton = ttk.Checkbutton(
            top_frame, text="生成调试报告", variable=self.generate_report_var, bootstyle="round-toggle"
        )
        self.report_checkbutton.pack(side=LEFT, padx=15)

        self.clear_search_button = ttk.Button(top_frame, text="清空搜索", command=self.clear_search, bootstyle=SECONDARY)
        self.clear_search_button.pack(side=RIGHT, padx=(5, 0))
        self.search_button = ttk.Button(top_frame, text="搜索", command=self.search_products, bootstyle=PRIMARY)
        self.search_button.pack(side=RIGHT, padx=(5, 0))
        self.search_entry = ttk.Entry(top_frame)
        self.search_entry.bind("<Return>", self.search_products)
        self.search_entry.pack(side=RIGHT, fill=X, expand=True, padx=(10, 0))
        self.search_label = ttk.Label(top_frame, text="搜索:")
        self.search_label.pack(side=RIGHT)

        tree_frame = ttk.Frame(self, padding=(10, 5))
        tree_frame.pack(expand=True, fill=BOTH)

        self.tree = ttk.Treeview(tree_frame, columns=DISPLAY_COLUMNS, show="headings", bootstyle=SECONDARY)

        for col in DISPLAY_COLUMNS:
            header = HEADER_MAP.get(col, col)
            self.tree.heading(col, text=header)
            self.tree.column(col, anchor=CENTER)

        scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=LEFT, expand=True, fill=BOTH)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.refresh_treeview()

    def _update_treeview(self, products):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for product_row in products:
            reordered_values = [product_row[col] for col in DISPLAY_COLUMNS]
            self.tree.insert("", tk.END, values=tuple(reordered_values))

    def refresh_treeview(self):
        products = database.get_all_products()
        self._update_treeview(products)

    def import_data(self):
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=(("Excel 文件", "*.xlsx"), ("所有文件", "*.*"))
        )
        if not file_path:
            return

        if not file_path.endswith('.xlsx'):
            messagebox.showerror("错误", "此筛选功能仅支持Excel (.xlsx) 文件。")
            return

        try:
            sheet1_dtypes = { '规格ID': str, '规格编码': str }
            sheet2_dtypes = { '无效的规格ID': str }
            sheet3_dtypes = { '启用的规格编码': str }

            df = pd.read_excel(file_path, sheet_name='Sheet1', dtype=sheet1_dtypes)
            df_sheet2 = pd.read_excel(file_path, sheet_name='Sheet2', dtype=sheet2_dtypes)
            df_sheet3 = pd.read_excel(file_path, sheet_name='Sheet3', dtype=sheet3_dtypes)
            
            report_df = df.copy()
            total_rows = len(report_df)

            # Clean Spec ID (case-insensitive)
            invalid_id_col = '无效的规格ID'
            invalid_ids = set(df_sheet2[invalid_id_col].dropna().astype(str).str.strip().str.lower())
            report_df['_clean_spec_id'] = report_df['规格ID'].astype(str).str.strip().str.lower()

            # Clean SKU (case-sensitive)
            enabled_sku_col = '启用的规格编码'
            enabled_codes = set(df_sheet3[enabled_sku_col].dropna().astype(str).str.strip())
            report_df['_clean_sku'] = report_df['规格编码'].astype(str).str.strip()

            reasons = []
            for index, row in report_df.iterrows():
                reason = ''
                if row['_clean_spec_id'] in invalid_ids:
                    reason = '无效的规格ID'
                elif row['_clean_sku'] != '*' and row['_clean_sku'] not in enabled_codes:
                    reason = '规格编码未启用'
                reasons.append(reason)
            
            report_df['_filter_reason'] = reasons
            report_df['_is_imported'] = ['是' if not r else '否' for r in reasons]

            if self.generate_report_var.get():
                with pd.ExcelWriter('debug_report.xlsx') as writer:
                    report_df.to_excel(writer, sheet_name='Filter_Debug_Report', index=False)

            df_filtered = report_df[report_df['_is_imported'] == '是']

            user_header_to_db_col = {v: k for k, v in HEADER_MAP.items()}
            df_renamed = df_filtered.rename(columns=user_header_to_db_col)
            df_renamed = df_renamed.fillna('')

            products = [tuple(row) for row in df_renamed[DB_COLUMNS].itertuples(index=False)]
            
            if not products:
                messagebox.showinfo("完成", "没有符合筛选条件的商品可供导入。")
                return

            database.add_product_batch(products)
            self.refresh_treeview()
            
            filtered_count = total_rows - len(products)
            summary_message = (
                f"导入完成！\n\n"
                f"无效ID数量 (Sheet2): {len(invalid_ids)}\n"
                f"启用编码数量 (Sheet3): {len(enabled_codes)}\n\n"
                f"总行数 (Sheet1): {total_rows}\n"
                f"过滤掉: {filtered_count}\n"
                f"成功导入: {len(products)}"
            )
            if self.generate_report_var.get():
                summary_message += "\n\n已生成调试报告文件: debug_report.xlsx"
            
            messagebox.showinfo("成功", summary_message)

        except FileNotFoundError:
            messagebox.showerror("错误", f"找不到文件: {file_path}")
        except KeyError as e:
            messagebox.showerror("错误", f"Excel文件中缺少必要的Sheet或列: {e}")
        except Exception as e:
            messagebox.showerror("导入失败", f"处理Excel文件时发生未知错误: {e}")

    def search_products(self, event=None):
        query = self.search_entry.get()
        products = database.search_products(query) if query else database.get_all_products()
        self._update_treeview(products)

    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.refresh_treeview()

    def delete_products(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的商品。")
            return

        if messagebox.askyesno("确认删除", f"你确定要删除选中的 {len(selected_items)} 件商品吗？"):
            sku_index = DISPLAY_COLUMNS.index('sku')
            for item in selected_items:
                sku = self.tree.item(item, 'values')[sku_index]
                database.delete_product(sku)
            self.refresh_treeview()
            messagebox.showinfo("成功", f"成功删除了 {len(selected_items)} 件商品。")

    def open_add_window(self):
        ProductEditorWindow(self)

    def open_edit_window(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请选择一个要编辑的商品。")
            return
        if len(selected_items) > 1:
            messagebox.showwarning("警告", "一次只能编辑一个商品。")
            return
        
        item = selected_items[0]
        values = self.tree.item(item, 'values')
        product_data = dict(zip(DISPLAY_COLUMNS, values))
        ProductEditorWindow(self, product=product_data)

if __name__ == "__main__":
    database.init_db()
    app = App()
    app.mainloop()