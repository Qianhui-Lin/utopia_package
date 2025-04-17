from fpdf import FPDF
import matplotlib.pyplot as plt
import pandas as pd
import tempfile
import os


class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Results Report", ln=True, align="C")
        self.ln(10)

    def add_text(self, text):
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 10, text)
        self.ln()

    def add_dataframe(self, df):
        self.set_font("Arial", "", 8)
        col_width = self.w / (len(df.columns) + 1)
        for col in df.columns:
            self.cell(col_width, 8, str(col), border=1)
        self.ln()
        for i in df.itertuples(index=False):
            for val in i:
                self.cell(col_width, 8, str(val), border=1)
            self.ln()
        self.ln()

    def add_figure(self, fig):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            fig.savefig(tmpfile.name)
            self.image(tmpfile.name, w=180)
            plt.close(fig)
        os.remove(tmpfile.name)

    def add_dict(self, d):
        for k, v in d.items():
            self.add_text(f"{k}: {v}")
