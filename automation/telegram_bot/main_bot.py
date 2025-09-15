#!/usr/bin/env python3
"""
Main Telegram Bot Application (webhook-compatible)
Provides a minimal Application wrapper and integrates /snap with the SnapCommandOrchestrator.
This satisfies imports for webhook_server.py and allows either webhook or polling modes.
"""

import logging
import os
from typing import Optional

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

from .config import TelegramBotConfig
from .snap_command_orchestrator import SnapCommandOrchestrator
from .health_server import start_health_server
from utils.balance_manager import get_balance_manager
from utils.crypto_payments import create_charge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TinderBotApplication:
    """Minimal wrapper around python-telegram-bot Application.

    Exposes `application` for webhook_server.py and wires up a functional /snap command
    via SnapCommandOrchestrator.
    """

    def __init__(self):
        # Validate token via config (raises if missing)
        self.config = TelegramBotConfig()

        # Build Application
        self.application: Application = Application.builder().token(self.config.BOT_TOKEN).build()

        # Orchestrator for /snap (pass Application for bot access)
        self.snap_orchestrator = SnapCommandOrchestrator(telegram_app=self.application)

        # Start health server for readiness/liveness checks
        start_health_server()

        # Register handlers
        self._register_handlers()

        logger.info("✅ TinderBotApplication initialized (webhook-compatible)")

    def _register_handlers(self):
        """Register basic command handlers"""
        self.application.add_handler(CommandHandler("start", self._start))
        self.application.add_handler(CommandHandler("help", self._help))
        self.application.add_handler(CommandHandler("menu", self._menu))
        self.application.add_handler(CommandHandler("balance", self._balance))
        self.application.add_handler(CommandHandler("addfunds", self._addfunds))
        self.application.add_handler(CommandHandler("snap", self.snap_orchestrator.handle_snap_command))
        # Menu callbacks first
        self.application.add_handler(CallbackQueryHandler(self._handle_menu_cb, pattern=r"^(menu_|refresh_active)"))
        self.application.add_handler(CallbackQueryHandler(self.snap_orchestrator.handle_callback_query))

        # Fallback text handler (optional)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._fallback_text))

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Publish commands so Telegram shows the new menu
        try:
            await self.application.bot.set_my_commands([
                BotCommand("start", "Welcome and get started"),
                BotCommand("menu", "Open navigation"),
                BotCommand("snap", "Create Snapchat accounts"),
                BotCommand("balance", "View your balance"),
                BotCommand("addfunds", "Add funds via crypto"),
                BotCommand("help", "Help and usage"),
            ])
        except Exception:
            pass

        welcome = (
            "Welcome.\n\n"
            "We create high-quality Snapchat accounts using real-device automation with strict integrity checks.\n"
            "Each account is set up with human pacing, realistic device profiles, and optional Bitmoji/profile setup.\n\n"
            "How it works:\n"
            "1) Place an order: /snap N (e.g., /snap 1)\n"
            "2) Watch progress in a single dashboard message\n"
            "3) Download your accounts on completion (CSV/JSON/TXT)\n\n"
            "Quality & safety:\n"
            "- Realistic device configs and human-like behavior\n"
            "- Verified APKs and strict checks in production\n"
            "- Optional webhooks for live events\n\n"
            "Use /menu for quick actions."
        )
        if update.message:
            await update.message.reply_text(welcome)
        else:
            await context.bot.send_message(chat_id=update.effective_user.id, text=welcome)
        await self._menu(update, context)

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "Commands:\n"
            "/menu – navigation and next steps\n"
            "/snap N – start an order for N accounts (e.g., /snap 3)\n"
            "/help – this help message\n\n"
            "Tip: after ordering, use the dashboard buttons to refresh status, view details, and download files."
        )
        if update.message:
            await update.message.reply_text(text)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text)

    async def _menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("New order (/snap)", callback_data="menu_nop")],
            [InlineKeyboardButton("Active requests", callback_data="refresh_active")],
            [InlineKeyboardButton("Balance", callback_data="menu_balance"), InlineKeyboardButton("Add funds", callback_data="menu_addfunds")],
            [InlineKeyboardButton("Help", callback_data="menu_help")]
        ]
        text = (
            "Menu:\n\n"
            "New order: /snap N (e.g., /snap 1)\n"
            "Active requests: shows your current orders\n"
            "Help: basic guidance and next steps"
        )
        # Support both message and callback origins
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _fallback_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Type /snap to start account creation.")

    async def _balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bm = get_balance_manager()
        user_id = update.effective_user.id
        free = bm.is_free_mode()
        bal = bm.get_balance(user_id)
        note = "Free test mode is ON. Orders do not deduct balance." if free else ""
        text = f"Balance: ${bal:.2f}\n{note}"
        if update.message:
            await update.message.reply_text(text)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text)

    async def _addfunds(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        try:
            amount = 10.0  # default quick top-up
            if context.args and len(context.args) >= 1:
                try:
                    amount = max(1.0, float(context.args[0]))
                except Exception:
                    pass
            result = await create_charge(user_id, amount, description=f"Top-up ${amount:.2f}")
            if result.get('simulated'):
                msg = result.get('message', 'Credited in free mode')
                if update.message:
                    await update.message.reply_text(msg)
                elif update.callback_query:
                    await update.callback_query.message.reply_text(msg)
            else:
                url = result.get('hosted_url')
                msg = f"Complete your payment here: {url}"
                if update.message:
                    await update.message.reply_text(msg)
                elif update.callback_query:
                    await update.callback_query.message.reply_text(msg)
        except Exception as e:
            if update.message:
                await update.message.reply_text("Payments unavailable right now. Try again later.")
            elif update.callback_query:
                await update.callback_query.message.reply_text("Payments unavailable right now. Try again later.")

    async def _handle_menu_cb(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        data = q.data or ""
        try:
            if data == "menu_help":
                await q.answer()
                await self._help(update, context)
            elif data == "menu_balance":
                await q.answer()
                await self._balance(update, context)
            elif data == "menu_addfunds":
                await q.answer()
                # Default quick link for 10 USD
                context.args = ["10"]
                await self._addfunds(update, context)
            elif data == "menu_nop":
                await q.answer()
                await q.message.reply_text("To start an order, type /snap 1 (or another number).")
            elif data == "refresh_active":
                await q.answer(text="No active requests to display yet.", show_alert=False)
            else:
                await q.answer()
        except Exception:
            try:
                await q.answer()
            except Exception:
                pass


# Optional: allow running in polling mode for local testing
if __name__ == "__main__":
    async def _run_polling():
        import asyncio
        app = TinderBotApplication()
        await app.application.initialize()
        await app.application.start()
        # In PTB v20, you can use app.application.updater.start_polling() for advanced control
        await app.application.updater.start_polling()
        while True:
            await asyncio.sleep(1)

    try:
        import asyncio
        asyncio.run(_run_polling())
    except KeyboardInterrupt:
        print("\nExiting.")
