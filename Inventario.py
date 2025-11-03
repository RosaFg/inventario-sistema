import os
import shutil
import time
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkinter import ttk

# ============== CONFIGURACIÓN ==============
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ARCHIVO_EXCEL = "Inventario2.0.xlsx"

HEADERS = [
    "Producto", "Categoría", "Proveedor",
    "Stock Inicial", "Entradas", "Salidas",
    "Stock Final", "Stock Mínimo", "Precio Unitario",
    "Valor Total", "Fecha de Movimiento",
    "Usuario Responsable", "Observaciones"
]

MOV_HEADERS = ["Fecha", "Producto", "Tipo", "Cantidad", "Usuario", 
               "Observaciones", "Stock Antes", "Stock Después"]

# Colores personalizados
COLORS = {
    "primary": "#595E5F",      # Rosa fuerte
    "secondary": "#595E5F",    # Rosa claro
    "accent": "#595E5F",       # Rosa medio
    "bg": "#FFF0F5",          # Fondo rosa muy claro
    "text": "#4D0033",        # Texto oscuro
    "hover": "#4F6B72",       # Hover rosa
    "success": "#4F6B72",     # Verde éxito
    "warning": "#4F6B72",     # Amarillo advertencia
    "danger": "#4F6B72"       # Rojo peligro
}

# ============== UTILIDADES ==============
def safe_int(x, default=0):
    try:
        if pd.isna(x):
            return default
        return int(float(str(x).replace(',', '.')))
    except Exception:
        return default

def safe_float(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(str(x).replace(',', '.'))
    except Exception:
        return default

def backup_file(path=ARCHIVO_EXCEL):
    if os.path.exists(path):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        bak = f"{os.path.splitext(path)[0]}_bak_{timestamp}.xlsx"
        try:
            shutil.copy2(path, bak)
            return True
        except Exception:
            return False
    return False

def list_backups():
    base = os.path.splitext(ARCHIVO_EXCEL)[0]
    files = [f for f in os.listdir('.') if f.startswith(base + "_bak_") and f.endswith('.xlsx')]
    files.sort(reverse=True)
    return files

def load_data():
    if os.path.exists(ARCHIVO_EXCEL):
        try:
            xls = pd.ExcelFile(ARCHIVO_EXCEL, engine="openpyxl")
            df_inv = pd.read_excel(xls, sheet_name='Inventario2.0', engine='openpyxl') if 'Inventario2.0' in xls.sheet_names else pd.DataFrame(columns=HEADERS)
            df_mov = pd.read_excel(xls, sheet_name='Movimientos', engine='openpyxl') if 'Movimientos' in xls.sheet_names else pd.DataFrame(columns=MOV_HEADERS)
        except Exception as e:
            messagebox.showerror("Error", f"Error al leer {ARCHIVO_EXCEL}: {e}")
            df_inv = pd.DataFrame(columns=HEADERS)
            df_mov = pd.DataFrame(columns=MOV_HEADERS)
    else:
        df_inv = pd.DataFrame(columns=HEADERS)
        df_mov = pd.DataFrame(columns=MOV_HEADERS)
        save_data(df_inv, df_mov)

    # Asegurar columnas
    for c in HEADERS:
        if c not in df_inv.columns:
            df_inv[c] = pd.NA
    for c in MOV_HEADERS:
        if c not in df_mov.columns:
            df_mov[c] = pd.NA

    # Normalizar tipos
    for col in ['Stock Inicial', 'Entradas', 'Salidas', 'Stock Final']:
        try:
            df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0).astype(int)
        except Exception:
            df_inv[col] = 0
    
    try:
        df_inv['Stock Mínimo'] = pd.to_numeric(df_inv['Stock Mínimo'], errors='coerce')
        df_inv['Precio Unitario'] = pd.to_numeric(df_inv['Precio Unitario'], errors='coerce').fillna(0.0).astype(float)
        df_inv['Valor Total'] = pd.to_numeric(df_inv['Valor Total'], errors='coerce').fillna(0.0).astype(float)
    except Exception:
        pass

    try:
        df_mov['Fecha'] = pd.to_datetime(df_mov['Fecha'], errors='coerce')
    except Exception:
        pass

    return df_inv, df_mov

def save_data(df_inv, df_mov, path=ARCHIVO_EXCEL):
    try:
        backup_file(path)
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            df_inv.to_excel(writer, sheet_name='Inventario2.0', index=False)
            df_mov.to_excel(writer, sheet_name='Movimientos', index=False)
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Error al guardar: {e}")
        return False

def find_product(df_inv, name, partial=True):
    name_norm = str(name).strip().lower()
    if name_norm == "":
        return []
    exact = df_inv[df_inv['Producto'].astype(str).str.strip().str.lower() == name_norm]
    if not exact.empty:
        return list(exact.index)
    if partial:
        matches = df_inv[df_inv['Producto'].astype(str).fillna('').str.strip().str.lower().str.contains(name_norm)]
        return list(matches.index)
    return []

def log_movement(df_mov, producto, tipo, cantidad, usuario, observaciones, stock_antes, stock_despues):
    fecha = pd.Timestamp.now()
    new = {
        'Fecha': fecha,
        'Producto': producto,
        'Tipo': tipo,
        'Cantidad': cantidad,
        'Usuario': usuario,
        'Observaciones': observaciones,
        'Stock Antes': stock_antes,
        'Stock Después': stock_despues
    }
    df_mov = pd.concat([df_mov, pd.DataFrame([new])], ignore_index=True)
    return df_mov

