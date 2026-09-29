# Supermart Sales Dashboard

An interactive Dash application showing four KPIs and four Plotly charts. The Year dropdown updates every KPI and chart through one callback.

## Project structure

```text
supermart_render_dashboard/
├── app.py
├── assets/
│   └── style.css
├── data/
│   └── supermart_grocery_sales.csv
├── requirements.txt
├── Procfile
├── render.yaml
└── .python-version
```

## Run locally

Create and activate a virtual environment, then install the requirements.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### Windows Git Bash

```bash
py -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python app.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:8050/>. Press `Ctrl+C` in the terminal to stop the server.

## Deploy on Render

1. Push this folder to a GitHub repository.
2. Sign in to [Render](https://dashboard.render.com/).
3. Select **New → Web Service** and connect the repository.
4. Confirm these settings:

   | Setting | Value |
   |---|---|
   | Runtime | Python |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:server --bind 0.0.0.0:$PORT` |

5. Select a plan and create the web service.

The included `render.yaml` contains the same configuration if you prefer to create a Render Blueprint.


