# Virtual Environment Activation Guide for Windows

## Why the Error Occurs in PowerShell

The error "The term is not recognized as the name of a cmdlet" happens because:

1. **PowerShell doesn't use `.bat` files directly** - The `activate` script in `venv/Scripts/` is a batch file (`.bat`) designed for Command Prompt, not PowerShell.

2. **Different shell syntax** - PowerShell has its own way of activating virtual environments.

3. **Execution policy restrictions** - PowerShell may block script execution by default for security reasons.

---

## Correct Commands to Activate Virtual Environment

### PowerShell (Recommended)
```
powershell
.\venv\Scripts\Activate
```
Or use this if the above doesn't work:
```
powershell
& "C:\Users\User\OneDrive\Desktop\Pinnacle\venv\Scripts\Activate.ps1"
```

### Command Prompt (cmd)
```
cmd
venv\Scripts\activate
```
Or with full path:
```
cmd
C:\Users\User\OneDrive\Desktop\Pinnacle\venv\Scripts\activate
```

### Git Bash
```
bash
source venv/Scripts/activate
```
Or with full path:
```
bash
source /c/Users/User/OneDrive/Desktop/Pinnacle/venv/Scripts/activate
```

---

## If Execution Policy Blocks Activation

If you see an error like "running scripts is disabled on this system", run this command FIRST:

```
powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

This temporarily allows script execution for the current PowerShell session only. It will reset when you close PowerShell.

---

## Step-by-Step Instructions

### Step 1: Open Your Terminal

- **PowerShell**: Search for "PowerShell" in Start menu, right-click, and select "Run as Administrator" (optional but recommended)
- **Command Prompt**: Search for "cmd" in Start menu
- **Git Bash**: Open Git Bash if installed

### Step 2: Navigate to Your Project Folder

**PowerShell / Command Prompt:**
```
powershell
cd C:\Users\User\OneDrive\Desktop\Pinnacle
```

**Git Bash:**
```
bash
cd /c/Users/User/OneDrive/Desktop/Pinnacle
```

### Step 3: Activate the Virtual Environment

**For PowerShell:**
```
powershell
.\venv\Scripts\Activate
```

**For Command Prompt:**
```
cmd
venv\Scripts\activate
```

**For Git Bash:**
```
bash
source venv/Scripts/activate
```

### Step 4: Verify Activation

After activation, you should see `(venv)` at the beginning of your command prompt, like:

```
(venv) PS C:\Users\User\OneDrive\Desktop\Pinnacle>
```

You can also verify with:
```
powershell
python --version
```
This should show Python from your virtual environment, not the system Python.

---

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Term not recognized" in PowerShell | Use `.\venv\Scripts\Activate` instead of just `activate` |
| "Scripts disabled" error | Run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Nothing happens after activate | Make sure you're in the correct directory first |
| Git Bash says "permission denied" | Try: `chmod +x venv/Scripts/activate` |

---

## Alternative: Use Python -m venv

If you continue having issues, you can recreate the virtual environment:

```
powershell
python -m venv venv
```

Then activate using the commands above.

---

## For Running Your Flask App

Once activated, install dependencies:
```
powershell
pip install -r requirements.txt
```

Run your Flask app:
```
powershell
python app.py
```

Or:
```
powershell
flask run