# ============== VENTANAS DE DIÁLOGO ==============
class AgregarProductoDialog(ctk.CTkToplevel):
    def __init__(self, parent, df_inv, df_mov, callback):
        super().__init__(parent)
        self.df_inv = df_inv
        self.df_mov = df_mov
        self.callback = callback
        self.result = None
        
        self.title("🌸 Agregar Producto")
        self.geometry("500x550")
        self.resizable(False, False)
        
        # Centrar ventana
        self.transient(parent)
        self.grab_set()
        
        self.configure(fg_color=COLORS["bg"])
        
        self.create_widgets()
        
    def create_widgets(self):
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title = ctk.CTkLabel(main_frame, text="Agregar Nuevo Producto", 
                            font=ctk.CTkFont(size=20, weight="bold"),
                            text_color=COLORS["primary"])
        title.pack(pady=(0, 20))
        
        # Campos
        self.entries = {}
        campos = [
            ("Producto *", ""),
            ("Categoría", ""),
            ("Proveedor", ""),
            ("Stock Inicial", "0"),
            ("Stock Mínimo", ""),
            ("Precio Unitario", "0.0"),
            ("Usuario Responsable", ""),
            ("Observaciones", "")
        ]
        
        for label_text, default in campos:
            frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            
            label = ctk.CTkLabel(frame, text=label_text, width=150, anchor="w")
            label.pack(side="left", padx=(0, 10))
            
            entry = ctk.CTkEntry(frame, placeholder_text=default)
            entry.pack(side="left", fill="x", expand=True)
            
            self.entries[label_text.replace(" *", "")] = entry
        
        # Botones
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        save_btn = ctk.CTkButton(btn_frame, text="💾 Guardar",
                                command=self.guardar,
                                fg_color=COLORS["primary"],
                                hover_color=COLORS["hover"],
                                width=150)
        save_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="✖ Cancelar",
                                  command=self.destroy,
                                  fg_color=COLORS["secondary"],
                                  hover_color=COLORS["hover"],
                                  width=150)
        cancel_btn.pack(side="left", padx=5)
    
    def guardar(self):
        producto = self.entries["Producto"].get().strip()
        if not producto:
            messagebox.showwarning("Atención", "El campo 'Producto' es obligatorio")
            return
        
        if find_product(self.df_inv, producto, partial=False):
            messagebox.showwarning("Error", "El producto ya existe")
            return
        
        try:
            categoria = self.entries["Categoría"].get().strip() or pd.NA
            proveedor = self.entries["Proveedor"].get().strip() or pd.NA
            stock_inicial = safe_int(self.entries["Stock Inicial"].get(), 0)
            
            stock_minimo_str = self.entries["Stock Mínimo"].get().strip()
            stock_minimo = int(stock_minimo_str) if stock_minimo_str else pd.NA
            
            precio_unitario = safe_float(self.entries["Precio Unitario"].get(), 0.0)
            usuario = self.entries["Usuario Responsable"].get().strip() or pd.NA
            observaciones = self.entries["Observaciones"].get().strip() or pd.NA
            
            self.df_inv.loc[len(self.df_inv)] = [
                producto, categoria, proveedor,
                stock_inicial, 0, 0, stock_inicial,
                stock_minimo, precio_unitario,
                stock_inicial * precio_unitario,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                usuario, observaciones
            ]
            
            save_data(self.df_inv, self.df_mov)
            self.callback()
            messagebox.showinfo("Éxito", f"🌟 Producto '{producto}' agregado correctamente")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el producto:\n{e}")

