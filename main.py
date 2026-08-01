import re
import tkinter as tk
from tkinter import ttk
import webbrowser
from typing import List, Dict

from scraper import collect_products


class CheaperApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cheaper")
        self.geometry("400x520")
        self.resizable(False, False)
        self.configure(bg="#f5f5f5")

        self.product_name = ""
        self.current_store = ""
        self.permission_granted = False
        self.pages_to_scan = 1
        self.raw_products: List[Dict[str, str]] = []
        self.scan_in_progress = False

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
        self.permission_window = None

        self.show_frame("search")

    def _build_search_frame(self) -> tk.Frame:
        frame = tk.Frame(self.container, bg="#f5f5f5", padx=18, pady=16)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Cheaper", font=("Arial", 20, "bold"), bg="#f5f5f5", fg="#1a1a1a").pack(pady=(0, 14))

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
        for store in ["amazon", "alibaba", "temu"]:
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
        products_canvas.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=products_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        products_canvas.configure(yscrollcommand=scrollbar.set)

        self.products_inner = tk.Frame(products_canvas, bg="#f5f5f5")
        products_canvas.create_window((0, 0), window=self.products_inner, anchor="nw")
        self.products_inner.bind("<Configure>", lambda e: products_canvas.configure(scrollregion=products_canvas.bbox("all")))
        self.products_canvas = products_canvas
        return frame

    def show_frame(self, frame_name: str) -> None:
        for name, frame in [("search", self.search_frame), ("results", self.results_frame), ("products", self.products_frame)]:
            frame.pack_forget()
        if frame_name == "search":
            self.search_frame.pack(fill="both", expand=True)
        elif frame_name == "results":
            self.results_frame.pack(fill="both", expand=True)
        elif frame_name == "products":
            self.products_frame.pack(fill="both", expand=True)

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
        self.link_buttons["amazon"].config(text=f"Amazon: https://www.amazon.com/s?k={query}")
        self.link_buttons["alibaba"].config(text=f"Alibaba: https://www.alibaba.com/showroom/{self.product_name.replace(' ', '-')}.html")
        self.link_buttons["temu"].config(text=f"Temu: https://www.temu.com/search_result.html?search_key={query}")

    def on_store_click(self, store: str) -> None:
        self.current_store = store
        self.show_frame("products")
        self.products_title.config(text=f"Products Found: {store.title()}")
        if not self.permission_granted:
            self.open_permission_dialog()
        else:
            self.get_page_data()

    def open_permission_dialog(self) -> None:
        if self.permission_window is not None and self.permission_window.winfo_exists():
            return
        self.permission_window = tk.Toplevel(self)
        self.permission_window.title("Scan pages?")
        self.permission_window.geometry("320x220")
        self.permission_window.transient(self)
        self.permission_window.grab_set()

        tk.Label(self.permission_window, text="Scan pages?", font=("Arial", 14, "bold")).pack(pady=(16, 8))
        tk.Label(
            self.permission_window,
            text="Allow Cheaper to read pages and collect product data.",
            wraplength=280,
            justify="left",
        ).pack(pady=(0, 8))

        tk.Label(self.permission_window, text="Maximum pages").pack(pady=(6, 2))
        self.max_pages_entry = tk.Entry(self.permission_window, width=12)
        self.max_pages_entry.insert(0, "1")
        self.max_pages_entry.pack(pady=(0, 10))

        buttons = tk.Frame(self.permission_window)
        buttons.pack(pady=(6, 0))
        tk.Button(buttons, text="Cancel", bg="#f2f2f2", command=self.on_permission_cancel).pack(side="left", padx=6)
        tk.Button(buttons, text="Allow", bg="#4a90e2", fg="white", command=self.on_permission_allow).pack(side="left", padx=6)

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
            text="This site asked for a login, bot check, or unusual traffic verification. Please complete the prompt in the browser and try again.",
            fg="#666666",
            bg="#f5f5f5",
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=4)
        tk.Button(self.products_inner, text="Retry Scan", bg="#4a90e2", fg="white", relief="flat", command=self.get_page_data).pack(anchor="w", pady=8)

    def render_products(self, products: List[Dict[str, str]], show_retry: bool = False) -> None:
        self.clear_products()
        if not products:
            tk.Label(self.products_inner, text="No products found.", fg="#666666", bg="#f5f5f5").pack(anchor="w", pady=8)
            if show_retry:
                tk.Button(self.products_inner, text="Retry Scan", bg="#4a90e2", fg="white", relief="flat", command=self.get_page_data).pack(anchor="w", pady=8)
            return

        for product in products:
            card = tk.Frame(self.products_inner, bg="#ffffff", bd=1, relief="solid")
            card.pack(fill="x", pady=6)
            tk.Label(card, text=product.get("title", ""), fg="#1a1a1a", bg="#ffffff", wraplength=320, justify="left", anchor="w").pack(fill="x", padx=8, pady=(8, 4))
            tk.Label(card, text=f"Price: {product.get('price', 'N/A')}", fg="#28a745", bg="#ffffff", anchor="w").pack(fill="x", padx=8)
            tk.Label(card, text=f"Rating: {product.get('rating', 'N/A')}", fg="#666666", bg="#ffffff", anchor="w").pack(fill="x", padx=8)
            tk.Button(card, text="View Product ↗", bg="#f0f5ff", fg="#4a90e2", relief="flat", command=lambda link=product.get("link", ""): webbrowser.open(link)).pack(anchor="w", padx=8, pady=(4, 8))

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
        if self.current_store:
            self.show_frame("results")
        else:
            self.show_frame("search")


if __name__ == "__main__":
    app = CheaperApp()
    app.mainloop()
