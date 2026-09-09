import io
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    constants,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import processor

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("InvoiceBot")


async def check_access(update: Update) -> bool:
    """Validate if the user is authorized to use this bot."""
    user = update.effective_user
    if not user:
        return False
    if not config.is_user_allowed(user.id):
        if update.effective_message:
            await update.effective_message.reply_text(
                f"الوصول غير مصرح به. معرف حسابك: {user.id}"
            )
        return False
    return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with simple text and buttons."""
    if not await check_access(update):
        return

    keyboard = [
        [
            InlineKeyboardButton("تجربة فاتورة نموذجية", callback_data="btn_sample"),
            InlineKeyboardButton("عرض الخلفية الحالية", callback_data="btn_letterhead"),
        ],
        [
            InlineKeyboardButton("تغيير الخلفية", callback_data="btn_setbg"),
            InlineKeyboardButton("تعليمات الاستخدام", callback_data="btn_help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "مرحباً بك في نظام إضافة خلفيات الفواتير.\n\n"
        "أرسل ملف الفاتورة بصيغة PDF أو صورة، وسيتم إضافة خلفية الشركة الرسمية وإعادتها لك فوراً."
    )

    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command with simple text."""
    if not await check_access(update):
        return

    help_text = (
        "تعليمات الاستخدام:\n\n"
        "1. أرسل ملف الفاتورة بصيغة PDF أو كصورة.\n"
        "2. سيقوم النظام بإضافة الخلفية وإرسال الفاتورة جاهزة.\n\n"
        "الأوامر المتاحة:\n"
        "/start - القائمة الرئيسية\n"
        "/help - تعليمات الاستخدام\n"
        "/sample - تجربة فاتورة نموذجية\n"
        "/getbg - عرض صورة الخلفية الحالية\n"
        "/setbg - رفع صورة خلفية جديدة\n"
        "/resetbg - استعادة الخلفية السابقة\n"
        "/cancel - إلغاء تغيير الخلفية\n\n"
        f"الحد الأقصى لحجم الملف: {config.MAX_FILE_SIZE_MB} ميغابايت."
    )

    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=help_text)


async def set_background_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate background update mode."""
    if not await check_access(update):
        return

    user = update.effective_user
    if not config.is_user_admin(user.id):
        await update.effective_message.reply_text("غير مصرح: هذه الميزة مخصصة للمشرفين فقط.")
        return

    context.user_data["awaiting_bg"] = True
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "تغيير خلفية الفاتورة:\n"
            "أرسل ملف الخلفية الجديد الآن (PDF أو صورة JPG / PNG).\n"
            "للإلغاء أرسل /cancel."
        ),
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending operations like background change."""
    chat_id = update.effective_chat.id
    if context.user_data.get("awaiting_bg"):
        context.user_data["awaiting_bg"] = False
        await context.bot.send_message(chat_id=chat_id, text="تم إلغاء تغيير الخلفية.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="لا توجد عملية قيد الانتظار.")


async def reset_background_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restore the previous background from backup if available."""
    if not await check_access(update):
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    if not config.is_user_admin(user.id):
        await context.bot.send_message(chat_id=chat_id, text="غير مصرح: هذه الميزة مخصصة للمشرفين فقط.")
        return

    # Find any backup file matching invoiceBg.backup.*
    backups = list(config.BASE_DIR.glob("invoiceBg.backup.*"))
    if not backups:
        await context.bot.send_message(chat_id=chat_id, text="لا توجد نسخة احتياطية سابقة.")
        return

    # Pick the most recently modified backup
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    backup_file = backups[0]
    original_ext = backup_file.suffix.replace(".backup", "")  # e.g. .pdf or .jpeg
    target_path = config.BASE_DIR / f"invoiceBg{original_ext}"

    try:
        import shutil
        curr_bg = config.get_background_path()
        if curr_bg.exists() and curr_bg.resolve() != target_path.resolve():
            try:
                curr_bg.unlink()
            except Exception:
                pass
        shutil.copy2(backup_file, target_path)
        config.set_background_path(target_path)
        await context.bot.send_message(chat_id=chat_id, text=f"تمت استعادة الخلفية السابقة بنجاح ({target_path.name}).")
        await get_background_command(update, context)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"فشلت الاستعادة: {e}")


async def get_background_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /getbg command to send the current background (PDF document or image)."""
    if not await check_access(update):
        return

    chat_id = update.effective_chat.id
    bg_path = config.get_background_path()
    if not bg_path.exists():
        await context.bot.send_message(chat_id=chat_id, text="ملف الخلفية غير موجود في السيرفر.")
        return

    is_pdf_bg = processor.is_pdf(bg_path)

    if is_pdf_bg:
        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.UPLOAD_DOCUMENT)
        with open(bg_path, "rb") as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=bg_path.name,
                caption=f"ملف الخلفية الحالي (PDF): {bg_path.name}",
            )
        # Also send visual preview of page 1
        preview_png = processor.get_background_preview(bg_path)
        if preview_png:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(preview_png),
                caption="معاينة تصميم الخلفية (الصفحة 1)",
            )
    else:
        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.UPLOAD_PHOTO)
        with open(bg_path, "rb") as f:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=f,
                caption=f"الخلفية الحالية: {bg_path.name}",
            )


