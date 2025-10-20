Quick run instructions (macOS)

1) Open Terminal and go to project folder:

   cd /Users/achi/swiss-asset-manager

2) Make start script executable (only once):

   chmod +x start_app.sh

3) Run the helper script (creates venv, installs requirements, starts app on free port):

   ./start_app.sh

4) Open the URL printed in the console (e.g. http://127.0.0.1:8000) in your browser. The app prints the access password in the console.

Notes:
- If installation fails with numpy build errors, use Python 3.11 and recreate the venv. I can give exact pyenv/Homebrew commands if you want.
   - If you get SciPy/numpy build errors (missing Fortran or lzma), run the helper to install pyenv and build dependencies:
      ```bash
      chmod +x fix_python.sh
      ./fix_python.sh
      rm -rf venv
      ./start_app.sh
      ```
      `fix_python.sh` will install Homebrew dependencies (xz, gcc, pkg-config) and `pyenv`, then install Python 3.11.x locally so SciPy and numpy can be built.
- If port 8000 is in use, the script will try 8001. If both in use, free a port or edit the script.

Environment (.env):

- Copy `.env.example` to `.env` and set one of:
   - `APP_PASSWORD=your-plaintext` (hashed at startup), or
   - `APP_PASSWORD_HASH=...` (precomputed, preferred for prod)
- To generate a hash locally:
   ```bash
   source venv/bin/activate
   python tools/hash_password.py
   ```
   Copy the printed hash into `.env` as `APP_PASSWORD_HASH=...`.