class EditarProductoDialog(ctk.CTkToplevel):
    def __init__(self, parent, df_inv, df_mov, idx, callback):
        super().__init__(parent)
        self.df_inv = df_inv
        self.df_mov = df_mov
        self.idx = idx
        self.callback = callback
        
        prod = df_inv.loc[idx]
        self.title(f"✏️ Editar: {prod['Producto']}")
        self.geometry("500x500")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLORS["bg"])
        
        self.create_widgets(prod)
    
    def create_widgets(self, prod):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(main_frame, text=f"Editar: {prod['Producto']}", 
                            font=ctk.CTkFont(size=18, weight="bold"),
                            text_color=COLORS["primary"])
        title.pack(pady=(0, 20))
        
        self.entries = {}
        campos = [
            ("Categoría", prod.get("Categoría", "")),
            ("Proveedor", prod.get("Proveedor", "")),
            ("Precio Unitario", str(prod.get("Precio Unitario", ""))),
            ("Stock Mínimo", str(prod.get("Stock Mínimo", "") if pd.notna(prod.get("Stock Mínimo")) else "")),
            ("Usuario Responsable", prod.get("Usuario Responsable", "")),
            ("Observaciones", prod.get("Observaciones", ""))
        ]
        
        for label_text, value in campos:
            frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            
            label = ctk.CTkLabel(frame, text=label_text, width=150, anchor="w")
            label.pack(side="left", padx=(0, 10))
            
            entry = ctk.CTkEntry(frame)
            entry.insert(0, "" if pd.isna(value) else str(value))
            entry.pack(side="left", fill="x", expand=True)
            
            self.entries[label_text] = entry
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        save_btn = ctk.CTkButton(btn_frame, text="💾 Guardar",
                                command=self.guardar,
                                fg_color=COLORS["primary"],
                                hover_color=COLORS["hover"],
                                width=150)
        save_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="✖ Cancelar",
                                  command=self.destroy,
                                  fg_color=COLORS["secondary"],
                                  hover_color=COLORS["hover"],
                                  width=150)
        cancel_btn.pack(side="left", padx=5)
    
    def guardar(self):
        try:
            categoria = self.entries["Categoría"].get().strip() or pd.NA
            proveedor = self.entries["Proveedor"].get().strip() or pd.NA
            usuario = self.entries["Usuario Responsable"].get().strip() or pd.NA
            observaciones = self.entries["Observaciones"].get().strip() or pd.NA
            
            if self.entries["Precio Unitario"].get().strip():
                nuevo_precio = safe_float(self.entries["Precio Unitario"].get())
                self.df_inv.at[self.idx, "Precio Unitario"] = nuevo_precio
                self.df_inv.at[self.idx, "Valor Total"] = self.df_inv.at[self.idx, "Stock Final"] * nuevo_precio
            
            if self.entries["Stock Mínimo"].get().strip():
                self.df_inv.at[self.idx, "Stock Mínimo"] = int(self.entries["Stock Mínimo"].get())
            else:
                self.df_inv.at[self.idx, "Stock Mínimo"] = pd.NA
            
            self.df_inv.at[self.idx, "Categoría"] = categoria
            self.df_inv.at[self.idx, "Proveedor"] = proveedor
            self.df_inv.at[self.idx, "Usuario Responsable"] = usuario
            self.df_inv.at[self.idx, "Observaciones"] = observaciones
            self.df_inv.at[self.idx, "Fecha de Movimiento"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            save_data(self.df_inv, self.df_mov)
            self.callback()
            messagebox.showinfo("Éxito", "📝 Producto actualizado correctamente")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar:\n{e}")

class MovimientoDialog(ctk.CTkToplevel):
    def __init__(self, parent, df_inv, df_mov, idx, callback):
        super().__init__(parent)
        self.df_inv = df_inv
        self.df_mov = df_mov
        self.idx = idx
        self.callback = callback
        
        prod = df_inv.loc[idx]
        self.title(f"📦 Movimiento: {prod['Producto']}")
        self.geometry("450x400")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLORS["bg"])
        
        self.create_widgets(prod)
    
    def create_widgets(self, prod):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(main_frame, text=f"Movimiento de Stock", 
                            font=ctk.CTkFont(size=18, weight="bold"),
                            text_color=COLORS["primary"])
        title.pack(pady=(0, 10))
        
        subtitle = ctk.CTkLabel(main_frame, text=f"Producto: {prod['Producto']}", 
                               font=ctk.CTkFont(size=14))
        subtitle.pack(pady=(0, 20))
        
        # Tipo de movimiento
        tipo_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tipo_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(tipo_frame, text="Tipo:", width=100, anchor="w").pack(side="left")
        self.tipo_var = ctk.StringVar(value="Entrada")
        tipo_menu = ctk.CTkOptionMenu(tipo_frame, variable=self.tipo_var,
                                     values=["Entrada", "Salida"],
                                     fg_color=COLORS["primary"],
                                     button_color=COLORS["accent"],
                                     button_hover_color=COLORS["hover"])
        tipo_menu.pack(side="left", fill="x", expand=True)
        
        # Cantidad
        cant_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        cant_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(cant_frame, text="Cantidad:", width=100, anchor="w").pack(side="left")
        self.cantidad_entry = ctk.CTkEntry(cant_frame, placeholder_text="0")
        self.cantidad_entry.pack(side="left", fill="x", expand=True)
        
        # Usuario
        user_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        user_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(user_frame, text="Usuario:", width=100, anchor="w").pack(side="left")
        self.usuario_entry = ctk.CTkEntry(user_frame)
        self.usuario_entry.pack(side="left", fill="x", expand=True)
        
        # Observaciones
        obs_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        obs_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(obs_frame, text="Observaciones:", width=100, anchor="w").pack(side="left")
        self.obs_entry = ctk.CTkEntry(obs_frame)
        self.obs_entry.pack(side="left", fill="x", expand=True)
        
        # Botones
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        save_btn = ctk.CTkButton(btn_frame, text="💾 Guardar",
                                command=self.guardar,
                                fg_color=COLORS["primary"],
                                hover_color=COLORS["hover"],
                                width=150)
        save_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="✖ Cancelar",
                                  command=self.destroy,
                                  fg_color=COLORS["secondary"],
                                  hover_color=COLORS["hover"],
                                  width=150)
        cancel_btn.pack(side="left", padx=5)
    
    def guardar(self):
        try:
            tipo = self.tipo_var.get()
            cantidad = safe_int(self.cantidad_entry.get(), 0)
            
            if cantidad <= 0:
                messagebox.showwarning("Atención", "La cantidad debe ser mayor a 0")
                return
            
            usuario = self.usuario_entry.get().strip() or pd.NA
            obs = self.obs_entry.get().strip() or pd.NA
            
            stock_antes = safe_int(self.df_inv.loc[self.idx, 'Stock Final'])
            
            if tipo == "Entrada":
                self.df_inv.loc[self.idx, 'Entradas'] += cantidad
                self.df_inv.loc[self.idx, 'Stock Final'] += cantidad
            else:  # Salida
                if stock_antes < cantidad:
                    messagebox.showwarning("Error", "Stock insuficiente")
                    return
                self.df_inv.loc[self.idx, 'Salidas'] += cantidad
                self.df_inv.loc[self.idx, 'Stock Final'] -= cantidad
            
            self.df_inv.loc[self.idx, 'Valor Total'] = (
                self.df_inv.loc[self.idx, 'Stock Final'] * 
                safe_float(self.df_inv.loc[self.idx, 'Precio Unitario'])
            )
            self.df_inv.loc[self.idx, 'Fecha de Movimiento'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.df_mov = log_movement(
                self.df_mov,
                self.df_inv.loc[self.idx, 'Producto'],
                tipo, cantidad, usuario, obs,
                stock_antes,
                self.df_inv.loc[self.idx, 'Stock Final']
            )
            
            save_data(self.df_inv, self.df_mov)
            self.callback()
            messagebox.showinfo("Éxito", f"✅ {tipo} registrada correctamente")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar el movimiento:\n{e}")

# ============== APLICACIÓN PRINCIPAL ==============
class InventarioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Tu Inventario 💗")
        self.geometry("1400x800")
        self.minsize(1000, 600)
        
        self.df_inv, self.df_mov = load_data()
        
        self.configure(fg_color=COLORS["bg"])
        
        self.create_widgets()
        self.refresh_all()
        
    def create_widgets(self):
        # Título principal
        header = ctk.CTkFrame(self, height=80, fg_color=COLORS["primary"])
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        title_label = ctk.CTkLabel(header, 
                                   text="Tu Inventario 💗",
                                   font=ctk.CTkFont(size=28, weight="bold"),
                                   text_color="white")
        title_label.pack(expand=True)
        
        # Tabview
        self.tabview = ctk.CTkTabview(self, fg_color="white", 
                                      segmented_button_fg_color=COLORS["secondary"],
                                      segmented_button_selected_color=COLORS["primary"])
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Crear pestañas
        self.tab_gestion = self.tabview.add("📦 Gestión")
        self.tab_movimientos = self.tabview.add("📋 Movimientos")
        self.tab_analisis = self.tabview.add("📊 Análisis")
        self.tab_config = self.tabview.add("⚙️ Configuración")
        
        self.setup_tab_gestion()
        self.setup_tab_movimientos()
        self.setup_tab_analisis()
        self.setup_tab_config()
        
    def setup_tab_gestion(self):
        # Frame superior con búsqueda
        top_frame = ctk.CTkFrame(self.tab_gestion, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *args: self.filtrar_inventario())
        
        search_label = ctk.CTkLabel(top_frame, text="🔍 Buscar:", 
                                   font=ctk.CTkFont(size=14, weight="bold"))
        search_label.pack(side="left", padx=(0, 10))
        
        search_entry = ctk.CTkEntry(top_frame, textvariable=self.search_var,
                                   placeholder_text="Buscar producto, categoría o proveedor...",
                                   width=400)
        search_entry.pack(side="left", padx=5)
        
        clear_btn = ctk.CTkButton(top_frame, text="🔄 Limpiar",
                                 command=lambda: self.search_var.set(""),
                                 fg_color=COLORS["secondary"],
                                 hover_color=COLORS["hover"],
                                 width=100)
        clear_btn.pack(side="left", padx=5)
        
        # Frame contenedor
        content_frame = ctk.CTkFrame(self.tab_gestion, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tabla
        table_frame = ctk.CTkFrame(content_frame)
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.create_treeview(table_frame)
        
        # Panel de botones
        btn_panel = ctk.CTkFrame(content_frame, width=200)
        btn_panel.pack(side="right", fill="y")
        btn_panel.pack_propagate(False)
        
        buttons = [
            ("➕ Agregar Producto", self.agregar_producto, COLORS["success"]),
            ("✏️ Editar Producto", self.editar_producto, COLORS["primary"]),
            ("📦 Movimiento", self.movimiento_stock, COLORS["accent"]),
            ("🗑️ Eliminar Producto", self.eliminar_producto, COLORS["danger"]),
            ("⚠️ Alertas Stock", self.alertas_stock, COLORS["warning"]),
            ("💾 Guardar", self.guardar_datos, COLORS["primary"]),
        ]
        
        for text, command, color in buttons:
            btn = ctk.CTkButton(btn_panel, text=text, command=command,
                              fg_color=color, hover_color=COLORS["hover"],
                              height=40, font=ctk.CTkFont(size=13, weight="bold"))
            btn.pack(pady=8, padx=10, fill="x")
    
    def create_treeview(self, parent):
        # Crear frame para treeview con scrollbar
        tree_container = ctk.CTkFrame(parent)
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                       background="white",
                       foreground="black",
                       rowheight=30,
                       fieldbackground="white",
                       font=('Helvetica', 10))
        style.map('Treeview', background=[('selected', COLORS["secondary"])])
        style.configure("Treeview.Heading",
                       font=('Helvetica', 11, 'bold'),
                       background=COLORS["primary"],
                       foreground="white")
        
        cols = ['Producto', 'Categoría', 'Proveedor', 'Stock Final', 
                'Stock Mínimo', 'Precio Unitario', 'Valor Total']
        
        self.tree_inv = ttk.Treeview(tree_container, columns=cols, show='headings', height=20)
        
        # Configurar columnas
        col_widths = {
            'Producto': 180,
            'Categoría': 120,
            'Proveedor': 120,
            'Stock Final': 100,
            'Stock Mínimo': 100,
            'Precio Unitario': 120,
            'Valor Total': 120
        }
        
        for col in cols:
            self.tree_inv.heading(col, text=col)
            self.tree_inv.column(col, width=col_widths.get(col, 100), anchor="center")
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_inv.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree_inv.xview)
        self.tree_inv.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree_inv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Doble click para ver detalle
        self.tree_inv.bind("<Double-1>", self.ver_detalle_producto)
    
    def setup_tab_movimientos(self):
        # Frame superior
        top_frame = ctk.CTkFrame(self.tab_movimientos, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        title = ctk.CTkLabel(top_frame, text="📋 Historial de Movimientos",
                            font=ctk.CTkFont(size=16, weight="bold"),
                            text_color=COLORS["primary"])
        title.pack(side="left", padx=10)
        
        # Búsqueda
        self.search_mov_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(top_frame, textvariable=self.search_mov_var,
                                   placeholder_text="Buscar en movimientos...",
                                   width=300)
        search_entry.pack(side="left", padx=10)
        
        search_btn = ctk.CTkButton(top_frame, text="🔍 Buscar",
                                  command=self.buscar_movimientos,
                                  fg_color=COLORS["primary"],
                                  width=100)
        search_btn.pack(side="left", padx=5)
        
        clear_btn = ctk.CTkButton(top_frame, text="🔄 Limpiar",
                                 command=self.limpiar_busqueda_mov,
                                 fg_color=COLORS["secondary"],
                                 width=100)
        clear_btn.pack(side="left", padx=5)
        
        # Contenedor
        content_frame = ctk.CTkFrame(self.tab_movimientos, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tabla de movimientos
        table_frame = ctk.CTkFrame(content_frame)
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.create_treeview_movimientos(table_frame)
        
        # Panel de botones
        btn_panel = ctk.CTkFrame(content_frame, width=180)
        btn_panel.pack(side="right", fill="y")
        btn_panel.pack_propagate(False)
        
        export_btn = ctk.CTkButton(btn_panel, text="📤 Exportar CSV",
                                  command=self.exportar_movimientos,
                                  fg_color=COLORS["primary"],
                                  height=40)
        export_btn.pack(pady=10, padx=10, fill="x")
        
        refresh_btn = ctk.CTkButton(btn_panel, text="🔄 Actualizar",
                                   command=self.refresh_movimientos,
                                   fg_color=COLORS["secondary"],
                                   height=40)
        refresh_btn.pack(pady=10, padx=10, fill="x")
    
    def create_treeview_movimientos(self, parent):
        tree_container = ctk.CTkFrame(parent)
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        cols = ['Fecha', 'Producto', 'Tipo', 'Cantidad', 'Usuario', 
                'Observaciones', 'Stock Antes', 'Stock Después']
        
        self.tree_mov = ttk.Treeview(tree_container, columns=cols, show='headings', height=20)
        
        col_widths = {
            'Fecha': 150,
            'Producto': 180,
            'Tipo': 80,
            'Cantidad': 80,
            'Usuario': 120,
            'Observaciones': 180,
            'Stock Antes': 100,
            'Stock Después': 100
        }
        
        for col in cols:
            self.tree_mov.heading(col, text=col)
            self.tree_mov.column(col, width=col_widths.get(col, 100), anchor="center")
        
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_mov.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree_mov.xview)
        self.tree_mov.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree_mov.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
    
    def setup_tab_analisis(self):
        # Frame superior
        top_frame = ctk.CTkFrame(self.tab_analisis, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        title = ctk.CTkLabel(top_frame, text="📊 Análisis y Gráficos",
                            font=ctk.CTkFont(size=16, weight="bold"),
                            text_color=COLORS["primary"])
        title.pack(side="left", padx=10)
        
        # Contenedor principal
        content_frame = ctk.CTkFrame(self.tab_analisis, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Panel de control
        control_panel = ctk.CTkFrame(content_frame, width=250)
        control_panel.pack(side="left", fill="y", padx=(0, 10))
        control_panel.pack_propagate(False)
        
        # Botones de gráficos
        btn_stock = ctk.CTkButton(control_panel, text="📊 Gráfico de Stock",
                                 command=self.grafico_stock,
                                 fg_color=COLORS["primary"],
                                 height=40)
        btn_stock.pack(pady=10, padx=10, fill="x")
        
        btn_valor = ctk.CTkButton(control_panel, text="💰 Valor Total",
                                 command=self.grafico_valor,
                                 fg_color=COLORS["accent"],
                                 height=40)
        btn_valor.pack(pady=10, padx=10, fill="x")
        
        btn_categoria = ctk.CTkButton(control_panel, text="🏷️ Por Categoría",
                                      command=self.grafico_categoria,
                                      fg_color=COLORS["secondary"],
                                      height=40)
        btn_categoria.pack(pady=10, padx=10, fill="x")
        
        btn_bajo = ctk.CTkButton(control_panel, text="⚠️ Stock Bajo",
                                command=self.grafico_stock_bajo,
                                fg_color=COLORS["warning"],
                                height=40)
        btn_bajo.pack(pady=10, padx=10, fill="x")
        
        # Frame para gráficos
        self.graph_frame = ctk.CTkFrame(content_frame)
        self.graph_frame.pack(side="right", fill="both", expand=True)
        
        # Mensaje inicial
        welcome_label = ctk.CTkLabel(self.graph_frame, 
                                     text="Seleccione un tipo de gráfico",
                                     font=ctk.CTkFont(size=20),
                                     text_color=COLORS["primary"])
        welcome_label.place(relx=0.5, rely=0.5, anchor="center")
    
    def setup_tab_config(self):
        # Frame principal
        main_frame = ctk.CTkFrame(self.tab_config, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title = ctk.CTkLabel(main_frame, text="⚙️ Configuración y Backups",
                            font=ctk.CTkFont(size=20, weight="bold"),
                            text_color=COLORS["primary"])
        title.pack(pady=(0, 20))
        
        # Info del archivo
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=10)
        
        file_label = ctk.CTkLabel(info_frame, text=f"📁 Archivo: {os.path.abspath(ARCHIVO_EXCEL)}",
                                 font=ctk.CTkFont(size=12))
        file_label.pack(pady=10, padx=10)
        
        # Botones de acción
        action_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        action_frame.pack(fill="x", pady=20)
        
        save_btn = ctk.CTkButton(action_frame, text="💾 Guardar Datos",
                                command=lambda: self.guardar_datos(show_msg=True),
                                fg_color=COLORS["success"],
                                height=50,
                                font=ctk.CTkFont(size=14, weight="bold"))
        save_btn.pack(side="left", padx=10, fill="x", expand=True)
        
        backup_btn = ctk.CTkButton(action_frame, text="📦 Crear Backup Manual",
                                  command=self.crear_backup_manual,
                                  fg_color=COLORS["primary"],
                                  height=50,
                                  font=ctk.CTkFont(size=14, weight="bold"))
        backup_btn.pack(side="left", padx=10, fill="x", expand=True)
        
        folder_btn = ctk.CTkButton(action_frame, text="📂 Abrir Carpeta",
                                  command=self.abrir_carpeta,
                                  fg_color=COLORS["secondary"],
                                  height=50,
                                  font=ctk.CTkFont(size=14, weight="bold"))
        folder_btn.pack(side="left", padx=10, fill="x", expand=True)
        
        # Lista de backups
        backup_label = ctk.CTkLabel(main_frame, text="Backups Disponibles:",
                                   font=ctk.CTkFont(size=14, weight="bold"))
        backup_label.pack(anchor="w", pady=(20, 10))
        
        # Frame para lista y botones
        backup_container = ctk.CTkFrame(main_frame)
        backup_container.pack(fill="both", expand=True)
        
        # Scrollable frame para backups
        self.backup_list = ctk.CTkScrollableFrame(backup_container, height=300)
        self.backup_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Botón eliminar
        delete_btn = ctk.CTkButton(backup_container, text="🗑️ Eliminar Backup Seleccionado",
                                  command=self.eliminar_backup_seleccionado,
                                  fg_color=COLORS["danger"],
                                  height=40)
        delete_btn.pack(pady=10, padx=10, fill="x")
        
        self.backup_vars = []
        self.refresh_backups()
    
    # ============== MÉTODOS DE GESTIÓN ==============
    def get_selected_index(self):
        sel = self.tree_inv.selection()
        if not sel:
            return None
        try:
            iid = sel[0]
            return int(iid)
        except:
            return None
    
    def agregar_producto(self):
        AgregarProductoDialog(self, self.df_inv, self.df_mov, self.refresh_all)
    
    def editar_producto(self):
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showwarning("Atención", "Seleccione un producto de la tabla")
            return
        EditarProductoDialog(self, self.df_inv, self.df_mov, idx, self.refresh_all)
    
    def movimiento_stock(self):
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showwarning("Atención", "Seleccione un producto de la tabla")
            return
        MovimientoDialog(self, self.df_inv, self.df_mov, idx, self.refresh_all)
    
    def eliminar_producto(self):
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showwarning("Atención", "Seleccione un producto de la tabla")
            return
        
        prod_name = self.df_inv.at[idx, 'Producto']
        if messagebox.askyesno("Confirmar", f"¿Eliminar '{prod_name}'?"):
            self.df_inv.drop(index=idx, inplace=True)
            self.df_inv.reset_index(drop=True, inplace=True)
            save_data(self.df_inv, self.df_mov)
            self.refresh_all()
            messagebox.showinfo("Eliminado", "🗑️ Producto eliminado correctamente")
    
    def alertas_stock(self):
        if 'Stock Mínimo' not in self.df_inv.columns:
            messagebox.showinfo("Alertas", "No hay productos con stock mínimo definido")
            return
        
        df = self.df_inv.copy()
        df['Stock Mínimo'] = pd.to_numeric(df['Stock Mínimo'], errors='coerce')
        df['Stock Final'] = pd.to_numeric(df['Stock Final'], errors='coerce').fillna(0)
        df_mins = df[df['Stock Mínimo'].notna()]
        
        if df_mins.empty:
            messagebox.showinfo("Alertas", "No hay productos con stock mínimo definido")
            return
        
        bajos = df_mins[df_mins['Stock Final'] <= df_mins['Stock Mínimo']]
        
        if bajos.empty:
            messagebox.showinfo("Alertas", "✨ Todos los productos tienen stock suficiente")
            return
        
        # Crear ventana de alertas
        alert_win = ctk.CTkToplevel(self)
        alert_win.title("⚠️ Alertas de Stock Bajo")
        alert_win.geometry("600x400")
        alert_win.configure(fg_color=COLORS["bg"])
        
        title = ctk.CTkLabel(alert_win, text="⚠️ Productos con Stock Bajo",
                            font=ctk.CTkFont(size=18, weight="bold"),
                            text_color=COLORS["danger"])
        title.pack(pady=20)
        
        scroll_frame = ctk.CTkScrollableFrame(alert_win)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        for _, row in bajos.iterrows():
            alert_frame = ctk.CTkFrame(scroll_frame, fg_color=COLORS["warning"])
            alert_frame.pack(fill="x", pady=5, padx=5)
            
            text = f"🌸 {row['Producto']}: Stock: {int(row['Stock Final'])} | Mínimo: {int(row['Stock Mínimo'])}"
            label = ctk.CTkLabel(alert_frame, text=text, font=ctk.CTkFont(size=12))
            label.pack(pady=10, padx=10)
        
        close_btn = ctk.CTkButton(alert_win, text="Cerrar",
                                 command=alert_win.destroy,
                                 fg_color=COLORS["primary"])
        close_btn.pack(pady=10)
    
    def ver_detalle_producto(self, event):
        idx = self.get_selected_index()
        if idx is None:
            return
        
        prod = self.df_inv.loc[idx]
        
        # Ventana de detalle
        detail_win = ctk.CTkToplevel(self)
        detail_win.title(f"📋 Detalle: {prod['Producto']}")
        detail_win.geometry("500x600")
        detail_win.configure(fg_color=COLORS["bg"])
        
        title = ctk.CTkLabel(detail_win, text=f"📋 {prod['Producto']}",
                            font=ctk.CTkFont(size=20, weight="bold"),
                            text_color=COLORS["primary"])
        title.pack(pady=20)
        
        # Frame scrollable para detalles
        detail_frame = ctk.CTkScrollableFrame(detail_win)
        detail_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        for col in HEADERS:
            if col in prod.index:
                value = prod[col]
                if pd.notna(value):
                    info_frame = ctk.CTkFrame(detail_frame, fg_color="white")
                    info_frame.pack(fill="x", pady=5)
                    
                    label = ctk.CTkLabel(info_frame, text=f"{col}:",
                                        font=ctk.CTkFont(weight="bold"),
                                        anchor="w", width=200)
                    label.pack(side="left", padx=10, pady=10)
                    
                    value_label = ctk.CTkLabel(info_frame, text=str(value),
                                              anchor="w")
                    value_label.pack(side="left", padx=10, pady=10)
        
        close_btn = ctk.CTkButton(detail_win, text="Cerrar",
                                 command=detail_win.destroy,
                                 fg_color=COLORS["primary"])
        close_btn.pack(pady=10)
    
    # ============== MÉTODOS DE ACTUALIZACIÓN ==============
    def refresh_all(self):
        self.df_inv, self.df_mov = load_data()
        self.refresh_inventario()
        self.refresh_movimientos()
    
    def refresh_inventario(self):
        self.tree_inv.delete(*self.tree_inv.get_children())
        self.filtrar_inventario()
    
    def format_number(self, value):
        """Formatea números: sin decimales si es entero, con decimales si no"""
        try:
            num = float(value)
            if num == int(num):  # Es un número entero
                return f"{int(num):,}".replace(",", ".")
            else:  # Tiene decimales
                return f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return str(value)
    
    def filtrar_inventario(self):
        query = self.search_var.get().strip().lower()
        self.tree_inv.delete(*self.tree_inv.get_children())
        
        for idx, row in self.df_inv.iterrows():
            prod = str(row.get('Producto', '')).lower()
            cat = str(row.get('Categoría', '')).lower()
            prov = str(row.get('Proveedor', '')).lower()
            
            if query == "" or query in prod or query in cat or query in prov:
                precio = row.get('Precio Unitario', 0)
                valor_total = row.get('Valor Total', 0)
                
                values = [
                    row.get('Producto', ''),
                    row.get('Categoría', ''),
                    row.get('Proveedor', ''),
                    int(row.get('Stock Final', 0)) if pd.notna(row.get('Stock Final')) else 0,
                    int(row.get('Stock Mínimo', 0)) if pd.notna(row.get('Stock Mínimo')) else '',
                    self.format_number(precio),
                    self.format_number(valor_total)
                ]
                self.tree_inv.insert("", "end", iid=str(idx), values=values)
    
    def refresh_movimientos(self):
        self.tree_mov.delete(*self.tree_mov.get_children())
        
        dfm = self.df_mov.copy()
        try:
            dfm = dfm.sort_values('Fecha', ascending=False)
        except:
            pass
        
        for _, row in dfm.iterrows():
            fecha = row.get('Fecha', '')
            if pd.notna(fecha):
                try:
                    fecha = pd.to_datetime(fecha).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            values = [
                fecha,
                row.get('Producto', ''),
                row.get('Tipo', ''),
                row.get('Cantidad', ''),
                row.get('Usuario', ''),
                row.get('Observaciones', ''),
                row.get('Stock Antes', ''),
                row.get('Stock Después', '')
            ]
            self.tree_mov.insert("", "end", values=values)
    
    def buscar_movimientos(self):
        query = self.search_mov_var.get().strip().lower()
        self.tree_mov.delete(*self.tree_mov.get_children())
        
        for _, row in self.df_mov.iterrows():
            vals = [str(v).lower() for v in row.values]
            if any(query in v for v in vals):
                fecha = row.get('Fecha', '')
                if pd.notna(fecha):
                    try:
                        fecha = pd.to_datetime(fecha).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                
                values = [
                    fecha,
                    row.get('Producto', ''),
                    row.get('Tipo', ''),
                    row.get('Cantidad', ''),
                    row.get('Usuario', ''),
                    row.get('Observaciones', ''),
                    row.get('Stock Antes', ''),
                    row.get('Stock Después', '')
                ]
                self.tree_mov.insert("", "end", values=values)
    
    def limpiar_busqueda_mov(self):
        self.search_mov_var.set("")
        self.refresh_movimientos()
    
    def exportar_movimientos(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            try:
                self.df_mov.to_csv(path, index=False, encoding='utf-8-sig')
                messagebox.showinfo("Éxito", f"📤 Movimientos exportados a:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar:\n{e}")
    
    # ============== MÉTODOS DE GRÁFICOS ==============
    def clear_graph_frame(self):
        for widget in self.graph_frame.winfo_children():
            widget.destroy()
    
    def grafico_stock(self):
        self.clear_graph_frame()
        
        df_plot = self.df_inv[self.df_inv['Producto'].astype(str).str.strip() != ''].copy()
        if df_plot.empty:
            messagebox.showinfo("Gráfico", "No hay productos para graficar")
            return
        
        df_plot = df_plot.sort_values('Stock Final', ascending=False).head(20)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(range(len(df_plot)), df_plot['Stock Final'], 
                     color=COLORS["primary"], alpha=0.7)
        ax.set_xlabel("Producto", fontsize=12, fontweight='bold')
        ax.set_ylabel("Stock Final", fontsize=12, fontweight='bold')
        ax.set_title("📊 Stock por Producto (Top 20)", fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(df_plot)))
        ax.set_xticklabels(df_plot['Producto'], rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def grafico_valor(self):
        self.clear_graph_frame()
        
        df_plot = self.df_inv[self.df_inv['Valor Total'] > 0].copy()
        if df_plot.empty:
            messagebox.showinfo("Gráfico", "No hay datos de valor total")
            return
        
        df_plot = df_plot.sort_values('Valor Total', ascending=False).head(20)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(range(len(df_plot)), df_plot['Valor Total'],
                      color=COLORS["accent"], alpha=0.7)
        ax.set_yticks(range(len(df_plot)))
        ax.set_yticklabels(df_plot['Producto'])
        ax.set_xlabel("Valor Total ($)", fontsize=12, fontweight='bold')
        ax.set_title("💰 Valor Total por Producto (Top 20)", fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def grafico_categoria(self):
        self.clear_graph_frame()
        
        df_cat = self.df_inv.groupby('Categoría')['Stock Final'].sum()
        
        if df_cat.empty:
            messagebox.showinfo("Gráfico", "No hay categorías para graficar")
            return
        
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = ['#FF1493', '#FFB6D5', '#FF69B4', '#FF85C1', '#FFC0CB']
        ax.pie(df_cat.values, labels=df_cat.index, autopct='%1.1f%%',
              colors=colors, startangle=90)
        ax.set_title("🏷️ Stock por Categoría", fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def grafico_stock_bajo(self):
        self.clear_graph_frame()
        
        df = self.df_inv.copy()
        df['Stock Mínimo'] = pd.to_numeric(df['Stock Mínimo'], errors='coerce')
        df['Stock Final'] = pd.to_numeric(df['Stock Final'], errors='coerce').fillna(0)
        df_mins = df[df['Stock Mínimo'].notna()]
        bajos = df_mins[df_mins['Stock Final'] <= df_mins['Stock Mínimo']]
        
        if bajos.empty:
            messagebox.showinfo("Gráfico", "✨ No hay productos con stock bajo")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        x = range(len(bajos))
        width = 0.35
        
        ax.bar([i - width/2 for i in x], bajos['Stock Final'], width,
              label='Stock Actual', color=COLORS["danger"], alpha=0.7)
        ax.bar([i + width/2 for i in x], bajos['Stock Mínimo'], width,
              label='Stock Mínimo', color=COLORS["warning"], alpha=0.7)
        
        ax.set_xlabel("Producto", fontsize=12, fontweight='bold')
        ax.set_ylabel("Cantidad", fontsize=12, fontweight='bold')
        ax.set_title("⚠️ Productos con Stock Bajo", fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(bajos['Producto'], rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    
    # ============== MÉTODOS DE CONFIGURACIÓN ==============
    def guardar_datos(self, show_msg=False):
        if save_data(self.df_inv, self.df_mov):
            if show_msg:
                messagebox.showinfo("Éxito", "✅ Datos guardados correctamente")
            self.refresh_backups()
    
    def crear_backup_manual(self):
        if backup_file():
            messagebox.showinfo("Backup", "📦 Backup creado correctamente")
            self.refresh_backups()
        else:
            messagebox.showerror("Error", "No se pudo crear el backup")
    
    def abrir_carpeta(self):
        folder = os.path.abspath('.')
        try:
            if os.name == 'nt':
                os.startfile(folder)
            elif os.name == 'posix':
                import subprocess
                subprocess.Popen(['xdg-open', folder])
        except:
            messagebox.showinfo("Carpeta", f"Ruta: {folder}")
    
    def refresh_backups(self):
        for widget in self.backup_list.winfo_children():
            widget.destroy()
        
        self.backup_vars = []
        backups = list_backups()
        
        if not backups:
            label = ctk.CTkLabel(self.backup_list, text="No hay backups disponibles",
                                font=ctk.CTkFont(size=12))
            label.pack(pady=20)
        else:
            for backup in backups:
                var = ctk.StringVar(value="")
                frame = ctk.CTkFrame(self.backup_list, fg_color="white")
                frame.pack(fill="x", pady=3, padx=5)
                
                checkbox = ctk.CTkCheckBox(frame, text=backup, variable=var,
                                          onvalue=backup, offvalue="")
                checkbox.pack(side="left", padx=10, pady=8)
                
                self.backup_vars.append(var)
    
    def eliminar_backup_seleccionado(self):
        selected = [var.get() for var in self.backup_vars if var.get() != ""]
        
        if not selected:
            messagebox.showinfo("Eliminar", "Seleccione al menos un backup para eliminar")
            return
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar {len(selected)} backup(s)?"):
            for filename in selected:
                try:
                    os.remove(filename)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar {filename}:\n{e}")
            
            messagebox.showinfo("Éxito", f"✅ {len(selected)} backup(s) eliminado(s)")
            self.refresh_backups()

# ============== EJECUCIÓN ==============
if __name__ == "__main__":
    app = InventarioApp()
    app.mainloop()