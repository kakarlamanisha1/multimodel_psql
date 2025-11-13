# ==========================
# 1️⃣ Base image
# ==========================
FROM python:3.10-slim

# ==========================
# 2️⃣ Set working directory
# ==========================
WORKDIR /app

# ==========================
# 3️⃣ Copy project files
# ==========================
COPY . /app

# ==========================
# 4️⃣ Install dependencies
# ==========================
# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip

# Install packages from requirements.txt if available
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# ==========================
# 5️⃣ Expose Streamlit port
# ==========================
EXPOSE 8501

# ==========================
# 6️⃣ Set environment variables (optional)
# ==========================
ENV PYTHONUNBUFFERED=1
ENV PORT=8501

# ==========================
# 7️⃣ Streamlit configuration
# ==========================
# Disable Streamlit asking for headless mode, telemetry, etc.
RUN mkdir -p ~/.streamlit && \
    echo "\
    [server]\n\
    headless = true\n\
    enableCORS = false\n\
    port = 8501\n\
    \n\
    [theme]\n\
    base = 'dark'\n\
    " > ~/.streamlit/config.toml

# ==========================
# 8️⃣ Default command to run the app
# ==========================
CMD ["streamlit", "run", "app.py"]