async def sample_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sample command to process the sample invoice."""
    if not await check_access(update):
        return

    chat_id = update.effective_chat.id
    sample_pdf_path = config.BASE_DIR / "sampleInvoice.pdf"
    if not sample_pdf_path.exists():
        await context.bot.send_message(chat_id=chat_id, text="ملف الفاتورة النموذجية غير موجود.")
        return

    bg_path = config.get_background_path()
    if not bg_path.exists():
        await context.bot.send_message(chat_id=chat_id, text="ملف الخلفية غير موجود بالسيرفر.")
        return

    status_msg = await context.bot.send_message(chat_id=chat_id, text="جاري معالجة الفاتورة النموذجية...")
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.UPLOAD_DOCUMENT)

    try:
        out_pdf, preview_png = processor.add_background_to_pdf(sample_pdf_path, bg_path)
        
        await context.bot.send_document(
            chat_id=chat_id,
            document=io.BytesIO(out_pdf),
            filename="sampleInvoice_branded.pdf",
            caption="تم تجهيز الفاتورة النموذجية.",
        )

        if preview_png:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(preview_png),
                caption="معاينة الصفحة الأولى",
            )

        await status_msg.delete()
    except Exception as e:
        logger.error(f"Error processing sample invoice: {e}", exc_info=True)
        await status_msg.edit_text(f"حدث خطأ: {e}")


async def process_new_background(update: Update, context: ContextTypes.DEFAULT_TYPE, file_bytes: bytes, file_name: str = "background"):
    """Saves new background (PDF or Image), backs up current, and renders a test sample."""
    import shutil
    import pymupdf
    from PIL import Image

    chat_id = update.effective_chat.id

    # Check if the uploaded file is a PDF
    is_pdf_file = processor.is_pdf(file_bytes) or file_name.lower().endswith(".pdf")
    if is_pdf_file:
        try:
            bg_doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            if len(bg_doc) == 0:
                raise Exception("ملف PDF فارغ بدون صفحات")
            page_count = len(bg_doc)
            width = int(bg_doc[0].rect.width)
            height = int(bg_doc[0].rect.height)
            bg_doc.close()
            ext = ".pdf"
            desc_info = f"ملف PDF ({page_count} صفحة، {width}x{height} نقطة)"
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"الملف المرسل ليس ملف PDF صالح: {e}",
            )
            return
    else:
        # Validate image using PIL
        try:
            pil_img = Image.open(io.BytesIO(file_bytes))
            pil_img.verify()
            pil_img = Image.open(io.BytesIO(file_bytes))
            width, height = pil_img.size
            ext = ".png" if pil_img.format == "PNG" else ".jpeg"
            desc_info = f"صورة ({width}x{height} بكسل)"
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"الملف المرسل ليس صورة أو PDF صالح: {e}\nيرجى إرسال ملف PDF أو صورة JPG/PNG.",
            )
            return

    # Backup existing background if present
    curr_bg = config.get_background_path()
    if curr_bg.exists():
        backup_path = config.BASE_DIR / f"invoiceBg.backup{curr_bg.suffix}"
        try:
            shutil.copy2(curr_bg, backup_path)
        except Exception as e:
            logger.warning(f"Could not create backup of background: {e}")

    # Overwrite / write new background file
    target_bg = config.BASE_DIR / f"invoiceBg{ext}"
    try:
        if curr_bg.exists() and curr_bg.resolve() != target_bg.resolve():
            try:
                curr_bg.unlink()
            except Exception as e:
                logger.warning(f"Could not remove old background {curr_bg}: {e}")
        target_bg.write_bytes(file_bytes)
        config.set_background_path(target_bg)
        context.user_data["awaiting_bg"] = False
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"فشل حفظ ملف الخلفية: {e}")
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"تم حفظ الخلفية الجديدة بنجاح: {desc_info}",
    )

    # Show preview of the new background
    try:
        preview_bytes = processor.get_background_preview(target_bg)
        if preview_bytes:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(preview_bytes),
                caption="معاينة تصميم الخلفية الجديد",
            )
    except Exception as e:
        logger.warning(f"Could not generate background preview: {e}")

    # Automatically generate sample preview with new background
    sample_pdf_path = config.BASE_DIR / "sampleInvoice.pdf"
    if sample_pdf_path.exists():
        try:
            out_pdf, preview_png = processor.add_background_to_pdf(sample_pdf_path, target_bg)
            if preview_png:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=io.BytesIO(preview_png),
                    caption="معاينة الفاتورة النموذجية مع الخلفية الجديدة",
                )
        except Exception as e:
            logger.warning(f"Could not generate sample preview: {e}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded documents (PDFs or uncompressed images)."""
    if not await check_access(update):
        return

    doc = update.message.document
    file_name = doc.file_name or "invoice.pdf"
    file_ext = Path(file_name).suffix.lower()
    chat_id = update.effective_chat.id

    # Check size limit
    max_bytes = config.MAX_FILE_SIZE_MB * 1024 * 1024
    if doc.file_size and doc.file_size > max_bytes:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"حجم الملف كبير جداً. الحد الأقصى: {config.MAX_FILE_SIZE_MB} ميغابايت.",
        )
        return

    # Check if user is uploading a new background letterhead
    caption = update.message.caption or ""
    is_bg_request = context.user_data.get("awaiting_bg") or ("/setbg" in caption)
    if is_bg_request:
        if not config.is_user_admin(update.effective_user.id):
            await context.bot.send_message(chat_id=chat_id, text="غير مصرح: هذه الميزة للمشرفين فقط.")
            return

        if file_ext not in [".pdf", ".jpg", ".jpeg", ".png", ".webp"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text="يجب أن تكون الخلفية ملف PDF أو صورة (JPG أو PNG). للإلغاء أرسل /cancel.",
            )
            return

        status_msg = await context.bot.send_message(chat_id=chat_id, text="جاري تحديث الخلفية...")
        tg_file = await context.bot.get_file(doc.file_id)
        input_bytes = await tg_file.download_as_bytearray()
        await status_msg.delete()
        await process_new_background(update, context, bytes(input_bytes), file_name)
        return

    # Check supported extensions
    supported_exts = [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
    if file_ext not in supported_exts:
        await context.bot.send_message(
            chat_id=chat_id,
            text="نوع الملف غير مدعوم. يرجى إرسال PDF أو صورة.",
        )
        return

    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"جاري معالجة {file_name}...",
    )
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.UPLOAD_DOCUMENT)

    try:
        # Download file
        tg_file = await context.bot.get_file(doc.file_id)
        input_bytes = await tg_file.download_as_bytearray()

        # Check background exists
        bg_path = config.get_background_path()
        if not bg_path.exists():
            raise processor.InvoiceProcessingError("ملف الخلفية غير موجود بالسيرفر.")

        # Process file
        orig_stem = Path(file_name).stem
        if file_ext == ".pdf":
            out_pdf_bytes, preview_bytes = processor.add_background_to_pdf(
                bytes(input_bytes), bg_path
            )
        else:
            out_pdf_bytes, preview_bytes = processor.add_background_to_image(
                bytes(input_bytes), bg_path
            )

        output_filename = f"{orig_stem}_branded.pdf"

        # Send processed PDF
        await context.bot.send_document(
            chat_id=chat_id,
            document=io.BytesIO(out_pdf_bytes),
            filename=output_filename,
            caption=f"تم تجهيز الفاتورة: {output_filename}",
        )

        # Send preview image
        if preview_bytes:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(preview_bytes),
                caption="معاينة الصفحة الأولى",
            )

        await status_msg.delete()
        logger.info(f"Processed {file_name} for user {update.effective_user.id}")

    except processor.InvoiceProcessingError as e:
        logger.warning(f"Processing error: {e}")
        await status_msg.edit_text(f"خطأ أثناء المعالجة: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while processing {file_name}: {e}", exc_info=True)
        await status_msg.edit_text("حدث خطأ أثناء معالجة الفاتورة. يرجى المحاولة مرة أخرى.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos sent directly (compressed images)."""
    if not await check_access(update):
        return

    chat_id = update.effective_chat.id

    # Check if user is uploading a new background letterhead
    caption = update.message.caption or ""
    is_bg_request = context.user_data.get("awaiting_bg") or ("/setbg" in caption)
    if is_bg_request:
        if not config.is_user_admin(update.effective_user.id):
            await context.bot.send_message(chat_id=chat_id, text="غير مصرح: هذه الميزة للمشرفين فقط.")
            return

        status_msg = await context.bot.send_message(chat_id=chat_id, text="جاري تحديث الخلفية...")
        photo = update.message.photo[-1]
        tg_file = await context.bot.get_file(photo.file_id)
        input_bytes = await tg_file.download_as_bytearray()
        await status_msg.delete()
        await process_new_background(update, context, bytes(input_bytes), "background.jpg")
        return

    bg_path = config.get_background_path()
    if not bg_path.exists():
        await context.bot.send_message(chat_id=chat_id, text="ملف الخلفية غير موجود بالسيرفر.")
        return

    photo = update.message.photo[-1]
    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="جاري معالجة الصورة...",
    )
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.UPLOAD_DOCUMENT)

    try:
        tg_file = await context.bot.get_file(photo.file_id)
        input_bytes = await tg_file.download_as_bytearray()

        out_pdf_bytes, preview_bytes = processor.add_background_to_image(
            bytes(input_bytes), bg_path
        )

        output_filename = "invoice_branded.pdf"

        await context.bot.send_document(
            chat_id=chat_id,
            document=io.BytesIO(out_pdf_bytes),
            filename=output_filename,
            caption="تم تحويل الصورة وإضافة الخلفية بنجاح.",
        )

        if preview_bytes:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(preview_bytes),
                caption="معاينة الفاتورة",
            )

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Error processing photo: {e}", exc_info=True)
        await status_msg.edit_text(f"حدث خطأ أثناء معالجة الصورة: {e}")


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks safely without relying on update.message."""
    query = update.callback_query
    await query.answer()

    if query.data == "btn_sample":
        await sample_command(update, context)
    elif query.data == "btn_letterhead":
        await get_background_command(update, context)
    elif query.data == "btn_setbg":
        await set_background_command(update, context)
    elif query.data == "btn_help":
        await help_command(update, context)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler so Render/cloud platforms detect an open port and stay healthy."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ASC Invoice Logo Bot is online and healthy!")

    def log_message(self, format, *args):
        # Silence routine access log messages in terminal
        pass


def start_health_check_server():
    """Starts a lightweight HTTP server on $PORT for Render / cloud health checks."""
    import os
    import threading
    port_str = os.environ.get("PORT") or ("10000" if os.environ.get("RENDER") else None)
    if not port_str:
        return
    try:
        port = int(port_str)
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"🌐 خادم الفحص الصحي متصل على المنفذ {port} (Render Health Check Online)")
    except Exception as e:
        logger.warning(f"Could not start health check server: {e}")


def main():
    """Start and run the Telegram Bot."""
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("=" * 70)
        print("TELEGRAM_BOT_TOKEN is missing or not set!")
        print("Please set your Telegram bot token in the .env file:")
        print("  TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        print("=" * 70)
        sys.exit(1)

    # Start health check server if on Render/cloud
    start_health_check_server()

    print("جاري تشغيل البوت...")
    print(f"ملف الخلفية: {config.get_background_path().resolve()}")
    if config.ALLOWED_USER_IDS:
        print(f"المستخدمين المصرح لهم: {config.ALLOWED_USER_IDS}")
    else:
        print("البوت متاح لجميع المستخدمين")

    # Build Application
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("sample", sample_command))
    app.add_handler(CommandHandler("getbg", get_background_command))
    app.add_handler(CommandHandler("setbg", set_background_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("resetbg", reset_background_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Document & Photo Handlers
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("البوت متصل الآن وجاهز لاستقبال الفواتير.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
