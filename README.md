# Pakistani Residential Floorplan Generator

An AI-powered architectural pipeline designed for the Pakistani residential market. This project extends the **Graph2Plan** framework to generate high-fidelity, culturally appropriate floorplans with professional CAD-style outputs.

## 🚀 Key Features
- **Architectural Edge Detection**: Automatically merges room polygons to eliminate messy internal lines.
- **Master Line Masking**: Ensures perfectly uniform 2px line thickness across all drawings.
- **Smart Labeling**: Centered, readable labels with automatic grouping for complex room shapes.
- **Professional Exports**:
  - **PNG**: Labeled and Clean blueprints.
  - **SVG**: Scaleable vector graphics for high-resolution printing.
  - **CAD Drafting View**: High-detail Matplotlib-based plan with architectural grids and dimension lines (scaled to 25'x45').
  - **JSON**: Structured coordinate data for integration with other software.

---

## 🛠️ Installation & Setup

### 1. Python Environment
This project runs on Python 3.14 (or 3.x).
```bash
# Clone the repository
git clone https://github.com/your-username/pakistani-floorplan-gen.git
cd pakistani-floorplan-gen

# Create and activate virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. MATLAB Configuration (Mandatory)
The layout alignment (snapping) engine requires **MATLAB**.
- **Installation**: Ensure MATLAB (R2026a or newer recommended) is installed.
- **Proxy Setup**: This project uses a custom Subprocess Proxy to avoid MATLAB Engine API compatibility issues.
- **Configure Path**: Open `Graph2plan/Interface/Houseweb/views.py` and update the `matlab_exe` path to point to your local installation:
  ```python
  # Line 175 in views.py
  matlab_exe = r'C:\Program Files\MATLAB\R2026a\bin\matlab.exe'
  ```

### 3. Dataset Setup
Download the required pickle datasets and place them in the following directory:
`Graph2plan/Interface/static/Data/`
- `data_test_converted.pkl`
- `data_train_converted.pkl`

---

## 🖥️ Usage

### Running the Generator
1. Start the Django server:
   ```bash
   cd Graph2plan/Interface
   python manage.py runserver
   ```
2. Open your browser and go to: `http://127.0.0.1:8000/`

### Using the Zone Editor
For new plots, use the custom Zone Editor to define garage and setback constraints:
1. Open `Template genertor tool/zone_editor_v5.html` in any browser.
2. Draw your zones and click "Generate Template Code."
3. Paste the code into `pakistani_generator/template_postprocess.py`.

---

## 📐 Export Options
On the **Results** page, you can download:
- **Vector SVG**: Scaleable architectural drawing.
- **Final CAD Output**: Formal drafting view with grids and title block.
- **Floorplan Data**: Raw JSON coordinates.

---

## 🤝 Acknowledgements
- Based on the original **Graph2Plan** research.
- Developed for the Pakistani Architectural context by the FYP team.
