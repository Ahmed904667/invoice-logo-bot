import io
import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import config
import processor


class InvoiceApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ASC Invoice Letterhead & Logo Adder")
        self.geometry("960x680")
        self.minsize(850, 600)

        # Variables
        self.bg_path_var = tk.StringVar(value=str(config.get_background_path()))
        self.invoice_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.status_var = tk.StringVar(value="جاهز للاستخدام | Ready")
        self.is_batch_var = tk.BooleanVar(value=False)
        self.last_output_pdf = None

        # Style configuration
        self._setup_styles()

        # Build UI
        self._build_header()
        self._build_main_content()
        self._build_footer()

        # Load initial background preview
        self.after(200, self._load_initial_preview)

    def _setup_styles(self):
        self.style = ttk.Style(self)
        # Try to use 'clam' or 'vista' for modern native appearance
        available_themes = self.style.theme_names()
        if "vista" in available_themes:
            self.style.theme_use("vista")
        elif "clam" in available_themes:
            self.style.theme_use("clam")

        self.configure(bg="#f4f6f9")

        # Custom styles
        self.style.configure("Header.TFrame", background="#1e293b")
        self.style.configure("Card.TFrame", background="#ffffff", relief="flat")
        self.style.configure("Footer.TFrame", background="#e2e8f0")

        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 11, "bold"),
            padding=8,
        )
        self.style.configure(
            "Action.TButton",
            font=("Segoe UI", 9),
            padding=5,
        )

    def _build_header(self):
        header_frame = tk.Frame(self, bg="#1e293b", height=65)
        header_frame.pack(side=tk.TOP, fill=tk.X)

        title_lbl = tk.Label(
            header_frame,
            text="🧾 ASC Invoice Logo & Letterhead Adder",
            font=("Segoe UI", 15, "bold"),
            fg="#ffffff",
            bg="#1e293b",
            padx=20,
            pady=10,
        )
        title_lbl.pack(side=tk.LEFT)

        subtitle_lbl = tk.Label(
            header_frame,
            text="نظام إضافة الخلفيات وترويسة الشركات للفواتير",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#1e293b",
            padx=20,
        )
        subtitle_lbl.pack(side=tk.RIGHT)

    def _build_main_content(self):
        content_frame = tk.Frame(self, bg="#f4f6f9")
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=15)

        # 2 Columns: Left is Controls (450px), Right is Live Preview
        left_col = tk.Frame(content_frame, bg="#f4f6f9", width=460)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 15))

        right_col = tk.Frame(content_frame, bg="#ffffff", relief="solid", bd=1)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # ----------------- LEFT COLUMN: CONTROLS -----------------

        # Section 1: Background Template Card
        bg_card = tk.LabelFrame(
            left_col,
            text=" 1. تصميم الخلفية / الترويسة (Background Template) ",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            padx=12,
            pady=12,
            relief="solid",
            bd=1,
        )
        bg_card.pack(fill=tk.X, pady=(0, 12))

        bg_entry = ttk.Entry(bg_card, textvariable=self.bg_path_var, font=("Segoe UI", 9))
        bg_entry.pack(fill=tk.X, pady=(0, 8))

        bg_btn_row = tk.Frame(bg_card, bg="#ffffff")
        bg_btn_row.pack(fill=tk.X)

        browse_bg_btn = ttk.Button(
            bg_btn_row,
            text="📁 اختيار خلفية (PDF / صورة)...",
            command=self._browse_background,
            style="Action.TButton",
        )
        browse_bg_btn.pack(side=tk.LEFT, padx=(0, 6))

        reset_bg_btn = ttk.Button(
            bg_btn_row,
            text="🔄 الافتراضية",
            command=self._reset_background,
            style="Action.TButton",
        )
        reset_bg_btn.pack(side=tk.LEFT)

        # Section 2: Input Invoice Card
        inv_card = tk.LabelFrame(
            left_col,
            text=" 2. ملف الفاتورة المراد معالجتها (Input Invoice) ",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            padx=12,
            pady=12,
            relief="solid",
            bd=1,
        )
        inv_card.pack(fill=tk.X, pady=(0, 12))

        inv_entry = ttk.Entry(inv_card, textvariable=self.invoice_path_var, font=("Segoe UI", 9))
        inv_entry.pack(fill=tk.X, pady=(0, 8))

        inv_btn_row = tk.Frame(inv_card, bg="#ffffff")
        inv_btn_row.pack(fill=tk.X)

        browse_file_btn = ttk.Button(
            inv_btn_row,
            text="📄 اختيار ملف فاتورة (PDF/صورة)...",
            command=self._browse_invoice_file,
            style="Action.TButton",
        )
        browse_file_btn.pack(side=tk.LEFT, padx=(0, 6))

        browse_dir_btn = ttk.Button(
            inv_btn_row,
            text="📂 مجلد كامل (Batch)",
            command=self._browse_invoice_dir,
            style="Action.TButton",
        )
        browse_dir_btn.pack(side=tk.LEFT, padx=(0, 6))

        sample_btn = ttk.Button(
            inv_btn_row,
            text="⭐ نموذج تجريبي",
            command=self._load_sample_invoice,
            style="Action.TButton",
        )
        sample_btn.pack(side=tk.LEFT)

        # Section 3: Output destination (Optional)
        out_card = tk.LabelFrame(
            left_col,
            text=" 3. مجلد الحفظ (Output Destination) ",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            padx=12,
            pady=10,
            relief="solid",
            bd=1,
        )
        out_card.pack(fill=tk.X, pady=(0, 15))

        out_hint = tk.Label(
            out_card,
            text="افتراضياً: يتم حفظ الملف بجانب الفاتورة الأصلية باسم `[الاسم]_branded.pdf`",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#ffffff",
        )
        out_hint.pack(anchor="w", pady=(0, 4))

        out_entry = ttk.Entry(out_card, textvariable=self.output_dir_var, font=("Segoe UI", 9))
        out_entry.pack(fill=tk.X, pady=(0, 6))

        browse_out_btn = ttk.Button(
            out_card,
            text="📁 تحديد مجلد حفظ مخصص (اختياري)...",
            command=self._browse_output_dir,
            style="Action.TButton",
        )
        browse_out_btn.pack(anchor="w")

        # Section 4: Action Process Button
        self.process_btn = tk.Button(
            left_col,
            text="🚀 إضافة الخلفية وإنشاء الفاتورة (Generate PDF)",
            font=("Segoe UI", 11, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            pady=10,
            command=self._start_processing,
        )
        self.process_btn.pack(fill=tk.X, pady=(0, 10))

        # Progress bar
        self.progress_bar = ttk.Progressbar(left_col, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Action button row (Open Result / Folder)
        self.result_btn_row = tk.Frame(left_col, bg="#f4f6f9")
        self.result_btn_row.pack(fill=tk.X)

        self.open_pdf_btn = ttk.Button(
            self.result_btn_row,
            text="👁️ فتح ملف PDF الناتج",
            state=tk.DISABLED,
            command=self._open_result_pdf,
            style="Action.TButton",
        )
        self.open_pdf_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.open_dir_btn = ttk.Button(
            self.result_btn_row,
            text="📂 فتح المجلد",
            state=tk.DISABLED,
            command=self._open_result_dir,
            style="Action.TButton",
        )
        self.open_dir_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # ----------------- RIGHT COLUMN: PREVIEW -----------------
        preview_header = tk.Frame(right_col, bg="#f8fafc", height=40)
        preview_header.pack(side=tk.TOP, fill=tk.X)

        prev_title = tk.Label(
            preview_header,
            text="معاينة الصفحة الأولى (Page 1 Preview)",
            font=("Segoe UI", 10, "bold"),
            fg="#334155",
            bg="#f8fafc",
            padx=12,
            pady=8,
        )
        prev_title.pack(side=tk.LEFT)

        self.prev_info_lbl = tk.Label(
            preview_header,
            text="لا توجد معاينة حالياً",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#f8fafc",
            padx=12,
        )
        self.prev_info_lbl.pack(side=tk.RIGHT)

        # Canvas container for the preview
        self.preview_container = tk.Frame(right_col, bg="#ffffff")
        self.preview_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.preview_lbl = tk.Label(
            self.preview_container,
            text="حدد فاتورة واضغط على زر المعالجة\nلعرض النتيجة هنا مباشرة",
            font=("Segoe UI", 11),
            fg="#94a3b8",
            bg="#ffffff",
            justify="center",
        )
        self.preview_lbl.pack(fill=tk.BOTH, expand=True)

    def _build_footer(self):
        footer_frame = tk.Frame(self, bg="#e2e8f0", height=30)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

        status_lbl = tk.Label(
            footer_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg="#334155",
            bg="#e2e8f0",
            padx=15,
            pady=4,
        )
        status_lbl.pack(side=tk.LEFT)

    # ------------------ ACTIONS & LOGIC ------------------

    def _browse_background(self):
        filetypes = [
            ("All Supported Templates", "*.pdf;*.jpeg;*.jpg;*.png;*.webp"),
            ("PDF Documents (*.pdf)", "*.pdf"),
            ("Image Files (*.jpg, *.png)", "*.jpeg;*.jpg;*.png;*.webp"),
        ]
        chosen = filedialog.askopenfilename(
            title="اختر ملف تصميم الخلفية",
            filetypes=filetypes,
            initialdir=str(BASE_DIR),
        )
        if chosen:
            self.bg_path_var.set(chosen)
            self._update_background_preview(Path(chosen))

    def _reset_background(self):
        default_path = config.get_background_path()
        self.bg_path_var.set(str(default_path))
        self._update_background_preview(default_path)

    def _browse_invoice_file(self):
        filetypes = [
            ("Invoice Files (PDF / Images)", "*.pdf;*.jpeg;*.jpg;*.png;*.webp"),
            ("PDF Documents (*.pdf)", "*.pdf"),
            ("Images (*.jpg, *.png)", "*.jpeg;*.jpg;*.png;*.webp"),
        ]
        chosen = filedialog.askopenfilename(
            title="اختر ملف الفاتورة",
            filetypes=filetypes,
            initialdir=str(BASE_DIR),
        )
        if chosen:
            self.invoice_path_var.set(chosen)
            self.is_batch_var.set(False)
            self.status_var.set(f"تم اختيار: {Path(chosen).name}")

    def _browse_invoice_dir(self):
        chosen = filedialog.askdirectory(title="اختر مجلد الفواتير للمعالجة الجماعية")
        if chosen:
            self.invoice_path_var.set(chosen)
            self.is_batch_var.set(True)
            self.status_var.set(f"تم اختيار مجلد: {Path(chosen).name} (Batch mode)")

    def _browse_output_dir(self):
        chosen = filedialog.askdirectory(title="اختر مجلد حفظ الفواتير الجاهزة")
        if chosen:
            self.output_dir_var.set(chosen)

    def _load_sample_invoice(self):
        sample_file = BASE_DIR / "sampleInvoice.pdf"
        if sample_file.exists():
            self.invoice_path_var.set(str(sample_file))
            self.is_batch_var.set(False)
            self.status_var.set("تم تحميل الفاتورة النموذجية (sampleInvoice.pdf)")
        else:
            messagebox.showwarning("تنبيه", "ملف الفاتورة النموذجية sampleInvoice.pdf غير موجود.")

    def _load_initial_preview(self):
        bg = config.get_background_path()
        if bg.exists():
            self._update_background_preview(bg)

    def _update_background_preview(self, bg_path: Path):
        try:
            preview_bytes = processor.get_background_preview(bg_path, dpi=120)
            if preview_bytes:
                self._display_preview_image(preview_bytes, f"خلفية: {bg_path.name}")
        except Exception:
            pass

    def _display_preview_image(self, img_bytes: bytes, caption: str = ""):
        try:
            pil_img = Image.open(io.BytesIO(img_bytes))

            # Scale to fit container nicely (max ~420w x 550h)
            max_w, max_h = 420, 520
            orig_w, orig_h = pil_img.size
            ratio = min(max_w / orig_w, max_h / orig_h)
            new_w = max(1, int(orig_w * ratio))
            new_h = max(1, int(orig_h * ratio))

            scaled_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(scaled_img)

            self.preview_lbl.configure(image=tk_img, text="")
            self.preview_lbl.image = tk_img  # Retain reference!
            self.prev_info_lbl.configure(text=caption)
        except Exception as e:
            self.preview_lbl.configure(image="", text=f"تعذر عرض المعاينة: {e}")

    def _start_processing(self):
        inv_input = self.invoice_path_var.get().strip()
        bg_input = self.bg_path_var.get().strip()

        if not inv_input:
            messagebox.showerror("خطأ", "يرجى اختيار ملف الفاتورة أولاً.")
            return

        if not bg_input or not Path(bg_input).exists():
            messagebox.showerror("خطأ", f"ملف تصميم الخلفية غير موجود:\n{bg_input}")
            return

        # Disable button & start progress bar
        self.process_btn.configure(state=tk.DISABLED, text="⏳ جاري المعالجة...")
        self.progress_bar.start(10)
        self.status_var.set("جاري معالجة الفاتورة وإضافة الخلفية...")

        # Run in thread so UI doesn't freeze
        t = threading.Thread(target=self._run_processing_task, args=(Path(inv_input), Path(bg_input)), daemon=True)
        t.start()

    def _run_processing_task(self, inv_path: Path, bg_path: Path):
        custom_out_dir = self.output_dir_var.get().strip()
        out_dir = Path(custom_out_dir) if custom_out_dir else None

        try:
            if inv_path.is_dir():
                # Directory batch mode
                target_dir = out_dir if out_dir else inv_path / "branded_output"
                target_dir.mkdir(parents=True, exist_ok=True)

                supported_exts = [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
                files = [
                    f for f in inv_path.iterdir()
                    if f.is_file() and f.suffix.lower() in supported_exts and not f.name.endswith("_branded.pdf")
                ]

                if not files:
                    self._on_processing_complete(False, "لم يتم العثور على ملفات مدعومة داخل المجلد المختار.", None, None)
                    return

                count = 0
                last_pdf = None
                last_preview = None

                for f in files:
                    target_file = target_dir / f"{f.stem}_branded.pdf"
                    ext = f.suffix.lower()
                    if ext == ".pdf":
                        out_pdf, prev = processor.add_background_to_pdf(f, bg_path, output_path=target_file)
                    else:
                        out_pdf, prev = processor.add_background_to_image(f, bg_path, output_path=target_file)
                    last_pdf = target_file
                    last_preview = prev
                    count += 1

                msg = f"تم بنجاح معالجة {count} ملف وحفظها في:\n{target_dir}"
                self._on_processing_complete(True, msg, last_pdf, last_preview)

            elif inv_path.is_file():
                # Single file mode
                ext = inv_path.suffix.lower()
                if out_dir:
                    out_file = out_dir / f"{inv_path.stem}_branded.pdf"
                else:
                    out_file = inv_path.parent / f"{inv_path.stem}_branded.pdf"

                if ext == ".pdf":
                    out_pdf, preview_bytes = processor.add_background_to_pdf(inv_path, bg_path, output_path=out_file)
                elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    out_pdf, preview_bytes = processor.add_background_to_image(inv_path, bg_path, output_path=out_file)
                else:
                    self._on_processing_complete(False, f"صيغة الملف غير مدعومة: {ext}", None, None)
                    return

                msg = f"تمت المعالجة بنجاح! الملف: {out_file.name} ({len(out_pdf) // 1024} KB)"
                self._on_processing_complete(True, msg, out_file, preview_bytes)

            else:
                self._on_processing_complete(False, "المسار المحدد غير صالح أو غير موجود.", None, None)

        except Exception as e:
            self._on_processing_complete(False, f"حدث خطأ أثناء المعالجة: {e}", None, None)

    def _on_processing_complete(self, success: bool, message: str, result_pdf: Path, preview_bytes: bytes):
        # Update UI back on main thread
        self.after(0, self._finalize_ui, success, message, result_pdf, preview_bytes)

    def _finalize_ui(self, success: bool, message: str, result_pdf: Path, preview_bytes: bytes):
        self.progress_bar.stop()
        self.process_btn.configure(state=tk.NORMAL, text="🚀 إضافة الخلفية وإنشاء الفاتورة (Generate PDF)")
        self.status_var.set(message)

        if success:
            self.last_output_pdf = result_pdf
            self.open_pdf_btn.configure(state=tk.NORMAL)
            self.open_dir_btn.configure(state=tk.NORMAL)

            if preview_bytes:
                self._display_preview_image(preview_bytes, f"فاتورة جاهزة: {result_pdf.name}")

            messagebox.showinfo("نجاح العملية", f"✅ {message}")
        else:
            messagebox.showerror("خطأ", message)

    def _open_result_pdf(self):
        if self.last_output_pdf and self.last_output_pdf.exists():
            try:
                os.startfile(str(self.last_output_pdf))
            except Exception as e:
                messagebox.showerror("خطأ", f"تعذر فتح الملف: {e}")

    def _open_result_dir(self):
        if self.last_output_pdf and self.last_output_pdf.exists():
            folder = self.last_output_pdf.parent
            try:
                os.startfile(str(folder))
            except Exception as e:
                messagebox.showerror("خطأ", f"تعذر فتح المجلد: {e}")


def main():
    app = InvoiceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
