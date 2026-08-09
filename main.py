import re
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from typing import List, Dict

from scraper import build_url, collect_products


class LowBallApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("LowBall")
        self.geometry("400x520")
        self.resizable(False, False)
        self.configure(bg="#f5f5f5")

        self.product_name = ""
        self.current_store = ""
        self.permission_granted = False
        self.pages_to_scan = 1
        self.compare_window = None
        self.raw_products: List[Dict[str, str]] = []
        self.visible_products: List[Dict[str, str]] = []
        self.compare_items: List[Dict[str, str]] = []
        self.compare_visible = False
        self.current_screen = "search"
        self.scan_in_progress = False
        self.verification_window = None
        self.verification_browser = None
        self.verification_page = None

        self.style = ttk.Style(self)
        self.style.configure("TButton", padding=6)
        self.style.configure("TLabel", background="#f5f5f5")

        self._build_ui()

    def _build_ui(self) -> None:
        self.container = tk.Frame(self, bg="#f5f5f5")
        self.container.pack(fill="both", expand=True)

        self.search_frame = self._build_search_frame()
        self.results_frame = self._build_results_frame()
        self.products_frame = self._build_products_frame()
        self.global_controls = self._build_global_controls()
        self.permission_window = None

        self.show_frame("search")

    def _build_search_frame(self) -> tk.Frame:
        frame = tk.Frame(self.container, bg="#f5f5f5", padx=18, pady=16)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="LowBall", font=("Arial", 20, "bold"), bg="#f5f5f5", fg="#1a1a1a").pack(pady=(0, 14))

        option_bar = tk.Frame(frame, bg="#f5f5f5")
        option_bar.pack(fill="x", pady=(0, 12))
        tk.Button(option_bar, text="Text Search", bg="#4a90e2", fg="white", relief="flat", padx=12, pady=8, command=lambda: None).pack(fill="x")

        tk.Label(frame, text="Search", font=("Arial", 10, "bold"), bg="#f5f5f5", fg="#333333", anchor="w").pack(anchor="w", pady=(6, 4))
        self.search_entry = tk.Entry(frame, width=30, font=("Arial", 12))
        self.search_entry.pack(fill="x", pady=(0, 10))

        self.search_error = tk.Label(frame, text="", fg="#ff0000", bg="#f5f5f5", font=("Arial", 10))
        self.search_error.pack(pady=(0, 8))

        tk.Button(frame, text="Search", bg="#4a90e2", fg="white", relief="flat", padx=12, pady=8, command=self.on_search).pack(fill="x")

        tk.Label(frame, text="v0.0.7 beta", bg="#f5f5f5", fg="#666666", font=("Arial", 9)).pack(pady=(18, 2))
        tk.Label(frame, text="© 2026 Blast Team", bg="#f5f5f5", fg="#666666", font=("Arial", 9)).pack()
        return frame

    def _build_results_frame(self) -> tk.Frame:
        frame = tk.Frame(self.container, bg="#f5f5f5", padx=18, pady=16)
        frame.pack(fill="both", expand=True)

        self.results_title = tk.Label(frame, text="Search Results", font=("Arial", 16, "bold"), bg="#f5f5f5", fg="#1a1a1a")
        self.results_title.pack(anchor="w", pady=(0, 8))

        self.shop_links_frame = tk.Frame(frame, bg="#f5f5f5")
        self.shop_links_frame.pack(fill="both", expand=True)

        self.link_buttons = {}
        for store in ["amazon", "alibaba", "walmart", "target"]:
            btn = tk.Button(
                self.shop_links_frame,
                text=store.title(),
                bg="#f9f9f9",
                fg="#333333",
                relief="solid",
                bd=1,
                padx=10,
                pady=10,
                anchor="w",
                justify="left",
                command=lambda target=store: self.on_store_click(target),
            )
            btn.pack(fill="x", pady=6)
            self.link_buttons[store] = btn

        footer = tk.Frame(frame, bg="#f5f5f5")
        footer.pack(fill="x", side="bottom", pady=(10, 0))
        tk.Button(footer, text="Back", bg="white", fg="#4a90e2", relief="flat", command=self.on_back).pack(anchor="w")
        return frame

    def _build_global_controls(self) -> tk.Frame:
        frame = tk.Frame(self.container, bg="#f5f5f5", padx=18)
        frame.pack(fill="x", side="bottom", pady=(0, 12))

        self.push_compare_button = tk.Button(
            frame,
            text="Push list to compare list",
            bg="#4a90e2",
            fg="white",
            relief="flat",
            state="disabled",
            command=self.push_current_products_to_compare,
        )

        self.compare_button = tk.Button(
            frame,
            text="Show Compare List",
            bg="#f2f2f2",
            fg="#333333",
            relief="flat",
            command=self.toggle_compare_window,
        )

        self.compare_button.pack(side="left")
        self.push_compare_button.pack_forget()
        return frame

    def _sync_global_controls(self) -> None:
        self.global_controls.pack(fill="x", side="bottom", pady=(0, 12))
        self.compare_button.pack_forget()
        self.compare_button.pack(side="left")
        self.compare_button.config(
            text="Close Compare List" if self.compare_visible and self.compare_window is not None and self.compare_window.winfo_exists() else "Show Compare List"
        )

        if self.current_screen == "products":
            if self.visible_products:
                self.push_compare_button.config(state="normal")
                self.push_compare_button.pack_forget()
                self.push_compare_button.pack(side="left", padx=8)
            else:
                self.push_compare_button.config(state="disabled")
                self.push_compare_button.pack_forget()
        else:
            self.push_compare_button.config(state="disabled")
            self.push_compare_button.pack_forget()

    def _build_products_frame(self) -> tk.Frame:
        frame = tk.Frame(self.container, bg="#f5f5f5", padx=18, pady=16)
        frame.pack(fill="both", expand=True)

        header = tk.Frame(frame, bg="#f5f5f5")
        header.pack(fill="x")
        tk.Button(header, text="Back", bg="white", fg="#4a90e2", relief="flat", command=self.on_back).pack(side="left")
        self.filter_var = tk.StringVar(value="all")
        self.filter_combo = ttk.Combobox(header, textvariable=self.filter_var, width=16, state="readonly")
        self.filter_combo["values"] = ["All Products", "Cheapest First", "Most Popular"]
        self.filter_combo.pack(side="right")
        self.filter_combo.bind("<<ComboboxSelected>>", self.on_filter_change)

        self.products_title = tk.Label(frame, text="Products Found", font=("Arial", 16, "bold"), bg="#f5f5f5", fg="#1a1a1a")
        self.products_title.pack(anchor="w", pady=(10, 8))

        products_canvas = tk.Canvas(frame, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=products_canvas.yview)
        products_canvas.configure(yscrollcommand=scrollbar.set)

        self.products_inner = tk.Frame(products_canvas, bg="#f5f5f5")
        products_canvas.create_window((0, 0), window=self.products_inner, anchor="nw")
        self.products_inner.bind("<Configure>", lambda e: products_canvas.configure(scrollregion=products_canvas.bbox("all")))
        self.products_canvas = products_canvas
        products_canvas.bind_all("<MouseWheel>", lambda event: products_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        products_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return frame

    def _open_compare_window(self) -> None:
        if self.compare_window is not None and self.compare_window.winfo_exists():
            self.compare_window.focus_set()
            return

        self.compare_window = tk.Toplevel(self)
        self.compare_window.title("Compare List")
        self.compare_window.geometry("360x440")
        self.compare_window.transient(self)
        self.compare_window.focus_set()
        self.compare_window.protocol("WM_DELETE_WINDOW", self.on_compare_window_close)

        panel = tk.Frame(self.compare_window, bg="#f5f5f5", padx=12, pady=12)
        panel.pack(fill="both", expand=True)

        header = tk.Frame(panel, bg="#f5f5f5")
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="Compare List", font=("Arial", 14, "bold"), bg="#f5f5f5").pack(side="left")

        self.compare_sort_var = tk.StringVar(value="Price Low to High")
        self.compare_sort_combo = ttk.Combobox(header, textvariable=self.compare_sort_var, width=18, state="readonly")
        self.compare_sort_combo["values"] = ["Price Low to High", "Price High to Low", "Title A-Z"]
        self.compare_sort_combo.pack(side="right")
        self.compare_sort_combo.bind("<<ComboboxSelected>>", self.refresh_compare_window)

        content = tk.Frame(panel, bg="#f5f5f5")
        content.pack(fill="both", expand=True)

        self.compare_canvas = tk.Canvas(content, bg="#f5f5f5", highlightthickness=0)
        self.compare_scrollbar = ttk.Scrollbar(content, orient="vertical", command=self.compare_canvas.yview)
        self.compare_canvas.configure(yscrollcommand=self.compare_scrollbar.set)

        self.compare_inner = tk.Frame(self.compare_canvas, bg="#f5f5f5")
        self.compare_canvas.create_window((0, 0), window=self.compare_inner, anchor="nw")
        self.compare_inner.bind("<Configure>", lambda e: self.compare_canvas.configure(scrollregion=self.compare_canvas.bbox("all")))
        self.compare_canvas.bind_all("<MouseWheel>", lambda event: self.compare_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        self.compare_canvas.pack(side="left", fill="both", expand=True)
        self.compare_scrollbar.pack(side="right", fill="y")

        footer = tk.Frame(panel, bg="#f5f5f5")
        footer.pack(fill="x", pady=(10, 0))
        tk.Button(footer, text="Clear All", bg="#f2f2f2", fg="#333333", command=self.clear_compare_list).pack(side="left")

        self.compare_toggle_button = tk.Button(
            footer,
            text="Close Compare List",
            bg="#4a90e2",
            fg="white",
            relief="flat",
            command=self.toggle_compare_window,
        )
        self.compare_toggle_button.pack(side="right", fill="x", expand=True)

        self.compare_visible = True
        self.compare_button.config(text="Close Compare List")
        self.refresh_compare_window()

    def on_compare_window_close(self) -> None:
        self.compare_visible = False
        if self.compare_window is not None and self.compare_window.winfo_exists():
            self.compare_window.destroy()
        self.compare_window = None
        if hasattr(self, "compare_toggle_button"):
            self.compare_toggle_button = None
        self.compare_button.config(text="Show Compare List")

    def toggle_compare_window(self) -> None:
        if self.compare_window is not None and self.compare_window.winfo_exists():
            self.on_compare_window_close()
            return
        self.compare_visible = True
        self.compare_button.config(text="Close Compare List")
        self._open_compare_window()
        if self.compare_window is not None and self.compare_window.winfo_exists() and hasattr(self, "compare_toggle_button"):
            self.compare_toggle_button.config(text="Close Compare List")

    def refresh_compare_window(self, _event=None) -> None:
        if self.compare_window is None or not self.compare_window.winfo_exists():
            return

        for child in self.compare_inner.winfo_children():
            child.destroy()

        if not self.compare_items:
            tk.Label(
                self.compare_inner,
                text="No products",
                fg="#d9534f",
                bg="#f5f5f5",
                font=("Arial", 11, "bold"),
            ).pack(anchor="w", pady=8)
            return

        sort_mode = self.compare_sort_var.get()
        items = list(self.compare_items)
        if sort_mode == "Price Low to High":
            items.sort(key=lambda item: self._price_to_float(item.get("price", "N/A")))
        elif sort_mode == "Price High to Low":
            items.sort(key=lambda item: self._price_to_float(item.get("price", "N/A")), reverse=True)
        else:
            items.sort(key=lambda item: (item.get("title", "") or "").lower())

        for item in items:
            title = item.get("title", "")
            price = item.get("price", "N/A")
            rating = item.get("rating", "N/A")
            link = (item.get("link") or "").strip()
            store = item.get("store", "").title()

            card = tk.Frame(self.compare_inner, bg="#ffffff", bd=1, relief="solid")
            card.pack(fill="x", pady=6)

            tk.Label(card, text=title, fg="#1a1a1a", bg="#ffffff", wraplength=300, justify="left", anchor="w").pack(fill="x", padx=8, pady=(8, 4))
            tk.Label(card, text=f"Price: {price}", fg="#28a745", bg="#ffffff", anchor="w").pack(fill="x", padx=8)
            tk.Label(card, text=f"Rating: {rating}", fg="#666666", bg="#ffffff", anchor="w").pack(fill="x", padx=8)
            tk.Label(card, text=f"Store: {store}", fg="#555555", bg="#ffffff", anchor="w").pack(fill="x", padx=8)
            tk.Button(card, text="View Product ↗", bg="#f0f5ff", fg="#4a90e2", relief="flat", command=lambda target=link: webbrowser.open(target)).pack(anchor="w", padx=8, pady=(4, 8))

    def clear_compare_list(self) -> None:
        if not self.compare_items:
            self.compare_items = []
            self.compare_visible = False
            self.compare_button.config(text="Show Compare List")
            if self.compare_window is not None and self.compare_window.winfo_exists():
                self.refresh_compare_window()
            return

        if messagebox.askyesno("Clear all products", "Are you sure you want to remove all products?"):
            self.compare_items = []
            self.compare_visible = False
            self.compare_button.config(text="Show Compare List")
            if self.compare_window is not None and self.compare_window.winfo_exists():
                self.refresh_compare_window()

    def show_frame(self, frame_name: str) -> None:
        self.current_screen = frame_name
        for name, frame in [("search", self.search_frame), ("results", self.results_frame), ("products", self.products_frame)]:
            frame.pack_forget()

        if frame_name == "search":
            self.search_frame.pack(fill="both", expand=True)
        elif frame_name == "results":
            self.results_frame.pack(fill="both", expand=True)
        elif frame_name == "products":
            self.products_frame.pack(fill="both", expand=True)

        self.global_controls.pack(fill="x", side="bottom", pady=(0, 12))
        self._sync_global_controls()

        if self.compare_window is not None and self.compare_window.winfo_exists():
            self.compare_window.focus_set()

    def on_search(self) -> None:
        value = self.search_entry.get().strip()
        if not value:
            self.search_error.config(text="No input")
            return
        self.search_error.config(text="")
        self.product_name = value
        self.fill_links()
        self.show_frame("results")

    def fill_links(self) -> None:
        from urllib.parse import quote

        query = quote(self.product_name, safe="")
        walmart_query = query.replace("%20", "+")
        target_query = query.replace("%20", "+")
        self.link_buttons["amazon"].config(text=f"Amazon: https://www.amazon.com/s?k={query}")
        self.link_buttons["alibaba"].config(text=f"Alibaba: https://www.alibaba.com/showroom/{self.product_name.replace(' ', '-')}.html")
        self.link_buttons["walmart"].config(text=f"Walmart: https://www.walmart.com/search?q={walmart_query}")
        self.link_buttons["target"].config(text=f"Target: https://www.target.com/s?searchTerm={target_query}")

    def on_store_click(self, store: str) -> None:
        self.current_store = store
        self.show_frame("products")
        self.products_title.config(text=f"Products Found: {store.title()}")
        if not self.permission_granted:
            self.open_permission_dialog()
        else:
            self.get_page_data()

    def _open_permission_dialog(self) -> None:
        if self.permission_window is not None and self.permission_window.winfo_exists():
            self.permission_window.focus_set()
            return
        self.permission_window = tk.Toplevel(self)
        self.permission_window.title("Scan pages?")
        self.permission_window.geometry("320x220")
        self.permission_window.transient(self)
        self.permission_window.grab_set()

        tk.Label(self.permission_window, text="Scan pages?", font=("Arial", 14, "bold")).pack(pady=(16, 8))
        tk.Label(
            self.permission_window,
            text="Allow LowBall to read pages and collect product data.",
            wraplength=280,
            justify="left",
        ).pack(pady=(0, 8))

        tk.Label(self.permission_window, text="Maximum pages").pack(pady=(6, 2))
        self.max_pages_entry = tk.Entry(self.permission_window, width=12)
        self.max_pages_entry.insert(0, str(self.pages_to_scan))
        self.max_pages_entry.pack(pady=(0, 10))

        buttons = tk.Frame(self.permission_window)
        buttons.pack(pady=(6, 0))
        tk.Button(buttons, text="Cancel", bg="#f2f2f2", command=self.on_permission_cancel).pack(side="left", padx=6)
        tk.Button(buttons, text="Allow", bg="#4a90e2", fg="white", command=self.on_permission_allow).pack(side="left", padx=6)

    def open_permission_dialog(self) -> None:
        self._open_permission_dialog()

    def on_permission_cancel(self) -> None:
        self.permission_granted = False
        self.permission_window.destroy()
        self.permission_window = None
        self.on_back()

    def on_permission_allow(self) -> None:
        try:
            self.pages_to_scan = max(1, int(self.max_pages_entry.get().strip()))
        except ValueError:
            self.pages_to_scan = 1
        self.permission_granted = True
        self.permission_window.destroy()
        self.permission_window = None
        self.get_page_data()

    def get_page_data(self) -> None:
        self.scan_in_progress = True
        self.clear_products()
        self.render_loading_state()
        self.set_status("Scanning... Please wait")
        self.update_idletasks()

        def run_scan() -> None:
            try:
                products = collect_products(
                    self.current_store,
                    self.product_name,
                    pages_to_scan=self.pages_to_scan,
                    progress_callback=self.set_status,
                )
                self.raw_products = products
                self.render_products(products)
            except Exception as exc:
                message = str(exc)
                if "Verification required" in message:
                    self.set_status("Verification required")
                    self.render_verification_notice()
                else:
                    self.set_status(f"Scan failed: {message}")
                    self.render_products([], show_retry=True)
            finally:
                self.scan_in_progress = False

        self.after(0, run_scan)

    def clear_products(self) -> None:
        for child in self.products_inner.winfo_children():
            child.destroy()

    def render_loading_state(self) -> None:
        self.clear_products()
        tk.Label(self.products_inner, text="Loading products...", fg="#4a90e2", bg="#f5f5f5", font=("Arial", 11, "bold")).pack(anchor="w", pady=8)
        tk.Label(self.products_inner, text="Please wait while the scan completes.", fg="#666666", bg="#f5f5f5").pack(anchor="w", pady=4)

    def render_verification_notice(self) -> None:
        self.clear_products()
        tk.Label(self.products_inner, text="Verification required", fg="#d9534f", bg="#f5f5f5", font=("Arial", 11, "bold")).pack(anchor="w", pady=8)
        tk.Label(
            self.products_inner,
            text="A login, captcha, or bot-check is blocking the scan. Complete it in the verification window and continue when ready.",
            fg="#666666",
            bg="#f5f5f5",
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=4)
        tk.Button(self.products_inner, text="Open verification window", bg="#4a90e2", fg="white", relief="flat", command=self.open_verification_dialog).pack(anchor="w", pady=8)

    def open_verification_dialog(self) -> None:
        if self.verification_window is not None and self.verification_window.winfo_exists():
            self.verification_window.focus_set()
            return

        url = build_url(self.current_store, self.product_name, page=1)
        self.verification_window = tk.Toplevel(self)
        self.verification_window.title("Verification required")
        self.verification_window.geometry("760x310")
        self.verification_window.transient(self)
        self.verification_window.grab_set()
        self.verification_window.protocol("WM_DELETE_WINDOW", self.on_verification_cancel)

        body = tk.Frame(self.verification_window, padx=16, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Complete the login or captcha, then continue.", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Label(body, text=url, fg="#4a90e2", bg="#ffffff", wraplength=700, justify="left").pack(anchor="w", pady=(0, 12))

        tk.Button(body, text="Open in default browser", bg="#f2f2f2", command=lambda: webbrowser.open(url)).pack(anchor="w", pady=(0, 12))

        info = tk.Label(
            body,
            text="The verification window stays open until you continue or cancel. Closing this window shows no products.",
            wraplength=700,
            justify="left",
            fg="#666666",
        )
        info.pack(anchor="w", pady=(0, 12))

        buttons = tk.Frame(body)
        buttons.pack(anchor="w")
        tk.Button(buttons, text="Continue", bg="#4a90e2", fg="white", command=self.on_verification_continue).pack(side="left", padx=(0, 10))
        tk.Button(buttons, text="Cancel", bg="#f2f2f2", command=self.on_verification_cancel).pack(side="left")

        self._open_verification_browser(url)

    def _open_verification_browser(self, url: str) -> None:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            options.add_argument("--window-size=760,310")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--start-maximized")
            self.verification_browser = webdriver.Chrome(options=options)
            self.verification_page = self.verification_browser
            self.verification_browser.get(url)
        except Exception:
            self.verification_browser = None
            self.verification_page = None

    def on_verification_continue(self) -> None:
        self._close_verification_browser()
        if self.verification_window is not None and self.verification_window.winfo_exists():
            self.verification_window.destroy()
            self.verification_window = None
        self.get_page_data()

    def on_verification_cancel(self) -> None:
        self._close_verification_browser()
        if self.verification_window is not None and self.verification_window.winfo_exists():
            self.verification_window.destroy()
            self.verification_window = None
        self.raw_products = []
        self.clear_products()
        self.render_products([])
        self.scan_in_progress = False

    def _close_verification_browser(self) -> None:
        try:
            if self.verification_page is not None:
                self.verification_page.close()
        except Exception:
            pass
        try:
            if self.verification_browser is not None:
                self.verification_browser.stop()
        except Exception:
            pass
        self.verification_page = None
        self.verification_browser = None

    def render_products(self, products: List[Dict[str, str]], show_retry: bool = False) -> None:
        self.clear_products()
        visible_products = []
        for product in products:
            link = (product.get("link") or "").strip()
            price = (product.get("price") or "").strip()
            rating = (product.get("rating") or "").strip()
            if not link:
                continue
            if (price in ("", "N/A") or price.lower() == "n/a") and (rating in ("", "N/A") or rating.lower() == "n/a"):
                continue
            visible_products.append(product)

        self.visible_products = visible_products
        self.push_compare_button.config(state="normal" if visible_products else "disabled")
        self.products_title.config(text=f"Products Found: {len(visible_products)}")
        if self.current_screen == "products":
            self._sync_global_controls()

        if not visible_products:
            tk.Label(self.products_inner, text="No products found.", fg="#666666", bg="#f5f5f5").pack(anchor="w", pady=8)
            if show_retry:
                tk.Button(self.products_inner, text="Retry Scan", bg="#4a90e2", fg="white", relief="flat", command=self.get_page_data).pack(anchor="w", pady=8)
            return

        for product in visible_products:
            link = (product.get("link") or "").strip()
            price = (product.get("price") or "").strip()
            rating = (product.get("rating") or "").strip()

            card = tk.Frame(self.products_inner, bg="#ffffff", bd=1, relief="solid")
            card.pack(fill="x", pady=6)
            tk.Label(card, text=product.get("title", ""), fg="#1a1a1a", bg="#ffffff", wraplength=320, justify="left", anchor="w").pack(fill="x", padx=8, pady=(8, 4))
            tk.Label(card, text=f"Price: {price or 'N/A'}", fg="#28a745", bg="#ffffff", anchor="w").pack(fill="x", padx=8)
            display_rating = rating if rating and rating != "N/A" else "Unknown"
            tk.Label(card, text=f"Rating: {display_rating}", fg="#666666", bg="#ffffff", anchor="w").pack(fill="x", padx=8)
            store_name = product.get("store", self.current_store or "unknown").title()
            tk.Label(card, text=f"Store: {store_name}", fg="#555555", bg="#ffffff", anchor="w").pack(fill="x", padx=8)
            tk.Button(card, text="View Product ↗", bg="#f0f5ff", fg="#4a90e2", relief="flat", command=lambda target=link: webbrowser.open(target)).pack(anchor="w", padx=8, pady=(4, 8))

    def push_current_products_to_compare(self) -> None:
        if not self.visible_products:
            return

        for product in self.visible_products:
            entry = dict(product)
            entry["store"] = self.current_store
            duplicate = any(existing.get("link") == entry.get("link") for existing in self.compare_items)
            if not duplicate:
                self.compare_items.append(entry)

        if self.compare_window is not None and self.compare_window.winfo_exists():
            self.refresh_compare_window()
        self.compare_visible = True

    def on_filter_change(self, _event=None) -> None:
        mode = self.filter_var.get().lower()
        if mode == "cheapest first":
            sorted_products = sorted(self.raw_products, key=lambda p: self._price_to_float(p.get("price", "")))
        elif mode == "most popular":
            sorted_products = sorted(self.raw_products, key=lambda p: self._rating_to_float(p.get("rating", "")), reverse=True)
        else:
            sorted_products = list(self.raw_products)
        self.render_products(sorted_products)

    def _price_to_float(self, price: str) -> float:
        match = re.search(r"\d+(?:[.,]\d{1,2})?", price)
        if match:
            return float(match.group(0).replace(",", ""))
        return float("inf")

    def _rating_to_float(self, rating: str) -> float:
        match = re.search(r"\d+(?:[.,]\d{1,2})?", rating)
        if match:
            return float(match.group(0).replace(",", ""))
        return 0.0

    def set_status(self, message: str) -> None:
        self.products_title.config(text=message)

    def on_back(self) -> None:
        if self.permission_window is not None and self.permission_window.winfo_exists():
            self.permission_window.destroy()
            self.permission_window = None

        if self.current_screen == "products":
            self.permission_granted = False
            self.current_store = ""
            self.show_frame("results")
            return

        if self.current_screen == "results":
            self.permission_granted = False
            self.current_store = ""
            self.show_frame("search")
            return

        self.show_frame("search")


CheaperApp = LowBallApp

if __name__ == "__main__":
    app = LowBallApp()
    app.mainloop()
